"""Synthetic ChirunoMod v0.2.2 wire fixtures, not console compatibility proof."""
import io
import json
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch, call
from contextlib import redirect_stdout
from PIL import Image, ImageDraw
from chiruno_transport import packet, setup_packets, PacketParser, ChirunoDecoder, ChirunoSource, ProtocolError, MAX_PAYLOAD, VideoFrame
from ntr_transport import FrameStore
from video_stream import console_endpoint
from hardware_probe import probe
from hardware_validation import hardware_context, receipt_path, require_hardware
from tppflush import HIDButtons
import hashlib


def image_message(screen,index=None,colour=(210,50,10), padded=False):
    width=320 if screen==0 else 400
    segment=width//8 if index is not None else width
    rgb=Image.new('RGB',(segment,240),colour).rotate(-90,expand=True)
    r,g,b=rgb.split();wire=Image.merge('RGB',(b,g,r))
    if padded:
        bigger=Image.new('RGB',(256,wire.height));bigger.paste(wire,(0,0));wire=bigger
    stream=io.BytesIO();wire.save(stream,'JPEG',quality=100,subsampling=0)
    return 1,(0x10 if screen==0 else 0)|1,0 if index is None else 8|index,stream.getvalue()


def wire_message(message):
    kind,a,b,data=message
    return packet(kind,a,data,b)


class ChirunoTests(unittest.TestCase):
    def test_endpoints_do_not_confuse_ntr_and_chiruno(self):
        self.assertEqual(console_endpoint('192.168.1.2','ChirunoMod'),('192.168.1.2',6464))
        self.assertEqual(console_endpoint('192.168.1.2','NTR-HR'),('192.168.1.2',8000))
        self.assertEqual(console_endpoint('192.168.1.2:6465','ChirunoMod')[1],6465)
        with self.assertRaises(ValueError):console_endpoint('127.0.0.1','HzMod')

    def test_settings_wire_format_is_not_ntr(self):
        messages=[]
        for raw in setup_packets():messages+=PacketParser().feed(raw)
        self.assertEqual([(k,a,d) for k,a,b,d in messages],[(4,4,b'\0'),(4,1,b'P'),(4,5,b'\0'),(4,3,b'\x03'),(2,0,b'')])
        self.assertEqual(sum(map(len,setup_packets())),44)
        with self.assertRaises(ValueError):setup_packets(0)

    def test_tcp_parser_preserves_fragmented_headers_and_payloads(self):
        raw=b''.join(wire_message(image_message(1,i)) for i in range(8))
        parser=PacketParser();messages=[]
        for byte in raw:messages.extend(parser.feed(bytes([byte])))
        self.assertEqual(len(messages),8);self.assertFalse(parser.buffer)
        self.assertEqual(messages[7][2],15)
        with self.assertRaises(ProtocolError):PacketParser().feed(struct.pack('<BBBBI',1,0,0,0,MAX_PAYLOAD+1))

    def test_interleaved_eight_fractions_only_publish_complete_native_screens(self):
        clock=[1.0];decoder=ChirunoDecoder(clock=lambda:clock[0]);results={}
        for i in range(8):
            for screen in (0,1):
                clock[0]+=.02
                frame=decoder.feed(image_message(screen,i,(50+20*i,60,80)))
                if i<7:self.assertIsNone(frame)
                else:results[screen]=frame
        for screen,frame in results.items():
            width=320 if screen==0 else 400
            self.assertEqual(frame.image.size,(width,240))
            for i in range(8):
                pixel=frame.image.getpixel((i*width//8+5,100))
                self.assertLess(abs(pixel[0]-(50+20*i)),3)
            self.assertLess(frame.started,frame.completed)

    def test_coalesced_packets_keep_independent_first_byte_times(self):
        parser=PacketParser();raw=packet(255,payload=b'hello')
        self.assertEqual(parser.feed_timed(raw[:3],10),[])
        results=parser.feed_timed(raw[3:]+raw+raw[:4],11)
        self.assertEqual([started for _,started in results],[10,11])
        self.assertEqual(parser.started,11)
        results=parser.feed_timed(raw[4:],12)
        self.assertEqual([started for _,started in results],[11])
        self.assertIsNone(parser.started)

    def test_source_coalescing_does_not_age_later_frames_from_first_packet(self):
        clock=[10.0];raw=wire_message(image_message(1))
        source=ChirunoSource.__new__(ChirunoSource)
        source.parser=PacketParser();source.decoder=ChirunoDecoder(clock=lambda:clock[0])
        source.ready=[];source.partial_since=None;source.read_limit=2
        chunks=iter([raw[:4]]+[raw[4:]+raw[:4]]*15)
        def receive(size):
            clock[0]+=.2
            return next(chunks)
        source.tcp=Mock();source.tcp.recv.side_effect=receive
        frames=[]
        with patch('chiruno_transport.time.monotonic',side_effect=lambda:clock[0]):
            while len(frames)<15:
                try:frames.append(source.read())
                except socket.timeout:pass
        self.assertGreater(frames[-1].started-frames[0].started,2)
        self.assertTrue(all(f.completed-f.started<.21 for f in frames))

    def test_full_frame_padded_width_rotation_and_red_blue(self):
        frame=ChirunoDecoder().feed(image_message(1,colour=(220,50,10),padded=True))
        self.assertEqual(frame.image.size,(400,240))
        p=frame.image.getpixel((10,10));self.assertGreater(p[0],200);self.assertLess(p[2],20)
        # Asymmetric image: top-left in native coordinates must remain top-left.
        native=Image.new('RGB',(400,240),'blue');ImageDraw.Draw(native).rectangle((0,0,30,30),fill='red')
        raw=native.rotate(-90,expand=True);r,g,b=raw.split();raw=Image.merge('RGB',(b,g,r))
        buf=io.BytesIO();raw.save(buf,'JPEG',quality=100,subsampling=0)
        frame=ChirunoDecoder().feed((1,1,0,buf.getvalue()))
        self.assertGreater(frame.image.getpixel((5,5))[0],240)
        self.assertGreater(frame.image.getpixel((390,230))[2],240)

    def test_missing_duplicate_and_interlaced_fractions_fail_closed(self):
        for bad in (2,0):
            d=ChirunoDecoder();d.feed(image_message(1,0))
            with self.subTest(bad=bad),self.assertRaises(ProtocolError):d.feed(image_message(1,bad))
        for flag in (8,32,64,128):
            msg=list(image_message(1,0));msg[1]|=flag
            with self.subTest(flag=flag),self.assertRaises(ProtocolError):ChirunoDecoder().feed(msg)
        with self.assertRaises(ProtocolError):ChirunoDecoder().feed((3,0,0,b''))
        with self.assertRaises(ProtocolError):ChirunoDecoder().feed((1,1,8,b'bad jpeg'))

    def test_slow_assembly_and_old_packet_do_not_become_fresh(self):
        clock=[1.0];d=ChirunoDecoder(max_span=.5,clock=lambda:clock[0])
        d.feed(image_message(1,0));clock[0]=2
        with self.assertRaises(ProtocolError):d.feed(image_message(1,1))
        with self.assertRaises(ProtocolError):d.feed(image_message(0),packet_started=1)
        store=FrameStore(lambda:3.0)
        store.put(0,Image.new('RGB',(320,240)),started=0,completed=3)
        with self.assertRaises(OSError):store.snapshot(0)
        store.put(0,Image.new('RGB',(320,240)),started=1.9,completed=2)
        with self.assertRaises(OSError):store.snapshot(0,max_age=1)

    def test_real_tcp_setup_fragmentation_decode_and_disconnect(self):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(3)
        received=[];errors=[]
        def server():
            try:
                connection,_=listener.accept();connection.settimeout(3)
                with connection:
                    data=b''
                    while len(data)<44:data+=connection.recv(44-len(data))
                    received.append(data)
                    for i in range(8):
                        raw=wire_message(image_message(1,i))
                        for j in range(0,len(raw),37):connection.sendall(raw[j:j+37])
            except Exception as e:errors.append(e)
        worker=threading.Thread(target=server);worker.start()
        source=ChirunoSource(('127.0.0.1',8001),listener.getsockname())
        try:
            deadline=time.monotonic()+3;frame=None
            while frame is None and time.monotonic()<deadline:
                try:frame=source.read()
                except socket.timeout:pass
            self.assertIsNotNone(frame);self.assertEqual(frame.image.size,(400,240))
            with self.assertRaises(ProtocolError):source.read()
        finally:source.close();worker.join(3);listener.close()
        self.assertEqual(received,[b''.join(setup_packets())]);self.assertFalse(errors)

    def test_connecting_mid_pass_discards_prefix_without_publishing(self):
        decoder=ChirunoDecoder()
        for index in (4,5,6,7):self.assertIsNone(decoder.feed(image_message(1,index)))
        frames=[decoder.feed(image_message(1,index)) for index in range(8)]
        self.assertEqual(sum(frame is not None for frame in frames),1)
        with self.assertRaises(ProtocolError):decoder.feed(image_message(1,3))

    def test_partial_packet_timeout_is_not_reinterpreted_as_new_header(self):
        source=ChirunoSource.__new__(ChirunoSource)
        source.tcp=Mock();source.tcp.recv.return_value=b'\x01\x01\x08'
        source.parser=PacketParser();source.decoder=ChirunoDecoder();source.ready=[]
        source.partial_since=time.monotonic()-3;source.read_limit=2
        with self.assertRaises(ProtocolError):source.read()
        source.tcp.recv.assert_not_called()


class HardwareTests(unittest.TestCase):
    def test_socket_success_is_not_coexistence_evidence(self):
        context=hardware_context('ChirunoMod',('127.0.0.1',6464))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(OSError):require_hardware(context,td)
            report=Path(td)/'report.json'
            report.write_text(json.dumps(dict(context=context,status='observed',reported_himem_usum=True,input_probe_completed=True,frames_after_input={'0':3,'1':3})))
            receipt=dict(schema=1,context=context,report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),operator_confirmed_coexistence=True,operator_confirmed_manual_reset_continuity=True,environment=dict(console='Old 3DS LL',luma='13.4',streamer='ChirunoMod 0.2.2',loader='ChLoad_HIMEM',game='Japanese USUM'))
            rp=receipt_path(context,td);rp.write_text(json.dumps(receipt));require_hardware(context,td)
            receipt['operator_confirmed_manual_reset_continuity']=False;rp.write_text(json.dumps(receipt))
            with self.assertRaises(OSError):require_hardware(context,td)
            receipt['operator_confirmed_manual_reset_continuity']=True;rp.write_text(json.dumps(receipt))
            report.write_text('{}')
            with self.assertRaises(OSError):require_hardware(context,td)
        require_hardware(hardware_context('NTR-HR',('127.0.0.1',8000)))

    def test_legacy_settings_keep_ntr_and_new_slots_default_to_chiruno(self):
        from General import General
        with tempfile.TemporaryDirectory() as td:
            general=General.__new__(General);general.settingfolder=Path(td)
            (Path(td)/'USUMShinyHunter-1.txt').write_text('language=English\npcip=127.0.0.1:8001\n')
            settings=general.LoadSetting()
            self.assertEqual(settings[0].backend,'NTR-HR')
            self.assertEqual(settings[1].backend,'ChirunoMod')

    def test_probe_is_passive_by_default_and_only_b_when_explicit(self):
        for send in (False,True):
            with self.subTest(send=send),tempfile.TemporaryDirectory() as td:
                clock=[100.0];count=[0]
                def read():
                    clock[0]+=.1;count[0]+=1;s=count[0]%2
                    image=Image.new('RGB',((320 if s==0 else 400),240),(count[0]%255,80,90))
                    return VideoFrame(s,image,clock[0]-.01,clock[0])
                source=SimpleNamespace(read=read,close=Mock())
                args=SimpleNamespace(output=td,backend='ChirunoMod',console='127.0.0.1',input_port=4950,quality=80,max_span=2,max_age=2,seconds=3,himem_usum=True,local='127.0.0.1',send_b=send)
                with patch('hardware_probe.open_video',return_value=source),patch('hardware_probe.FrameStore',side_effect=lambda:FrameStore(lambda:clock[0])),patch('hardware_probe.time.monotonic',side_effect=lambda:clock[0]),patch('hardware_probe.time.sleep'),patch('hardware_probe.LumaInputServer') as input_class,redirect_stdout(io.StringIO()):
                    result=probe(args)
                self.assertEqual(result,0)
                report=json.loads((Path(td)/'report.json').read_text())
                self.assertFalse(report['controller_effect_verified'])
                self.assertEqual(report['input_probe_completed'],send)
                if send:
                    input_class.return_value.press.assert_called_once_with(HIDButtons.B)
                    input_class.return_value.unpress.assert_called_once_with(HIDButtons.B)
                else:input_class.assert_not_called()
                source.close.assert_called_once()

    def test_failed_stream_stops_probe_without_input(self):
        with tempfile.TemporaryDirectory() as td:
            source=SimpleNamespace(read=Mock(side_effect=OSError('TCP EOF')),close=Mock())
            args=SimpleNamespace(output=td,backend='ChirunoMod',console='127.0.0.1',input_port=4950,quality=80,max_span=2,max_age=2,seconds=3,himem_usum=True,local='127.0.0.1',send_b=True)
            with patch('hardware_probe.open_video',return_value=source),patch('hardware_probe.LumaInputServer') as input_class,redirect_stdout(io.StringIO()):
                self.assertEqual(probe(args),1)
            input_class.assert_not_called()
            report=json.loads((Path(td)/'report.json').read_text())
            self.assertEqual(report['status'],'safe_stop');self.assertIn('TCP EOF',report['error'])

if __name__=='__main__':unittest.main()
