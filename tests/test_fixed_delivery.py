import tempfile
import time
import unittest
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from fixed_delivery import FixedDelivery
from gift_recognition import SafetyStop
from ntr_transport import Frame,FrameStore
from rehearsal import Rehearsal
from summary_check import check_summary,load_config,summary_buttons
from tppflush import HIDButtons

NAV=summary_buttons(4)
SUMMARY=3+len(NAV)


class Game:
    def __init__(self):self.state=0;self.serial=0;self.error=None
    def snapshot(self,screen,**options):
        if self.error:raise OSError(self.error)
        self.serial+=1;now=time.monotonic();state=self.state%(SUMMARY+3)
        image=Image.new('RGB',((320 if screen==0 else 400),240),(20+state*5,60,90))
        draw=ImageDraw.Draw(image)
        box=(20,173,280,225) if state==3 else (20,20,180,100)
        draw.rectangle(box,fill='white');draw.text((30,185),'receipt',fill='black')
        if state==SUMMARY and screen==0:
            draw.rectangle((59,184,66,191),fill=(129,242,74))
        return Frame(image,self.serial,now,now,now)


class OCR:
    def __init__(self,game):self.game=game
    def read(self,image,**options):
        if self.game.state==0:return []
        if self.game.state==3:return [{'text':'ピカチュウをもらった！','confidence':1}]
        if self.game.state==SUMMARY:return [{'text':text,'confidence':1} for text in ('ピカチュウ','おや サトシ','IDNo. 12345','けいけんち')]
        raise AssertionError('Navigation must not invoke OCR')
    def close(self):pass


class Controller:
    def __init__(self,game):self.game=game;self.mask=0;self.down=[];self.socket=Mock()
    def press(self,button):self.mask|=button
    def send(self,print_sent=False):
        if self.mask:self.down.append(self.mask)
    def clear_everything(self):self.mask=0
    def return_control(self):self.game.state+=1


def setup(td):
    engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td);engine.store=Game()
    FixedDelivery(engine).start();engine.player.join(2)
    return engine


def execute(engine,stop=False,checker=None):
    controller=Controller(engine.store);delays=[]
    with patch('fixed_delivery.MacOCR',return_value=OCR(engine.store)),patch('fixed_delivery.LumaInputServer',return_value=controller),patch.object(FixedDelivery,'wait',side_effect=lambda seconds,label:delays.append(seconds)):
        with patch('fixed_delivery.check_summary',side_effect=checker) if checker else patch('fixed_delivery.check_summary',wraps=check_summary):
            runner=FixedDelivery(engine);runner.start(True,True,True,party_before=4,stop_at_summary=stop);engine.player.join(8)
    return controller,delays


class FixedTests(unittest.TestCase):
    def test_preflight_is_passive_and_only_field_start_exists(self):
        with tempfile.TemporaryDirectory() as td:
            engine=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td);engine.store=Game()
            runner=FixedDelivery(engine)
            with patch('fixed_delivery.LumaInputServer') as controller,patch('fixed_delivery.MacOCR') as ocr:
                runner.start();engine.player.join(2)
            controller.assert_not_called();ocr.assert_not_called()
            self.assertTrue(engine.report['fixed_preflight_verified'])
            self.assertTrue(engine.report['stop_at_summary'])
            self.assertEqual(engine.report['fixed_start'],'field')
            with self.assertRaises(TypeError):runner.start(start='title')
            with self.assertRaises(SafetyStop):runner.start(live=True,saved=True,approved=False)
            for party in (0,6,True,4.0):
                with self.assertRaises(SafetyStop):runner.start(party_before=party)

    def test_timed_buttons_summary_normal_consensus_then_reset(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);controller,delays=execute(engine)
            self.assertFalse(engine.player.is_alive())
            reset=HIDButtons.L|HIDButtons.R|HIDButtons.SELECT
            expected=[HIDButtons.A]*3+[getattr(HIDButtons,b) for b,_ in NAV]+[reset,HIDButtons.START,HIDButtons.A]
            self.assertEqual(controller.down,expected)
            self.assertEqual(delays,[3]*3+[d for _,d in NAV]+[25,5,12])
            self.assertEqual(engine.report['completed_cycles'],1,engine.report)
            self.assertEqual(engine.report['reset_attempts'],1)
            self.assertEqual(engine.report['summary_verdict'],'normal')
            self.assertTrue((engine.directory/'summary-final-reset-check-0.png').exists())

    def test_default_stops_on_normal_summary_without_reset(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);controller,_=execute(engine,stop=True)
            self.assertEqual(len(controller.down),SUMMARY)
            self.assertEqual(engine.report['reset_attempts'],0)
            self.assertEqual(engine.report['summary_verdict'],'normal')
            self.assertEqual(engine.report['completed_cycles'],0)
            self.assertFalse(engine.report['fixed_preflight_verified'])

    def test_shiny_unknown_conflict_and_final_change_never_reset(self):
        for labels in (['shiny']*3,['unknown'],['normal','shiny'],['normal']*3+['shiny']):
            with self.subTest(labels=labels),tempfile.TemporaryDirectory() as td:
                engine=setup(td)
                results=iter({'verdict':label} for label in labels)
                controller,_=execute(engine,checker=lambda *args:next(results))
                self.assertEqual(len(controller.down),SUMMARY)
                self.assertEqual(engine.report['reset_attempts'],0)
                self.assertEqual(engine.report['completed_cycles'],0)

    def test_disconnect_during_summary_never_resets(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td)
            def disconnect(*args):
                engine.store.error='connection lost'
                return {'verdict':'normal'}
            controller,_=execute(engine,checker=disconnect)
            self.assertEqual(engine.report['reset_attempts'],0)
            self.assertEqual(len(controller.down),SUMMARY)
            self.assertTrue(engine.stop.is_set())

    def test_unknown_received_screen_does_not_reset_or_add_buttons(self):
        with tempfile.TemporaryDirectory() as td:
            engine=setup(td);controller=Controller(engine.store)
            ocr=Mock();ocr.read.return_value=[{'text':'ビカチュウをもらった！','confidence':1}]
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


class SummaryTests(unittest.TestCase):
    def test_normal_shiny_unknown_colours_keep_three_states(self):
        config=load_config();ocr=Mock()
        ocr.read.return_value=[{'text':s,'confidence':1} for s in ('ピカチュウ','おや','IDNo')]
        for label,colour in (('normal',config['colour']['normal']),('shiny',config['colour']['shiny']),('unknown',[0,0,0])):
            images={str(screen):Image.new('RGB',((320 if screen==0 else 400),240),(129,242,74)) for screen in (0,1)}
            ImageDraw.Draw(images['0']).rectangle((59,184,66,191),fill=tuple(round(c) for c in colour))
            self.assertEqual(check_summary(images,ocr,config)['verdict'],label)

    def test_colour_without_summary_identity_or_context_is_unknown(self):
        config=load_config();images={'0':Image.new('RGB',(320,240),(129,242,74)),'1':Image.new('RGB',(400,240))}
        ocr=Mock()
        for texts in (('ピカチュウ',),('別のポケモン','おや','IDNo'),('ピカチュウ','つよさをみる')):
            ocr.read.return_value=[{'text':s,'confidence':1} for s in texts]
            self.assertEqual(check_summary(images,ocr,config)['verdict'],'unknown')
        ocr.read.return_value=[{'text':s,'confidence':1} for s in ('ピカチュウ','おや','IDNo')]
        self.assertEqual(check_summary(images,ocr,config)['verdict'],'normal')
        ocr.read.return_value=[{'text':s,'confidence':.4} for s in ('ピカチュウ','おや','IDNo')]
        self.assertEqual(check_summary(images,ocr,config)['verdict'],'unknown')

    def test_each_party_size_has_one_fixed_path_to_last_slot(self):
        for before in range(1,6):
            buttons=[b for b,_ in summary_buttons(before)]
            self.assertEqual(buttons.count('DPADDOWN'),before//2)
            self.assertEqual(buttons.count('DPADRIGHT'),before%2)
            self.assertEqual(buttons[-2:],['A','A'])


if __name__=='__main__':unittest.main()
