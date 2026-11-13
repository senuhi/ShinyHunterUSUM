import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw
from gift_recognition import SafetyStop
from ntr_transport import Frame
from rehearsal import Rehearsal, DEFAULT_BOXES, validate_trace
from tppflush import HIDButtons


def artwork(screen, state):
    image=Image.new('RGB',((320 if screen==0 else 400),240),
                    ['#204070','#902030','#208030','#805020'][state])
    draw=ImageDraw.Draw(image)
    draw.rectangle((20,20,150,70),fill='white')
    draw.text((30,30),f'Synthetic state {state}',fill='black')
    return image


class Frames:
    def __init__(self):self.state=0;self.serial=0;self.error=None
    def snapshot(self,screen,**options):
        if self.error:raise OSError(self.error)
        self.serial+=1;now=time.monotonic()
        return Frame(artwork(screen,self.state),self.serial,now,now,now)


def prepared(directory, notify=lambda *args:None):
    engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,directory,notify)
    engine.store=Frames()
    for state, button in enumerate(('A','RESET','START','A')):
        engine.store.state=state
        engine.record(button,{str(k):b for k,b in DEFAULT_BOXES.items()},button=='RESET')
    engine.store.state=0
    engine.finish_recording({str(k):b for k,b in DEFAULT_BOXES.items()})
    return engine


class Controller:
    def __init__(self,engine):
        self.engine=engine;self.pressed=0;self.down=[];self.step=0;self.socket=Mock()
    def press(self,button):self.pressed|=button
    def clear_everything(self):self.pressed=0
    def send(self,print_sent=False):
        if self.pressed:self.down.append(self.pressed)
    def return_control(self):
        self.step+=1;self.engine.store.state=self.step%4


class RehearsalTests(unittest.TestCase):
    def test_recording_and_confirmation_never_construct_controller(self):
        with tempfile.TemporaryDirectory() as td,patch('rehearsal.LumaInputServer') as controller:
            engine=prepared(td)
            self.assertEqual(engine.report['controller_packets'],0)
            self.assertFalse(engine.passive_verified)
            self.assertTrue((engine.directory/'trace.json').is_file())
            self.assertTrue((engine.directory/'trace-draft.json').is_file())
        controller.assert_not_called()

    def test_live_needs_save_permission_and_completed_passive_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td)
            for saved,approved in ((False,False),(True,False),(False,True),(True,True)):
                with self.subTest(saved=saved,approved=approved),self.assertRaises(SafetyStop):
                    engine.play(1,live=True,saved=saved,approved=approved)
            engine.passive_verified=True
            with self.assertRaises(SafetyStop):engine.play(4,live=True,saved=True,approved=True)

    def test_passive_full_cycle_uses_manual_ack_and_zero_network_input(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td)
            def notify(kind,value):
                if kind=='manual_ready' and value:
                    engine.store.state=(engine.store.state+1)%4;engine.manual_next.set()
            engine.notify=notify
            with patch('rehearsal.LumaInputServer') as controller:
                engine.play();engine.player.join(4)
            self.assertFalse(engine.player.is_alive());controller.assert_not_called()
            self.assertEqual(engine.report['completed_cycles'],1)
            self.assertEqual(engine.report['controller_packets'],0)
            self.assertTrue(engine.passive_verified)

    def test_live_three_cycle_budget_and_final_screen_checks(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td);engine.passive_verified=True
            controller=Controller(engine)
            with patch('rehearsal.LumaInputServer',return_value=controller):
                engine.play(3,True,True,True);engine.player.join(6)
            self.assertFalse(engine.player.is_alive())
            self.assertEqual(engine.report['completed_cycles'],3)
            self.assertEqual(engine.report['reset_attempts'],3)
            self.assertEqual(engine.report['controller_packets'],36)
            reset=HIDButtons.L|HIDButtons.R|HIDButtons.SELECT
            self.assertEqual(controller.down,[HIDButtons.A,reset,HIDButtons.START,HIDButtons.A]*3)
            self.assertFalse(engine.report['shiny_verified'])

    def test_unknown_screen_stops_without_any_press_or_reset(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td);engine.passive_verified=True;engine.store.state=2
            controller=Controller(engine);original=engine._wait_match
            engine._wait_match=lambda step,since:original(step,since,timeout=.15)
            with patch('rehearsal.LumaInputServer',return_value=controller):
                engine.play(1,True,True,True);engine.player.join(2)
            self.assertTrue(engine.stop.is_set());self.assertEqual(controller.down,[])
            self.assertEqual(engine.report['reset_attempts'],0)

    def test_stale_video_is_rejected_before_start(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td);engine.passive_verified=True;engine.store.error='stale video'
            with patch('rehearsal.LumaInputServer') as controller,self.assertRaises(OSError):
                engine.play(1,True,True,True)
            controller.assert_not_called()

    def test_reset_requires_received_checkpoint_and_distinct_image(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td)
            engine.trace['steps'][1]['received_confirmed']=False
            with self.assertRaises(SafetyStop):validate_trace(engine.trace,engine.directory)
            engine.trace['steps'][1]['received_confirmed']=True
            engine.trace['steps'][1]['references']=engine.trace['steps'][0]['references']
            with self.assertRaises(SafetyStop):validate_trace(engine.trace,engine.directory)

    def test_bad_actions_paths_and_blank_templates_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td);original=json.loads(json.dumps(engine.trace))
            engine.trace['steps'][0]['button']='HOME'
            with self.assertRaises(SafetyStop):validate_trace(engine.trace,engine.directory)
            engine.trace=original
            engine.trace['steps'][0]['boxes']={'0':DEFAULT_BOXES[0]}
            engine.trace['steps'][0]['references']['1']='../outside.png'
            with self.assertRaises(SafetyStop):validate_trace(engine.trace,engine.directory)

    def test_loaded_recording_copies_images_and_invalidates_passive_verification(self):
        with tempfile.TemporaryDirectory() as td:
            engine=prepared(td);other=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td)
            other.passive_verified=True;other.load(engine.directory/'trace.json')
            self.assertFalse(other.passive_verified)
            self.assertEqual(other.trace_directory,other.directory)
            validate_trace(other.trace,other.directory)
            for step in other.trace['steps']:
                self.assertTrue(all((other.directory/f).is_file() for f in step['references'].values()))


if __name__=='__main__':unittest.main()
