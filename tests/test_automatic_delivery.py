"""Bounded automatic diagnostic tests; synthetic game/recognizer, no console."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw
from automatic_delivery import AutomaticDelivery, recognize, screen_stage, corroborates_receipt, dialogue_visible, receipt_ocr_image
from gift_recognition import SafetyStop
from rehearsal import Rehearsal, DEFAULT_BOXES
from tppflush import HIDButtons
from test_rehearsal import Frames, Controller


def rows(text,confidence=1):return [{'text':text,'confidence':confidence}]


class GameFrames(Frames):
    def snapshot(self,screen,**options):
        from ntr_transport import Frame
        import time
        if self.error:raise OSError(self.error)
        self.serial+=1;now=time.monotonic()
        im=Image.new('RGB',((320 if screen==0 else 400),240),(20+self.state*40,60,90))
        draw=ImageDraw.Draw(im)
        if self.state in (1,2):
            draw.rectangle((20,173,280,225),fill='white')
            draw.text((30,185),f'State {self.state} synthetic text',fill='black')
        else:draw.rectangle((20,20,180,100),fill='white')
        return Frame(im,self.serial,now,now,now)


class GameController(Controller):
    def return_control(self):
        self.step+=1;self.engine.store.state=self.step%5


class GameOCR:
    def __init__(self,engine):self.engine=engine
    def read(self,image,**options):
        return {0:[],1:rows('とあるおかたから ピカチュウをおあずかりしています',.5),
                2:rows('うひは ピカチュウを 受け取った！'),3:[],4:[]}[self.engine.store.state]
    def close(self):pass


def setup(folder):
    engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,folder)
    engine.store=GameFrames()
    engine.record('A',{str(k):v for k,v in DEFAULT_BOXES.items()})
    return engine


def fake_stage(image,stage):
    state=(image.getpixel((0,0))[0]-20)//40
    matched={'field_hud':state==0,'title':state==3,'continue':state==4}[stage]
    return matched,0 if matched else 1,[0,0,image.width,image.height]


class AutomaticTests(unittest.TestCase):
    def test_receipt_preprocessing_keeps_foreground_for_both_polarities(self):
        for background,foreground in (('black','white'),('white','black')):
            image=Image.new('RGB',(40,20),background)
            ImageDraw.Draw(image).rectangle((8,5,10,7),fill=foreground)
            processed=receipt_ocr_image(image)
            self.assertEqual(processed.getpixel((0,0)),255)
            self.assertEqual(processed.getpixel((9,6)),0)

    def test_receipt_resume_requires_explicit_mode_and_permission(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);engine.report.update(automatic_dry_run_verified=True,automatic_ready_state='received')
            runner=AutomaticDelivery(engine)
            with self.assertRaises(SafetyStop):runner.start(True,True,True)
            with self.assertRaises(SafetyStop):runner.start(False,True,True,True)

    def test_receipt_resume_sends_only_reset_start_continue(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);engine.store.state=2
            engine.report.update(automatic_dry_run_verified=True,automatic_ready_state='received')
            fake=GameController(engine);fake.step=2
            with patch('automatic_delivery.MacOCR',side_effect=lambda _:GameOCR(engine)),patch('automatic_delivery.screen_stage',side_effect=fake_stage),patch('automatic_delivery.LumaInputServer',return_value=fake):
                runner=AutomaticDelivery(engine);runner.start(True,True,True,True);engine.player.join(6)
            self.assertFalse(engine.player.is_alive())
            self.assertEqual(fake.down,[HIDButtons.L|HIDButtons.R|HIDButtons.SELECT,HIDButtons.START,HIDButtons.A])
            self.assertEqual(engine.report['controller_packets'],9)
            self.assertEqual(engine.report['completed_cycles'],0)
            self.assertEqual(engine.report['completed_recoveries'],1)

    def test_dialogue_box_is_not_treated_as_an_empty_field(self):
        from PIL import ImageDraw
        image=Image.new('RGB',(400,240),'#305040')
        self.assertFalse(dialogue_visible(image))
        ImageDraw.Draw(image).rectangle((15,170,385,232),fill='white')
        self.assertTrue(dialogue_visible(image))
    def test_receive_requires_past_tense_high_confidence_and_no_quotation(self):
        self.assertEqual(recognize(rows('うひは ピカチュウを 受け取った！'),'receive')[0],'received')
        for text,confidence in [('ピカチュウを受け取った！',.5),('ピカチュウを受け取った？',1),
                                ('「ピカチュウを受け取った！」',1),('ピカチュウを受け取ったら',1),
                                ('ボックスがいっぱい ピカチュウを受け取った',1),('レポートをかきますか',1),
                                ('ピカチュウを逃がしますか',1)]:
            with self.subTest(text=text):self.assertEqual(recognize(rows(text,confidence),'receive')[0],'unknown')
        self.assertEqual(recognize(rows('ピカチュウを受け取りますか'),'receive')[0],'dialogue')
        self.assertNotEqual(recognize(rows('ピカチュウを受け取りますか'),'receive')[0],'received')

    def test_known_menu_templates_reject_blank_frames(self):
        for stage in ('title','continue'):
            for colour in ('white','black'):
                self.assertFalse(screen_stage(Image.new('RGB',(400,240),colour),stage)[0])
    def test_uncorrected_receipt_must_agree_without_question_or_weak_text(self):
        expected='ピカチュウを受け取った'
        self.assertTrue(corroborates_receipt(rows('ピカチュウを受け取った！',.5),expected))
        for text,confidence in [('ピカチュウを受け取った？',1),('ピカチュウを受け取りますか',1),('ピカチュウを受け取った！',.3)]:
            self.assertFalse(corroborates_receipt(rows(text,confidence),expected))

    def test_opt_in_and_dry_run_gate(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);runner=AutomaticDelivery(engine)
            for saved,approved in ((False,False),(True,False),(False,True),(True,True)):
                with self.assertRaises(SafetyStop):runner.start(saved,approved,True)

    def test_dry_run_no_controller_and_automatic_complete_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td)
            with patch('automatic_delivery.MacOCR',side_effect=lambda _:GameOCR(engine)),patch('automatic_delivery.screen_stage',side_effect=fake_stage),patch('automatic_delivery.LumaInputServer') as controller:
                runner=AutomaticDelivery(engine);runner.start();engine.player.join(5)
                self.assertFalse(engine.player.is_alive());controller.assert_not_called()
                self.assertTrue(engine.report['automatic_dry_run_verified'])
                self.assertEqual(engine.report['controller_packets'],0)
            fake=GameController(engine)
            with patch('automatic_delivery.MacOCR',side_effect=lambda _:GameOCR(engine)),patch('automatic_delivery.screen_stage',side_effect=fake_stage),patch('automatic_delivery.LumaInputServer',return_value=fake):
                runner=AutomaticDelivery(engine);runner.start(True,True,True);engine.player.join(9)
            self.assertFalse(engine.player.is_alive())
            self.assertEqual(engine.report['completed_cycles'],1,engine.report)
            self.assertEqual(engine.report['reset_attempts'],1)
            self.assertEqual(fake.down,[HIDButtons.A,HIDButtons.A,HIDButtons.L|HIDButtons.R|HIDButtons.SELECT,HIDButtons.START,HIDButtons.A])
            self.assertEqual(engine.report['controller_packets'],15)
            self.assertFalse(engine.report['shiny_verified'])

    def test_unconfirmed_receipt_never_resets(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);engine.report['automatic_dry_run_verified']=True
            engine.store.state=2;fake=GameController(engine);runner=AutomaticDelivery(engine)
            original=runner.observe
            runner.observe=lambda stage,since,previous='',timeout=25:original(stage,since,previous,timeout=.4)
            ocr=Mock();ocr.read.return_value=rows('ピカチュウを受け取った！',.5)
            with patch('automatic_delivery.MacOCR',return_value=ocr),patch('automatic_delivery.screen_stage',side_effect=fake_stage),patch('automatic_delivery.LumaInputServer',return_value=fake):
                runner.start(True,True,True);engine.player.join(3)
            self.assertTrue(engine.stop.is_set())
            self.assertEqual(fake.down,[]);self.assertEqual(engine.report['reset_attempts'],0)

    def test_lost_stream_and_second_reset_are_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);engine.store.error='TCP closed'
            with patch('automatic_delivery.LumaInputServer') as controller,self.assertRaises(OSError):
                AutomaticDelivery(engine).start()
            controller.assert_not_called()
            runner=AutomaticDelivery(engine);runner.reset_sent=True
            with self.assertRaises(SafetyStop):runner.send('RESET',Image.new('RGB',(400,240)),[0,0,400,240])

    def test_changed_final_receipt_blocks_reset(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);runner=AutomaticDelivery(engine);fake=GameController(engine)
            runner.controller=fake;runner.ocr=Mock()
            runner.ocr.read.return_value=rows('ピカチュウを受け取りますか？')
            with self.assertRaises(SafetyStop):
                runner.send('RESET',engine.store.snapshot(1).image,[15,170,385,232])
            self.assertEqual(fake.down,[]);self.assertEqual(engine.report['reset_attempts'],0)
            self.assertTrue(runner.reset_sent)


if __name__=='__main__':unittest.main()
