"""Video-only recovery: no real console/network, no old frame or button replay."""
import socket
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from rehearsal import Rehearsal,VideoRecoveryPending
from fixed_delivery import FixedDelivery
from tests.test_reliable_pulse import Controller

class Source:
    startup_retries=0
    def __init__(self,fail_after=None,silent=False):self.count=0;self.fail_after=fail_after;self.silent=silent;self.closed=False
    def read(self):
        time.sleep(.008)
        if self.silent:raise socket.timeout()
        if self.fail_after is not None and self.count>=self.fail_after:raise OSError('ChirunoMod screen assembly exceeded freshness limit')
        screen=self.count%2;self.count+=1;now=time.monotonic()
        return SimpleNamespace(screen=screen,image=Image.new('RGB',((320 if screen==0 else 400),240),(30+self.count%10,70,90)),started=now-.01,completed=now)
    def close(self):self.closed=True

class VideoRecoveryTests(unittest.TestCase):
    def engine(self,directory):return Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,directory)
    def until(self,condition,timeout=4):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if condition():return
            time.sleep(.01)
        self.fail('Timed out waiting for mock video recovery')

    def test_decoder_fault_reconnects_video_only_and_requires_new_pairs(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);e.video_recovery_enabled=True;a=Source(4);b=Source()
            try:
                with patch('rehearsal.open_video',side_effect=[a,b]) as connect:
                    e.connect();self.until(lambda:e.video_generation==1 and not e.video_recovering.is_set())
                    frames=e.healthy()
                    self.assertGreaterEqual(min(f.serial for f in frames.values()),4)
                    self.assertEqual(connect.call_count,2);self.assertTrue(a.closed)
                    self.assertEqual(e.report['controller_packets'],0);self.assertEqual(e.report['reset_attempts'],0)
                    self.assertFalse(e.stop.is_set())
            finally:e.disconnect();e.reader.join(2)

    def test_paused_input_cannot_send_a_button_or_replay_old_navigation(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);e.video_recovery_enabled=True;ir=Controller()
            e.request_video_recovery(OSError('video gap'))
            with self.assertRaises(VideoRecoveryPending):e.pulse('A',ir)
            self.assertEqual(ir.packets,[])
            runner=FixedDelivery(e);runner.actions=0;runner.max_actions=10;runner.controller=ir
            with patch.object(runner,'ready',side_effect=lambda:setattr(e,'video_generation',e.video_generation+1)):
                self.assertFalse(runner.click('A'))
            self.assertEqual(ir.packets,[])

    def test_same_frozen_picture_after_reconnect_is_not_resumed(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);e.video_recovery_enabled=True
            for screen,width in ((0,320),(1,400)):
                now=time.monotonic();e.store.put(screen,Image.new('RGB',(width,240),'green'),now,now)
            e.request_video_recovery(OSError('Frozen screen 1'));e.video_recovery_error=None
            e._resume_video_if_ready({0:2,1:2})
            self.assertTrue(e.video_recovering.is_set())
            now=time.monotonic();e.store.put(0,Image.new('RGB',(320,240),'blue'),now,now)
            e._resume_video_if_ready({0:2,1:2})
            self.assertFalse(e.video_recovering.is_set())
            self.assertEqual(e.report['controller_packets'],0)

    def test_legacy_transport_still_stops_and_keeps_original_error(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td)
            with patch('rehearsal.open_video',return_value=Source(0)) as connect:
                e.connect();e.reader.join(2)
            self.assertTrue(e.stop.is_set());self.assertEqual(connect.call_count,1)
            e.fail('receiver already stopped')
            self.assertIn('assembly exceeded freshness',e.report['status'])

    def test_failed_reconnect_is_bounded_without_controls(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);e.video_recovery_enabled=True;e.video_recovery_limit=2
            with patch('rehearsal.open_video',side_effect=[Source(0),OSError('offline'),OSError('offline')]) as connect:
                e.connect();e.reader.join(3)
            self.assertFalse(e.reader.is_alive());self.assertTrue(e.stop.is_set())
            self.assertEqual(connect.call_count,3);self.assertEqual(e.report['reset_attempts'],0)

    def test_connected_but_silent_replacement_cannot_hold_forever(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);e.video_recovery_enabled=True;e.video_recovery_timeout=.6
            with patch('rehearsal.open_video',side_effect=[Source(0),Source(silent=True)]):
                e.connect();e.reader.join(3)
            self.assertFalse(e.reader.is_alive());self.assertTrue(e.stop.is_set())
            self.assertEqual(e.report['controller_packets'],0)

if __name__=='__main__':unittest.main()
