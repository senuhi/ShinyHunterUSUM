"""App-loop logic with synthetic frames and mocked input; never a real 3DS."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image,ImageDraw
from app_gift_hunt import AppGiftHunt
from automatic_delivery import recognize
from gift_recognition import SafetyStop
from ntr_transport import Frame
from rehearsal import Rehearsal
from summary_check import summary_buttons
from gift_navigation import NavigationAnchors,ROOT as NAV_ROOT
import json
from tppflush import HIDButtons

NAV=summary_buttons(1);SUMMARY=3+len(NAV);ROUND=SUMMARY+3
PACKETS=7
NAV_MANIFEST=json.loads((NAV_ROOT/'manifest.json').read_text())
FIELD_HUD=Image.open(NAV_ROOT.parent/'Diagnostics/field_hud.png').convert('RGB')

class Game:
    def __init__(self,shiny=False):self.state=0;self.serial=0;self.shiny=shiny
    def snapshot(self,screen,**options):
        now=time.monotonic();self.serial+=1;state=self.state%ROUND
        colour=(30,70,90) if state in (0,13) else (30,130+state*4,160)
        image=Image.new('RGB',((320 if screen==0 else 400),240),colour)
        if screen==0 and state in (0,13):image.paste(FIELD_HUD,(0,0))
        draw=ImageDraw.Draw(image);draw.rectangle((20,20,180,100),fill='white')
        if screen==1 and state in (SUMMARY+1,SUMMARY+2):
            stage='title' if state==SUMMARY+1 else 'continue'
            root=NAV_ROOT.parent/'Diagnostics';item=json.loads((root/'manifest.json').read_text())['stages'][stage]
            with Image.open(root/item['template']) as part:image.paste(part,item['box'][:2])
        if screen==0 and state in (14,15,16):
            kind='menu' if state==14 else 'party'
            for item in NAV_MANIFEST['states'][kind]:
                with Image.open(NAV_ROOT/item['template']) as part:image.paste(part,item['box'][:2])
            if state in (15,16):
                x,y=(3,32) if state==15 else (173,48)
                draw.rectangle((x,y,x+8,y+10),fill=(230,35,20))
        if screen==1 and state==13 and getattr(self,'late_dialogue',False):
            draw.rectangle((15,170,385,235),fill='white')
        if state==SUMMARY and screen==0:
            draw.rectangle((59,184,66,191),fill=(129,242,74))
            if self.shiny:draw.rectangle((47,188,52,193),fill=(210,55,15))
        return Frame(image,self.serial,now,now,now)

class OCR:
    def __init__(self,game,name):self.game=game;self.name=name
    def read(self,image,**options):
        phase=self.game.state%ROUND
        if phase in (0,13):return []
        if phase in (1,2):texts=[self.name+'を受け取りますか？']
        elif phase==3:texts=[self.name+'をもらった！']
        elif phase==17:texts=['つよさをみる']
        elif phase==SUMMARY:texts=[self.name,'現在の経験値','次のレベルまで']
        else:raise AssertionError('No navigation OCR after receipt')
        return [{'text':s,'confidence':1} for s in texts]
    def close(self):pass

class Controller:
    def __init__(self,game):self.game=game;self.mask=0;self.last=0;self.sent_mask=0;self.down=[];self.socket=Mock();self.moves=[]
    def press(self,button):self.mask|=button
    def send(self,print_sent=False):
        if self.mask and self.mask!=self.sent_mask:self.down.append(self.mask);self.last=self.mask
        self.sent_mask=self.mask
    def clear_everything(self):self.mask=0
    def return_control(self):
        if self.last:self.game.state+=1;self.last=0
    def circle_pad_set(self,*args):self.moves.append(args)
    def circle_pad_neutral(self):pass

class AppLoopTests(unittest.TestCase):
    def engine(self,td,shiny=False):
        e=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td);e.store=Game(shiny)
        return e

    def run_case(self,e,target='poipole',cycles=1,stop=False,ocr=None):
        runner=AppGiftHunt(e,target);runner.start();e.player.join(2)
        self.assertTrue(e.report['fixed_preflight_verified'])
        ir=Controller(e.store);ocr=ocr or OCR(e.store,runner.target_name)
        with patch('app_gift_hunt.MacOCR',return_value=ocr),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
            runner.start(True,True,True,stop_at_summary=stop,cycles=cycles);e.player.join(12)
        self.assertFalse(e.player.is_alive(),e.report)
        return ir,runner

    def test_both_targets_complete_two_rounds_in_same_app_worker(self):
        for target in ('poipole','typenull_poni'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as td:
                e=self.engine(td);ir,runner=self.run_case(e,target,cycles=2)
                self.assertEqual(e.report['completed_cycles'],2,e.report)
                self.assertEqual(e.report['reset_attempts'],2)
                self.assertEqual(e.report['controller_packets'],(len(NAV)+6)*PACKETS*2+(18 if target=='typenull_poni' else 0))
                self.assertEqual(len(ir.moves),6 if target=='typenull_poni' else 0)
                self.assertTrue(e.stop.is_set())
                self.assertEqual(e.report['summary_verdict'],'normal')

    def test_continuous_mode_stops_on_shiny_without_reset(self):
        for target in ('poipole','typenull_poni'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as td:
                e=self.engine(td,True);ir,_=self.run_case(e,target,cycles=0)
                self.assertEqual(e.report['summary_verdict'],'shiny',e.report)
                self.assertEqual(e.report['reset_attempts'],0)
                self.assertEqual(e.report['completed_cycles'],0)
                self.assertNotIn(HIDButtons.L|HIDButtons.R|HIDButtons.SELECT,ir.down)

    def test_reconnect_after_consensus_requires_new_consensus_and_keeps_shiny(self):
        for shiny in (False,True):
            with self.subTest(shiny=shiny),tempfile.TemporaryDirectory() as td:
                e=self.engine(td);original=e.event;changed=False
                def event(kind,**details):
                    nonlocal changed
                    original(kind,**details)
                    if not changed and kind=='summary_verdict' and details.get('phase','').endswith('summary-3'):
                        changed=True;e.video_generation+=1;e.store.shiny=shiny
                e.event=event;ir,_=self.run_case(e)
                self.assertTrue(changed)
                self.assertEqual(e.report['reset_attempts'],0 if shiny else 1,e.report)
                self.assertEqual(e.report['summary_verdict'],'shiny' if shiny else 'normal')
                if shiny:self.assertNotIn(HIDButtons.L|HIDButtons.R|HIDButtons.SELECT,ir.down)
                records=[json.loads(x) for x in (e.directory/'events.jsonl').read_text().splitlines()]
                self.assertGreaterEqual(sum(x['event']=='summary_verdict' for x in records),6)

    def test_video_epoch_change_immediately_before_reset_cannot_replay_reset(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);original=e.event;changed=False
            def event(kind,**details):
                nonlocal changed
                original(kind,**details)
                if not changed and kind=='input_attempt' and details.get('button')=='RESET':
                    changed=True;e.video_generation+=1;e.store.shiny=True
            e.event=event;ir,_=self.run_case(e)
            self.assertEqual(e.report['reset_attempts'],0,e.report)
            self.assertEqual(e.report['summary_verdict'],'shiny')
            self.assertNotIn(HIDButtons.L|HIDButtons.R|HIDButtons.SELECT,ir.down)

    def test_info_stop_default_has_no_reset(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);self.run_case(e,stop=True)
            self.assertEqual(e.report['summary_verdict'],'normal')
            self.assertEqual(e.report['reset_attempts'],0)

    def test_final_shiny_pixels_revoke_normal_reset_in_app_mode(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);original=e.event
            def event(kind,**details):
                original(kind,**details)
                if kind=='summary_verdict' and details.get('phase','').endswith('summary-3'):
                    e.store.shiny=True
            e.event=event
            ir,_=self.run_case(e)
            self.assertEqual(e.report['reset_attempts'],0)
            self.assertEqual(e.report['summary_verdict'],'shiny')
            self.assertIn('送信直前',e.report['status'])

    def test_stop_during_dialogue_cleanup_prevents_reset(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            ir=Controller(e.store)
            def wait(seconds,label):
                if label in ('画面の表示待ち','図鑑登録・会話の終了待ち'):e.stop.set()
            with patch('app_gift_hunt.MacOCR',return_value=OCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait',side_effect=wait):
                runner.start(True,True,True,stop_at_summary=False,cycles=0);e.player.join(6)
            self.assertFalse(e.player.is_alive())
            self.assertEqual(e.report['reset_attempts'],0)
            self.assertEqual(ir.down,[HIDButtons.A]*3+[HIDButtons.B])

    def test_star_arriving_after_final_ocr_before_packet_still_blocks_reset(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);event=e.event
            def intercept(kind,**details):
                event(kind,**details)
                if kind=='input_attempt' and details.get('button')=='RESET':e.store.shiny=True
            e.event=intercept
            ir,_=self.run_case(e)
            self.assertEqual(e.report['reset_attempts'],0)
            self.assertNotIn(HIDButtons.L|HIDButtons.R|HIDButtons.SELECT,ir.down)
            self.assertIn('送信直前に星',e.report['status'])

    def test_unconfirmed_receipt_stops_without_reset(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            runner=AppGiftHunt(e);runner.receipt_timeout=.25
            ocr=Mock();ocr.read.return_value=[];ir=Controller(e.store)
            with patch('app_gift_hunt.MacOCR',return_value=ocr),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                runner.start(True,True,True,stop_at_summary=False);e.player.join(3)
            self.assertTrue(e.stop.is_set());self.assertEqual(e.report['reset_attempts'],0)
            self.assertEqual(ir.down,[HIDButtons.A])

    def test_weak_receipt_hint_continues_to_full_summary_checks(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);weak=OCR(e.store,'ベベノム');original=weak.read
            def read(image,**options):
                rows=original(image,**options)
                if e.store.state%ROUND==3:
                    return [dict(row,confidence=.3) for row in rows]
                return rows
            weak.read=read
            ir,_=self.run_case(e,ocr=weak)
            self.assertEqual(ir.down[:3],[HIDButtons.A]*3)
            self.assertEqual(e.report['completed_cycles'],1,e.report)
            self.assertEqual(e.report['reset_attempts'],1)
            self.assertEqual(e.report['summary_verdict'],'normal')

    def test_receipt_uncorrected_disagreement_does_not_block_navigation(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);ocr=OCR(e.store,'ベベノム');original=ocr.read
            def read(image,**options):
                if e.store.state%ROUND==3 and options.get('correction') is False:
                    return [{'text':'読取揺れ','confidence':.3}]
                return original(image,**options)
            ocr.read=read
            self.run_case(e,ocr=ocr)
            self.assertEqual(e.report['completed_cycles'],1,e.report)
            self.assertEqual(e.report['summary_verdict'],'normal')
            self.assertEqual(e.report['reset_attempts'],1)

    def test_receipt_hint_cannot_authorize_reset_on_unknown_summary(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);ocr=OCR(e.store,'ベベノム');original=ocr.read
            def read(image,**options):
                rows=original(image,**options)
                if e.store.state%ROUND==SUMMARY:
                    return [dict(row,text='別のポケモン') if row['text']=='ベベノム' else row for row in rows]
                if e.store.state%ROUND==3:return [dict(row,confidence=.3) for row in rows]
                return rows
            ocr.read=read
            ir,_=self.run_case(e,ocr=ocr)
            self.assertEqual(e.report['summary_verdict'],'unknown',e.report)
            self.assertEqual(e.report['reset_attempts'],0)
            self.assertEqual(e.report['completed_cycles'],0)
            self.assertNotIn(HIDButtons.L|HIDButtons.R|HIDButtons.SELECT,ir.down)

    def test_missed_initial_a_is_retried_from_verified_field_then_completes(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            class DropFirstA(Controller):
                def __init__(self,game):super().__init__(game);self.drops=1
                def return_control(self):
                    if self.last==HIDButtons.A and self.drops:
                        self.drops-=1;self.last=0
                    super().return_control()
            ir=DropFirstA(e.store);runner.start_retry_interval=0
            with patch('app_gift_hunt.MacOCR',return_value=OCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                runner.start(True,True,True,stop_at_summary=False);e.player.join(10)
            self.assertFalse(e.player.is_alive())
            self.assertEqual(e.report['completed_cycles'],1,e.report)
            self.assertEqual(e.report['reset_attempts'],1)
            self.assertEqual(ir.down[:4],[HIDButtons.A]*4)
            self.assertEqual(e.report['controller_packets'],(len(NAV)+7)*PACKETS)

    def test_persistently_unresponsive_start_is_bounded_and_never_resets(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            class DropAll(Controller):
                def return_control(self):self.last=0
            ir=DropAll(e.store);runner.start_retry_interval=0
            with patch('app_gift_hunt.MacOCR',return_value=OCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                runner.start(True,True,True,stop_at_summary=False);e.player.join(6)
            self.assertFalse(e.player.is_alive())
            self.assertEqual(ir.down,[HIDButtons.A]*4)
            self.assertEqual(e.report['reset_attempts'],0)
            self.assertEqual(e.report['completed_cycles'],0)
            self.assertIn('InputRedirection',e.report['status'])

    def test_blank_field_after_dialogue_is_not_treated_as_a_new_start(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            original=e.store.snapshot
            def snapshot(screen,**options):
                frame=original(screen,**options)
                if e.store.state==2:
                    return Frame(e.fixed_baseline[str(screen)].copy(),frame.serial,frame.received,frame.changed,frame.started)
                return frame
            e.store.snapshot=snapshot
            ocr=OCR(e.store,'ベベノム');read=ocr.read
            ocr.read=lambda image,**options: [] if e.store.state==2 else read(image,**options)
            ir=Controller(e.store);runner.start_retry_interval=0;runner.receipt_timeout=.7
            with patch('app_gift_hunt.MacOCR',return_value=ocr),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                runner.start(True,True,True,stop_at_summary=False);e.player.join(3)
            self.assertFalse(e.player.is_alive())
            self.assertEqual(ir.down,[HIDButtons.A]*2)
            self.assertEqual(e.report['reset_attempts'],0)

    def test_late_dialogue_after_x_recovers_without_blind_menu_a(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            class LateDialogue(Controller):
                def __init__(self,game):super().__init__(game);self.failed=False
                def return_control(self):
                    if self.last==HIDButtons.X and not self.failed:
                        self.failed=True;self.game.late_dialogue=True;self.last=0
                    elif self.last==HIDButtons.B and self.game.late_dialogue:
                        self.game.late_dialogue=False;self.last=0
                    super().return_control()
            e.store.late_dialogue=False;ir=LateDialogue(e.store)
            with patch('app_gift_hunt.MacOCR',return_value=OCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                runner.start(True,True,True,stop_at_summary=False);e.player.join(12)
            self.assertFalse(e.player.is_alive())
            self.assertEqual(e.report['completed_cycles'],1,e.report)
            self.assertEqual(e.report['reset_attempts'],1)
            index=ir.down.index(HIDButtons.X)
            self.assertEqual(ir.down[index:index+4],[HIDButtons.X,HIDButtons.B,HIDButtons.X,HIDButtons.A])
            self.assertEqual(e.report['controller_packets'],(len(NAV)+8)*PACKETS)

    def test_dropped_navigation_press_is_retried_in_its_observed_state(self):
        for phase in (13,14,15,16,17):
            with self.subTest(phase=phase),tempfile.TemporaryDirectory() as td:
                e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
                class DropAtPhase(Controller):
                    def __init__(self,game):super().__init__(game);self.dropped=False
                    def return_control(self):
                        if self.game.state==phase and not self.dropped:
                            self.dropped=True;self.last=0
                        super().return_control()
                ir=DropAtPhase(e.store)
                with patch('app_gift_hunt.MacOCR',return_value=OCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                    runner.start(True,True,True,stop_at_summary=False);e.player.join(12)
                self.assertFalse(e.player.is_alive())
                self.assertEqual(e.report['completed_cycles'],1,e.report)
                self.assertEqual(e.report['reset_attempts'],1)
                self.assertEqual(e.report['controller_packets'],(len(NAV)+7)*PACKETS)

    def test_resume_pending_gift_does_not_reset_or_receive_before_summary(self):
        for shiny,late in ((False,False),(True,False),(False,True),(True,True)):
            with self.subTest(shiny=shiny,late=late),tempfile.TemporaryDirectory() as td:
                e=self.engine(td,shiny);source=Path(td)/'previous';source.mkdir()
                for key in ('0','1'):e.store.snapshot(int(key)).image.save(source/f'fixed-baseline-{key}.png')
                (source/'received-message.png').write_bytes(b'receipt evidence')
                (source/'report.json').write_text(json.dumps(dict(mode='app_gift_hunt',target='poipole',round=1,completed_cycles=0,reset_attempts=0,summary_verdict='unknown',summary_scores={'context':[]})))
                e.store.state=13;e.store.late_dialogue=late
                runner=AppGiftHunt(e,resume_directory=source);runner.start();e.player.join(2)
                class ClearDialogue(Controller):
                    def return_control(self):
                        if self.last==HIDButtons.B and self.game.late_dialogue:
                            self.game.late_dialogue=False;self.last=0
                        super().return_control()
                ir=ClearDialogue(e.store)
                with patch('app_gift_hunt.MacOCR',return_value=OCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                    runner.start(True,True,True,stop_at_summary=False);e.player.join(10)
                self.assertFalse(e.player.is_alive())
                self.assertEqual(ir.down[0],HIDButtons.B if late else HIDButtons.X)
                self.assertEqual(e.report['summary_verdict'],'shiny' if shiny else 'normal',e.report)
                self.assertEqual(e.report['reset_attempts'],0 if shiny else 1)
                self.assertEqual(e.report['completed_cycles'],0 if shiny else 1)

    def test_resume_from_party_with_no_selectable_second_slot_restarts_reception_once(self):
        for shiny in (False,True):
            with self.subTest(shiny=shiny),tempfile.TemporaryDirectory() as td:
                e=self.engine(td,shiny);source=Path(td)/'previous';source.mkdir()
                for key in ('0','1'):e.store.snapshot(int(key)).image.save(source/f'fixed-baseline-{key}.png')
                (source/'received-message.png').write_bytes(b'receipt evidence')
                (source/'report.json').write_text(json.dumps(dict(mode='app_gift_hunt',target='poipole',round=1,completed_cycles=0,reset_attempts=0,summary_verdict='unknown',summary_scores={'context':[]})))
                e.store.state=15
                runner=AppGiftHunt(e,resume_directory=source);runner.start();e.player.join(2)
                class OneMemberRecovery(Controller):
                    missing=True
                    rights=0
                    def return_control(self):
                        if self.game.state==15 and self.missing:
                            if self.last==HIDButtons.DPADRIGHT:self.rights+=1;self.last=0
                            elif self.last==HIDButtons.B:
                                self.game.state=13;self.last=0
                                if self.rights>=3:self.missing=False
                        elif self.game.state==13 and self.last==HIDButtons.A:
                            self.game.state=1;self.last=0
                        super().return_control()
                ir=OneMemberRecovery(e.store)
                class PartyOCR(OCR):
                    def read(self,image,**options):
                        if self.game.state==15:return []
                        return super().read(image,**options)
                with patch('app_gift_hunt.MacOCR',return_value=PartyOCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                    runner.start(True,True,True,stop_at_summary=False);e.player.join(12)
                self.assertFalse(e.player.is_alive(),e.report)
                self.assertTrue(ir.down,e.report)
                self.assertEqual(ir.down[0],HIDButtons.B)
                self.assertEqual(ir.rights,3)
                for key in ('0','1'):
                    with Image.open(e.directory/f'fixed-baseline-{key}.png') as image:
                        self.assertEqual(image.convert('RGB').tobytes(),runner.baseline[key].tobytes())
                self.assertEqual(e.report['summary_verdict'],'shiny' if shiny else 'normal',e.report)
                self.assertEqual(e.report['reset_attempts'],0 if shiny else 1)

    def test_old_report_previous_round_normal_does_not_classify_pending_registration(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);source=Path(td)/'previous';source.mkdir()
            for key in ('0','1'):e.store.snapshot(int(key)).image.save(source/f'fixed-baseline-{key}.png')
            (source/'received-message.png').write_bytes(b'receipt evidence')
            (source/'report.json').write_text(json.dumps(dict(mode='app_gift_hunt',target='poipole',round=19,completed_cycles=18,reset_attempts=18,summary_verdict='normal',summary_scores={'context':['experience','next_level']})))
            records=[dict(event='summary_verdict',elapsed=1,phase='round-000018-summary-final-reset-check'),dict(event='input_attempt',elapsed=2,button='RESET'),dict(event='gift_receipt_read',elapsed=3,decision='received')]
            (source/'events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records))
            e.store.state=8
            class RegistrationOCR(OCR):
                def read(self,image,**options):
                    if self.game.state%ROUND==8:return []
                    return super().read(image,**options)
            runner=AppGiftHunt(e,resume_directory=source);runner.start();e.player.join(2);ir=Controller(e.store)
            with patch('app_gift_hunt.MacOCR',return_value=RegistrationOCR(e.store,'ベベノム')),patch('app_gift_hunt.LumaInputServer',return_value=ir),patch.object(runner,'wait'):
                runner.start(True,True,True,stop_at_summary=False);e.player.join(12)
            self.assertFalse(e.player.is_alive(),e.report)
            self.assertEqual(ir.down[0],HIDButtons.B)
            self.assertEqual(e.report['completed_cycles'],1,e.report)
            self.assertEqual(e.report['summary_round'],1)
            self.assertEqual(e.report['reset_attempts'],1)

    def test_resume_rejects_shiny_summary_and_already_reset_sources(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);source=Path(td)/'previous';source.mkdir()
            (source/'received-message.png').write_bytes(b'receipt')
            base=dict(mode='app_gift_hunt',target='poipole',round=1,completed_cycles=0,reset_attempts=0,summary_verdict='unknown',summary_scores={'context':[]})
            for change in ({'summary_verdict':'shiny'},{'reset_attempts':1},{'summary_scores':{'context':['経験値','次のレベル']}},{'target':'typenull_poni'},{'completed_cycles':None},{'completed_cycles':False,'reset_attempts':False}):
                with self.subTest(change=change):
                    (source/'report.json').write_text(json.dumps(dict(base,**change)))
                    runner=AppGiftHunt(e,resume_directory=source);runner.start();e.player.join(2)
                    with patch('app_gift_hunt.LumaInputServer') as ir,self.assertRaises(SafetyStop):
                        runner.start(True,True,True,stop_at_summary=False)
                    ir.assert_not_called()
                    self.assertEqual(e.report['controller_packets'],0)

    def test_first_registration_needs_more_than_ten_b_before_menu(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            # A long registration stays off-field for 18 B presses. Only then
            # can three distinct field frames release the Summary navigation.
            original=e.store.snapshot
            def snapshot(screen,**options):
                frame=original(screen,**options)
                image=runner.baseline['1'].copy() if e.store.state>=18 else Image.new('RGB',frame.image.size,'blue')
                return Frame(image,frame.serial,frame.received,frame.changed,frame.started)
            e.store.snapshot=snapshot
            runner.baseline=e.fixed_baseline;runner.actions=0;runner.max_actions=100
            runner.controller=Controller(e.store)
            with patch.object(runner,'wait'):
                runner.clear_receipt()
            self.assertEqual(runner.controller.down,[HIDButtons.B]*18)
            self.assertEqual(e.report['reset_attempts'],0)
            self.assertEqual(e.report['controller_packets'],18*PACKETS)

    def test_registration_timeout_does_not_open_menu_or_reset(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e);runner.start();e.player.join(2)
            runner.baseline={'1':e.fixed_baseline['1'].copy()}
            runner.baseline['1'].paste('white',(0,120,400,240))
            runner.actions=0;runner.max_actions=100;runner.controller=Controller(e.store)
            with patch.object(runner,'wait'),self.assertRaises(SafetyStop):
                runner.clear_receipt(timeout=.05)
            self.assertTrue(runner.controller.down)
            self.assertTrue(all(button==HIDButtons.B for button in runner.controller.down))
            self.assertEqual(e.report['reset_attempts'],0)

    def test_start_guards_and_target_receipt_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            e=self.engine(td);runner=AppGiftHunt(e)
            with self.assertRaises(SafetyStop):runner.start(True,True,True)
            with self.assertRaises(SafetyStop):runner.start(party_before=4)
            for cycles in (-1,True,1.0):
                with self.assertRaises(SafetyStop):runner.start(cycles=cycles)
            rows=lambda s:[{'text':s,'confidence':1}]
            self.assertEqual(runner.receipt_kind(rows('ベベノムをもらった！'))[0],'received')
            self.assertEqual(runner.receipt_kind(rows('ベベノムの データが 新しく ポケモン図鑑に 登録されます！'))[0],'received')
            self.assertEqual(runner.receipt_kind(rows('ベベノムは手持ちに加わった！'))[0],'received')
            for text in ('ベベノムを受け取りますか？','タイプ：ヌルをもらった！','ベベノムをもらった？'):
                self.assertEqual(runner.receipt_kind(rows(text))[0],'unknown')

if __name__=='__main__':unittest.main()
