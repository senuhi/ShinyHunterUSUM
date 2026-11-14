"""Synthetic fixtures exercise logic only; they do NOT validate Japanese game footage."""
import copy
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image, ImageDraw
from gift_recognition import Profile, SafetyStop, colour_verdict, template_score, TARGETS
from gift_hunt import Evidence, GiftRunner, run_gift
from ntr_transport import Frame
from tppflush import HIDButtons
from platform_support import lock_slot

ROOT=Path(__file__).resolve().parents[1]


def fixture(folder, language='Japanese', target='poipole'):
    code='ja' if language=='Japanese' else 'en'
    doc=json.loads((ROOT/'profiles'/f'{code}.json').read_text())
    doc['template_root']='assets'
    # Unique nonblank synthetic artwork, not Japanese game assets.
    assets=folder/'assets';assets.mkdir(exist_ok=True)
    for stage in doc['targets'][target]['stages'].values():
        w=stage['box'][2]-stage['box'][0];h=stage['box'][3]-stage['box'][1]
        for filename in stage['templates']:
            p=assets/filename
            if not p.exists():
                image=Image.new('L',(min(w,11),h),255)
                d=ImageDraw.Draw(image)
                for x in range(image.width):
                    for y in range(image.height):
                        if (x*7+y*13+(3 if code=='ja' else 0))%5<2:d.point((x,y),fill=0)
                image.save(p)
    # Same name used upstream at dialogue and party positions, both 12px high.
    path=folder/f'{code}.json';path.write_text(json.dumps(doc))
    profile=Profile(language,target,path)
    return profile


def screen_for(profile, verdict='normal'):
    image=Image.new('RGB',(320,240),'#222222')
    stage=profile.data['stages']['party_name']
    image.paste(profile.templates['party_name'][0],tuple(stage['box'][:2]))
    config=profile.data['colour']
    colour=config.get(verdict,[0,0,0])
    ImageDraw.Draw(image).rectangle((config['box'][0],config['box'][1],config['box'][2]-1,config['box'][3]-1),fill=tuple(round(x) for x in colour))
    return image


class LiveFrames:
    def __init__(self,image):self.image=image;self.serial=0;self.error=None;self.lock=threading.Lock();self.frames={}
    def snapshot(self,screen,**kwargs):
        if self.error:raise OSError(self.error)
        self.serial+=1
        return Frame(self.image.copy(),self.serial,time.monotonic(),time.monotonic())


def runner_for(folder,profile,dry=True):
    frames=LiveFrames(screen_for(profile))
    general=SimpleNamespace(frames=frames,stop_event=threading.Event(),shotpath=folder,
                            RoundStartHook=None,CounterPlusOne=Mock(),ConnectState=Mock())
    ir=SimpleNamespace(press=Mock(),unpress=Mock(),send=Mock(),clear_everything=Mock(),
                       return_control=Mock(),circle_pad_set=Mock(),circle_pad_neutral=Mock())
    tab=SimpleNamespace(General=general,ir=ir,msgbox=SimpleNamespace(MsgAppend=Mock()))
    runner=GiftRunner(tab,profile,dry)
    runner.pause=lambda seconds:runner.healthy()
    return runner


class ProfileTests(unittest.TestCase):
    def test_all_six_language_target_profiles_are_separate(self):
        for language in ('Japanese','English'):
            for target in TARGETS:
                with self.subTest(language=language,target=target),tempfile.TemporaryDirectory() as td:
                    profile=fixture(Path(td),language,target)
                    profile.require_ready()
                    score,ok=profile.score('party_name',screen_for(profile))
                    self.assertTrue(ok);self.assertEqual(score,0)
                    for label in ('normal','shiny','unknown'):
                        self.assertEqual(colour_verdict(screen_for(profile,label),profile.data['colour'])['verdict'],label)

    def test_real_english_template_matches_with_upstream_offsets(self):
        profile=Profile('English','poipole')
        stage=profile.data['stages']['dialogue_name']
        image=Image.new('RGB',(400,240),'white')
        image.paste(profile.templates['dialogue_name'][0],(110,193))
        self.assertTrue(profile.score('dialogue_name',image)[1])

    def test_japanese_placeholders_fail_closed_no_english_fallback(self):
        profile=Profile('Japanese','poipole')
        self.assertTrue(profile.missing)
        with self.assertRaises(SafetyStop):profile.require_ready()
        with self.assertRaises(SafetyStop):profile.require_ready(live=True)

    def test_blank_template_and_invalid_crop_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            profile=fixture(Path(td))
            p=profile.assets/profile.data['stages']['party_name']['templates'][0];Image.new('L',(11,12),255).save(p)
            with self.assertRaises(SafetyStop):Profile('Japanese','poipole',profile.path)
        with self.assertRaises(SafetyStop):template_score(Image.new('RGB',(320,240)),[-1,0,10,12],Image.new('L',(10,12)))

    def test_live_receipt_bound_to_profile_and_assets(self):
        with tempfile.TemporaryDirectory() as td:
            profile=fixture(Path(td))
            with self.assertRaises(SafetyStop):profile.require_ready(live=True)
            receipt=profile.path.parent/'ja-poipole.validated.json'
            receipt.write_text(json.dumps(dict(profile_sha256=profile.digest,hardware_verified=True,target='poipole',evidence='SYNTHETIC TEST ONLY')))
            profile.require_ready(live=True)
            p=profile.assets/profile.data['stages']['party_name']['templates'][0];im=Image.open(p).copy();im.putpixel((0,0),127);im.save(p)
            with self.assertRaises(SafetyStop):Profile('Japanese','poipole',profile.path).require_ready(live=True)

    def test_invalid_colour_thresholds_do_not_become_normal(self):
        profile=Profile('English','poipole');config=copy.deepcopy(profile.data['colour'])
        for key,value in [('max_distance',float('nan')),('min_margin',0),('max_distance',2),('normal',config['shiny'])]:
            bad=copy.deepcopy(config);bad[key]=value
            with self.subTest(key=key),self.assertRaises(SafetyStop):colour_verdict(screen_for(profile),bad)

    def test_evidence_directories_unique_with_identical_clock(self):
        with tempfile.TemporaryDirectory() as td:
            profile=fixture(Path(td))
            with patch('gift_hunt.datetime') as clock:
                clock.now.return_value.strftime.return_value='SAME-TIMESTAMP-'
                first=Evidence(td,profile);second=Evidence(td,profile)
            self.assertNotEqual(first.directory,second.directory)
            first.record('test');second.record('test')

    def test_platform_lock_is_exclusive_and_released(self):
        with tempfile.TemporaryDirectory() as td:
            first=lock_slot(td,1)
            self.assertIsNotNone(first);self.assertIsNone(lock_slot(td,1))
            first.close();second=lock_slot(td,1);self.assertIsNotNone(second);second.close()


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.profile=fixture(self.folder)
    def tearDown(self):self.temp.cleanup()

    def assert_no_reset(self,runner):
        self.assertNotIn(unittest.mock.call(HIDButtons.SELECT),runner.tab.ir.press.call_args_list)

    def test_dry_run_sends_zero_packets_including_normal_verdict(self):
        runner=runner_for(self.folder,self.profile)
        result=runner.run()
        self.assertIn('normal',result);runner.tab.ir.send.assert_not_called()
        with self.assertRaises(SafetyStop):runner.reset()
        runner.tab.ir.send.assert_not_called();self.assert_no_reset(runner)

    def test_unknown_and_lost_anchor_stop(self):
        for kind in ('unknown','lost_anchor'):
            runner=runner_for(self.folder,self.profile,False)
            runner.frames.image=screen_for(self.profile,'unknown') if kind=='unknown' else Image.new('RGB',(320,240))
            with self.subTest(kind=kind),self.assertRaises(SafetyStop):runner.classify()
            self.assertIsNone(runner.normal_token);self.assert_no_reset(runner)

    def test_stale_frozen_and_network_error_stop_before_reset(self):
        for message in ('Stale screen','Frozen screen','Network disconnected'):
            runner=runner_for(self.folder,self.profile,False)
            runner.normal_token=runner.frames.snapshot(0);runner.frames.error=message
            with self.subTest(message=message),self.assertRaises(OSError):runner.reset()
            runner.tab.ir.send.assert_not_called();self.assert_no_reset(runner)

    def test_conflicting_fresh_frames_stop(self):
        runner=runner_for(self.folder,self.profile,False)
        with patch('gift_hunt.colour_verdict',side_effect=[dict(verdict='normal'),dict(verdict='shiny')]):
            with self.assertRaises(SafetyStop):runner.classify()
        self.assertIsNone(runner.normal_token);self.assert_no_reset(runner)

    def test_no_normal_ticket_and_expired_ticket_never_reset(self):
        runner=runner_for(self.folder,self.profile,False)
        with self.assertRaises(SafetyStop):runner.reset()
        runner.normal_token=Frame(runner.frames.image,1,time.monotonic()-10,time.monotonic())
        with self.assertRaises(SafetyStop):runner.reset()
        self.assert_no_reset(runner)

    def test_changed_final_verdict_never_resets(self):
        runner=runner_for(self.folder,self.profile,False);runner.classify()
        runner.frames.image=screen_for(self.profile,'shiny')
        with self.assertRaises(SafetyStop):runner.reset()
        self.assert_no_reset(runner)

    def test_normal_consensus_authorizes_one_reset_only(self):
        runner=runner_for(self.folder,self.profile,False)
        self.profile.require_ready=Mock()
        runner.wait_stage=Mock()
        runner.classify();runner.reset()
        runner.tab.ir.press.assert_any_call(HIDButtons.SELECT)
        self.assertIsNone(runner.normal_token)
        self.assertEqual([c.args[0] for c in runner.wait_stage.call_args_list],['restart_title','save_file'])
        with self.assertRaises(SafetyStop):runner.reset()

    def test_navigation_timeout_saves_image_and_never_resets(self):
        runner=runner_for(self.folder,self.profile,False)
        self.profile.data['stages']['party_name']['attempts']=2
        runner.frames.image=Image.new('RGB',(320,240))
        with self.assertRaises(SafetyStop):runner.wait_stage('party_name',HIDButtons.A)
        self.assertTrue(list(runner.evidence.directory.glob('*timeout.png')))
        self.assert_no_reset(runner)

    def test_route_specific_steps_and_no_startup_reset(self):
        for target in TARGETS:
            with tempfile.TemporaryDirectory() as td:
                profile=fixture(Path(td),target=target);runner=runner_for(Path(td),profile,False)
                runner.wait_stage=Mock();runner.click=Mock();runner.receive()
                stages=[c.args[0] for c in runner.wait_stage.call_args_list]
                self.assertEqual(stages[0],'dialogue_name')
                self.assertEqual('party_added' in stages,target!='typenull_poni')
                self.assertEqual('dialogue_end' in stages,target!='poipole')
                self.assert_no_reset(runner)

    def test_poipole_and_poni_receipt_prefix_matches_preserved_upstream(self):
        from Recv import Recv
        for index,target in ((0,'poipole'),(1,'typenull_poni')):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as td:
                legacy=SimpleNamespace(cpad=Mock(),wait_for=Mock(return_value=1),
                    check_summary=Mock(return_value=(0,None)),lab=[object(),object()],ty=object(),be=object())
                legacy.nav_dialogue=lambda poke,game:Recv.nav_dialogue(legacy,poke,game)
                with patch('Recv.time.sleep') as sleeper:Recv.findrecv(legacy,index,1)
                legacy_buttons=[call.kwargs['button'] for call in legacy.wait_for.call_args_list]
                profile=fixture(Path(td),target=target);runner=runner_for(Path(td),profile,False)
                runner.wait_stage=Mock();runner.click=Mock();runner.receive()
                self.assertEqual([c.args[1] for c in runner.wait_stage.call_args_list[:2]],legacy_buttons)
                self.assertEqual([c.args[0] for c in runner.wait_stage.call_args_list[:2]],
                    ['dialogue_name','party_added' if index==0 else 'dialogue_end'])
                self.assertEqual([c.args[0] for c in runner.click.call_args_list],
                    [HIDButtons.B]*10+[HIDButtons.DPADRIGHT,HIDButtons.A,HIDButtons.A])
                self.assertEqual(runner.wait_stage.call_args_list[-1].args,('party_name',))
                if index==1:
                    self.assertEqual(legacy.cpad.call_args_list,[unittest.mock.call(1.0,0.0),unittest.mock.call(0.0,0.0)]*3)
                    self.assertEqual(sleeper.call_args_list,[unittest.mock.call(.1)]*3)
                    self.assertEqual(runner.tab.ir.circle_pad_set.call_count,3)
                    self.assertEqual(runner.tab.ir.circle_pad_neutral.call_count,3)
                    self.assertEqual(profile.data['approach'],{'x':1.0,'seconds':.1,'repeats':3})
                else:
                    legacy.cpad.assert_not_called();runner.tab.ir.circle_pad_set.assert_not_called()
                self.assert_no_reset(runner)

    def test_shiny_candidate_stops_without_startup_reset(self):
        runner=runner_for(self.folder,self.profile,False)
        self.profile.require_ready=Mock()
        runner.receive=Mock();runner.classify=Mock(return_value='shiny');runner.reset=Mock()
        self.assertIn('Shiny candidate',runner.run())
        runner.receive.assert_called_once();runner.reset.assert_not_called()
        runner.tab.ir.send.assert_not_called()

    def test_missing_live_calibration_blocks_before_any_navigation(self):
        runner=runner_for(self.folder,self.profile,False)
        runner.receive=Mock()
        with self.assertRaises(SafetyStop):runner.run()
        runner.receive.assert_not_called();runner.tab.ir.send.assert_not_called()

    def test_chiruno_coexistence_gate_blocks_live_start_and_reset(self):
        for action in ('run','reset'):
            runner=runner_for(self.folder,self.profile,False)
            runner.general.video_backend='ChirunoMod'
            runner.general.hardware_context={'backend':'ChirunoMod'}
            self.profile.require_ready=Mock()
            runner.receive=Mock()
            if action=='reset':runner.classify()
            with patch('gift_hunt.require_hardware',side_effect=OSError('HIMEM not verified')):
                with self.assertRaises(OSError):getattr(runner,action)()
            runner.receive.assert_not_called();self.assert_no_reset(runner)

    def test_ntr_calibration_receipt_cannot_enable_chiruno(self):
        receipt=self.profile.path.parent/'ja-poipole.validated.json'
        data=dict(profile_sha256=self.profile.digest,hardware_verified=True,target='poipole',evidence='SYNTHETIC TEST ONLY',video_backend='NTR-HR')
        receipt.write_text(json.dumps(data))
        with self.assertRaises(SafetyStop):self.profile.require_ready(live=True,backend='ChirunoMod')
        data['video_backend']='ChirunoMod';receipt.write_text(json.dumps(data))
        self.profile.require_ready(live=True,backend='ChirunoMod')

    def test_exception_wrapper_releases_and_does_not_retry(self):
        runner=runner_for(self.folder,self.profile,False)
        with patch('gift_hunt.GiftRunner.run',side_effect=OSError('injected receive failure')):
            run_gift(runner.tab,'Japanese',0,False,self.profile.path)
        self.assertTrue(runner.general.stop_event.is_set())
        self.assert_no_reset(runner);runner.tab.ir.return_control.assert_called_once()

if __name__=='__main__':unittest.main()
