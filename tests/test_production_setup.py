"""Offline preparations only; no receiver/controller or real reference images."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from PIL import Image
from production_setup import DEFAULT_PARTY_BEFORE,PRODUCTION_TARGETS,preparation,summary_profile
from summary_check import check_summary,load_config,replay_summary,summary_buttons
from gift_recognition import SafetyStop
from gift_hunt import run_gift


class ProductionPreparationTests(unittest.TestCase):
    def test_two_routes_one_member_and_upstream_receipt_flows(self):
        plan=preparation()
        self.assertEqual(DEFAULT_PARTY_BEFORE,1)
        self.assertEqual(set(plan['targets']),{'poipole','typenull_poni'})
        self.assertEqual(plan['received_slot'],2)
        self.assertEqual(summary_buttons(1)[-3:],[('DPADRIGHT',1),('A',1),('A',3)])
        self.assertTrue(plan['dry_run_default'])
        self.assertFalse(plan['body_can_authorize_reset'])
        self.assertEqual(plan['navigation'],'upstream_recv')
        self.assertEqual(plan['targets']['typenull_poni']['approach'],{'x':1.0,'seconds':.1,'repeats':3})
        self.assertEqual(plan['targets']['poipole']['start'],'facing_gift_npc_no_dialogue')
        self.assertEqual(plan['targets']['typenull_poni']['start'],'left_of_event_trigger')
        with self.assertRaises(SafetyStop):summary_profile('typenull_aether')

    def test_both_target_names_and_colon_variants_on_summary(self):
        for target,label in [('poipole','ベベノム'),('typenull_poni','タイプ:ヌル')]:
            config=load_config(summary_profile(target))
            images={'0':Image.new('RGB',(320,240),(129,242,74)),'1':Image.new('RGB',(400,240))}
            ocr=Mock();ocr.read.return_value=[{'text':s,'confidence':1} for s in (label,'現在の経験値','次のレベルまで')]
            self.assertEqual(check_summary(images,ocr,config)['verdict'],'normal')
            ocr.read.return_value=[{'text':'別のポケモン','confidence':1},{'text':'現在の経験値','confidence':1},{'text':'次のレベルまで','confidence':1}]
            self.assertEqual(check_summary(images,ocr,config)['verdict'],'unknown')

    def test_saved_pair_replay_can_never_authorize_reset(self):
        with tempfile.TemporaryDirectory() as td:
            upper=Path(td)/'upper.png';lower=Path(td)/'lower.png'
            Image.new('RGB',(400,240),'white').save(upper)
            Image.new('RGB',(320,240),(129,242,74)).save(lower)
            ocr=Mock();ocr.read.return_value=[{'text':s,'confidence':1} for s in ('タイプ：ヌル','現在の経験値','次のレベルまで')]
            result=replay_summary('typenull_poni',upper,lower,ocr)
            self.assertEqual(result['verdict'],'normal')
            self.assertEqual(result['controller_packets'],0)
            self.assertFalse(result['reset_authorized'])
            self.assertIn('UNVERIFIED',result['calibration_status'])
            Image.new('RGB',(1200,720)).save(upper);ocr.reset_mock()
            with self.assertRaises(SafetyStop):replay_summary('typenull_poni',upper,lower,ocr)
            ocr.read.assert_not_called()

    def test_low_score_name_requires_both_screens_and_uncorrected_agreement(self):
        config=load_config(summary_profile('poipole'))
        images={'0':Image.new('RGB',(320,240),(129,242,74)),'1':Image.new('RGB',(400,240))}
        name={'text':'ベベノム','confidence':.3}
        fields=[{'text':'現在の経験値','confidence':1},{'text':'次のレベルまで','confidence':1}]
        ocr=Mock();ocr.read.side_effect=[[name]+fields,[name]+fields,[name],[name]]
        result=check_summary(images,ocr,config)
        self.assertEqual(result['verdict'],'normal')
        self.assertEqual(result['name_verification'],'dual_screen_exact_uncorrected')
        ocr.read.side_effect=[[name]+fields,fields]
        self.assertEqual(check_summary(images,ocr,config)['verdict'],'unknown')
        wrong={'text':'別のポケモン','confidence':1}
        ocr.read.side_effect=[[name]+fields,[name]+fields,[wrong],[name]]
        self.assertEqual(check_summary(images,ocr,config)['verdict'],'unknown')

    def test_japanese_aether_hidden_scope_also_blocks_programmatic_runner(self):
        tab=Mock();tab.ir=None
        with patch('gift_hunt.GiftRunner') as runner:
            run_gift(tab,'Japanese',2,True)
        runner.assert_not_called()
        self.assertIn('2ルート',tab.msgbox.MsgAppend.call_args[0][0])


if __name__=='__main__':unittest.main()
