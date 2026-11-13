import io
import socket
import struct
import threading
import unittest
from unittest.mock import patch
from PIL import Image
from ntr_transport import endpoint, control_packets, FrameAssembler, FrameStore, open_stream
from tppflush import LumaInputServer, HIDButtons


def packets(screen, colour='red', frame=1):
    image = Image.new('RGB', (240, 320 if screen == 0 else 400), colour)
    buf = io.BytesIO(); image.save(buf, 'JPEG')
    data = buf.getvalue()
    chunks = [data[i:i+700] for i in range(0,len(data),700)]
    return [bytes([frame, screen | (16 if i == len(chunks)-1 else 0), 0, i])+chunk for i,chunk in enumerate(chunks)]


class TransportTests(unittest.TestCase):
    def test_address_validation(self):
        self.assertEqual(endpoint('192.168.1.3',8001),('192.168.1.3',8001))
        self.assertEqual(endpoint('127.0.0.1:65535',8001),('127.0.0.1',65535))
        for invalid in ('1.2.3.4:0','1.2.3.4:65536','1.2.3.4:3:4','host:2','256.0.0.1','1.2.3.4:'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): endpoint(invalid,8001)

    def test_control_packet_layout_matches_upstream(self):
        heartbeat, setup = control_packets(8123)
        self.assertEqual(len(heartbeat),84); self.assertEqual(len(setup),84)
        self.assertEqual(struct.unpack_from('<I',heartbeat)[0],0x12345678)
        self.assertEqual(struct.unpack_from('<I',setup,12)[0],901)
        self.assertEqual(struct.unpack_from('<H',setup,32)[0],8123)
        self.assertEqual(struct.unpack_from('<I',setup,20)[0],80)

    def test_interleaved_screens_and_frame_wrap(self):
        assembler = FrameAssembler(); result={}
        lower,upper = packets(0,frame=255),packets(1,frame=255)
        for i in range(max(len(lower),len(upper))):
            for ps in (lower,upper):
                if i < len(ps):
                    r=assembler.feed(ps[i])
                    if r: result[r[0]]=r[1].size
        self.assertEqual(result,{0:(320,240),1:(400,240)})
        for packet in packets(1,frame=0): r=assembler.feed(packet)
        self.assertEqual(r[0],1)

    def test_dropped_out_of_order_and_invalid_jpeg(self):
        assembler=FrameAssembler(); ps=packets(1)
        result=[assembler.feed(p) for p in ps[:1]+ps[2:]]
        self.assertFalse(any(result))
        for p in (b'',b'123',bytes([1,17,0,0])+b'not a jpeg',bytes([0,22,0,0])+b'xxx'):
            self.assertIsNone(assembler.feed(p))

    def test_stale_and_frozen_repeated_frames(self):
        clock=[0.0]; store=FrameStore(lambda:clock[0]); image=Image.new('RGB',(320,240))
        store.put(0,image); self.assertEqual(store.snapshot(0).serial,1)
        clock[0]=3
        with self.assertRaises(OSError):store.snapshot(0)
        store.put(0,image); self.assertEqual(store.snapshot(0).serial,2)
        clock[0]=16; store.put(0,image)
        with self.assertRaises(OSError):store.snapshot(0)
        store.put(0,Image.new('RGB',(320,240),'blue')); store.snapshot(0)
        store.error='receive error'
        with self.assertRaises(OSError): store.snapshot(0)

    def test_input_redirection_actual_udp_packet_and_custom_port(self):
        receiver=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        receiver.bind(('127.0.0.1',0));receiver.settimeout(1)
        server=LumaInputServer('127.0.0.1',receiver.getsockname()[1])
        try:
            server.press(HIDButtons.A);server.send(print_sent=False)
            packet,_=receiver.recvfrom(100)
            self.assertEqual(len(packet),20)
            self.assertEqual(int.from_bytes(packet[:4],'little') & 1,0)
            server.return_control(); packet,_=receiver.recvfrom(100)
            self.assertEqual(packet,bytes.fromhex('ff0f000000000002fff77f008100808000000000'))
        finally:server.socket.close();receiver.close()

    def test_actual_tcp_setup_and_local_udp_bind(self):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
        received=[]
        def consume():
            conn,_=listener.accept()
            with conn:
                while sum(map(len,received))<336:
                    received.append(conn.recv(336))
        worker=threading.Thread(target=consume);worker.start()
        # Reserve a free local UDP port for the exact bind tested below.
        probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);probe.bind(('127.0.0.1',0))
        port=probe.getsockname()[1];probe.close()
        tcp,udp=open_stream(('127.0.0.1',port),'127.0.0.1',listener.getsockname()[1])
        try:
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(b''.join(received),b''.join(control_packets(port))*2)
            self.assertEqual(udp.getsockname(),('127.0.0.1',port))
        finally:tcp.close();udp.close();listener.close()

if __name__=='__main__':unittest.main()
