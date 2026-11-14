import tempfile
import time
import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from automatic_delivery import AutomaticDelivery
from fixed_delivery import FixedDelivery
from gift_recognition import SafetyStop
from ntr_transport import Frame,FrameStore
from rehearsal import Rehearsal
from tppflush import HIDButtons


class Game:
    def __init__(self):self.state=0;self.serial=0;self.error=None
    def snapshot(self,screen,**options):
        if self.error:raise OSError(self.error)
        self.serial+=1;now=time.monotonic()
        image=Image.new('RGB',((320 if screen==0 else 400),240),(20+self.state*30,60,90))
        draw=ImageDraw.Draw(image)
        box=(20,173,280,225) if self.state==3 else (20,20,180,100)
        draw.rectangle(box,fill='white');draw.text((30,185),'receipt',fill='black')
        return Frame(image,self.serial,now,now,now)


class OCR:
    def __init__(self,game):self.game=game
    def read(self,image,**options):
        if self.game.state==0:return []  # Passive warmup.
        if self.game.state!=3:raise AssertionError('Navigation must not invoke OCR')
        return [{'text':'ピカチュウをもらった！','confidence':1}]
    def close(self):pass


class Controller:
    def __init__(self,game):self.game=game;self.mask=0;self.down=[];self.socket=Mock()
    def press(self,button):self.mask|=button
    def send(self,print_sent=False):
        if self.mask:self.down.append(self.mask)
    def clear_everything(self):self.mask=0
    def return_control(self):self.game.state=(self.game.state+1)%6


class FixedTests(unittest.TestCase):
    def test_preflight_is_passive_and_only_field_start_exists(self):
        with tempfile.TemporaryDirectory() as td:
            engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td);engine.store=Game()
            runner=FixedDelivery(engine)
            with patch('fixed_delivery.LumaInputServer') as controller,patch('fixed_delivery.MacOCR') as ocr:
                runner.start();engine.player.join(2)
            controller.assert_not_called();ocr.assert_not_called()
            self.assertTrue(engine.report['fixed_preflight_verified'])
            self.assertEqual(engine.report['fixed_start'],'field')
            with self.assertRaises(TypeError):runner.start(start='title')
            with self.assertRaises(SafetyStop):runner.start(live=True,saved=True,approved=False)

    def test_timed_buttons_and_only_post_receipt_ocr(self):
        with tempfile.TemporaryDirectory() as td:
            engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td);engine.store=Game()
            FixedDelivery(engine).start();engine.player.join(2)
            controller=Controller(engine.store);delays=[]
            with patch('fixed_delivery.MacOCR',return_value=OCR(engine.store)),patch('fixed_delivery.LumaInputServer',return_value=controller),patch.object(FixedDelivery,'wait',side_effect=lambda seconds,label:delays.append(seconds)):
                runner=FixedDelivery(engine);runner.start(True,True,True);engine.player.join(5)
            self.assertFalse(engine.player.is_alive())
            reset=HIDButtons.L|HIDButtons.R|HIDButtons.SELECT
            self.assertEqual(controller.down,[HIDButtons.A]*3+[reset,HIDButtons.START,HIDButtons.A])
            self.assertEqual(delays,[3,3,3,25,5,12])
            self.assertEqual(engine.report['completed_cycles'],1,engine.report)
            self.assertEqual(engine.report['reset_attempts'],1)

    def test_unknown_received_screen_does_not_reset_or_add_buttons(self):
        with tempfile.TemporaryDirectory() as td:
            engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td);engine.store=Game()
            FixedDelivery(engine).start();engine.player.join(2)
            controller=Controller(engine.store);ocr=Mock();ocr.read.return_value=[{'text':'ビカチュウをもらった！','confidence':1}]
            runner=FixedDelivery(engine);original=runner.observe
            runner.observe=lambda stage,since,timeout=8:original(stage,since,timeout=.3)
            with patch('fixed_delivery.MacOCR',return_value=ocr),patch('fixed_delivery.LumaInputServer',return_value=controller),patch.object(FixedDelivery,'wait'):
                runner.start(True,True,True);engine.player.join(3)
            self.assertEqual(controller.down,[HIDButtons.A]*3)
            self.assertEqual(engine.report['reset_attempts'],0)
            self.assertTrue(engine.stop.is_set())

    def test_transient_origin_age_pauses_inputs_but_transport_silence_stops(self):
        with tempfile.TemporaryDirectory() as td:
            engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td)
            clock=[2.1];engine.store=FrameStore(lambda:clock[0])
            for screen,width in ((0,320),(1,400)):engine.store.put(screen,Image.new('RGB',(width,240)),started=0,completed=1.6)
            self.assertIsNone(engine.recognition_frames());self.assertFalse(engine.stop.is_set())
            controller=Mock()
            with self.assertRaises(OSError):engine.pulse('A',controller)
            controller.send.assert_not_called()
            clock[0]=2.2
            for screen,width in ((0,320),(1,400)):engine.store.put(screen,Image.new('RGB',(width,240),'blue'),started=1.7,completed=2.2)
            self.assertIsNotNone(engine.recognition_frames())
            clock[0]=4.3
            with self.assertRaises(OSError):engine.recognition_frames()


if __name__=='__main__':unittest.main()
