import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image
from chiruno_transport import VideoFrame
from reset_probe import input_plan, run
from tppflush import HIDButtons, N3DS_Buttons, Special_Buttons, LumaInputServer


class ResetProbeTests(unittest.TestCase):
    def test_dry_run_never_connects_and_reset_has_only_l_r_select(self):
        with patch('socket.create_connection') as network, redirect_stdout(io.StringIO()):
            self.assertEqual(run(SimpleNamespace(execute=False)), 0)
        network.assert_not_called()
        plan=input_plan()
        raw=bytes.fromhex(plan['packets']['RESET'][0])
        pressed=(~int.from_bytes(raw[:4], 'little')) & 0xffffffff
        self.assertEqual(pressed, int(HIDButtons.L | HIDButtons.R | HIDButtons.SELECT))
        self.assertEqual(raw[16:], bytes(4))
        self.assertTrue(all(len(bytes.fromhex(p))==20 for packets in plan['packets'].values() for p in packets))

    def test_live_requires_explicit_acceptance_before_connecting(self):
        with patch('reset_probe.ChirunoSource') as video:
            with self.assertRaises(ValueError):
                run(SimpleNamespace(execute=True, accept_unsaved=False))
        video.assert_not_called()

    def test_unknown_pre_reset_screen_sends_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); reference=root/'field.png'; Image.new('RGB',(320,240),'blue').save(reference)
            counter=[0]
            def read():
                counter[0]+=1; screen=counter[0]%2; now=time.monotonic()
                return VideoFrame(screen,Image.new('RGB',((320 if screen==0 else 400),240),'red'),now,now)
            source=SimpleNamespace(read=read, close=Mock())
            args=SimpleNamespace(execute=True,accept_unsaved=True,initial_reference=str(reference),output=str(root/'probe'),local='127.0.0.1',console='127.0.0.1',quality=50,input_port=4950,seconds=2)
            plan=input_plan()
            with patch('reset_probe.input_plan',return_value=plan),patch('reset_probe.ChirunoSource',return_value=source),patch('reset_probe.LumaInputServer') as controller,redirect_stdout(io.StringIO()):
                self.assertEqual(run(args),1)
            controller.assert_not_called()
            report=json.loads((root/'probe/report.json').read_text())
            self.assertEqual(report['inputs']['RESET'],0)
            self.assertEqual(report['status'],'safe_stop')

    def test_button_enum_families_do_not_alias_and_clear_all_is_neutral(self):
        with patch('tppflush.socket.socket') as socket_class:
            ir=LumaInputServer('127.0.0.1')
            ir.press(N3DS_Buttons.ZL)
            self.assertEqual(ir.current_pressed_buttons,0)
            ir.press(Special_Buttons.HOME)
            self.assertEqual(ir.current_pressed_buttons,0)
            ir.press(HIDButtons.L | HIDButtons.R | HIDButtons.SELECT)
            ir.clear_everything(); ir.send(print_sent=False)
            raw=bytes(socket_class.return_value.send.call_args.args[0])
            self.assertEqual(raw.hex(),'ffffffff20000000000880008100808000000000')

    def test_failed_video_reconnect_never_repeats_reset(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); reference=root/'field.png'; Image.new('RGB',(320,240),'blue').save(reference)
            counter=[0]
            def read():
                counter[0]+=1
                if counter[0]>6: raise OSError('stream lost after reset')
                screen=counter[0]%2; now=time.monotonic()
                return VideoFrame(screen,Image.new('RGB',((320 if screen==0 else 400),240),'blue'),now,now)
            source=SimpleNamespace(read=read, close=Mock())
            args=SimpleNamespace(execute=True,accept_unsaved=True,initial_reference=str(reference),output=str(root/'probe'),local='127.0.0.1',console='127.0.0.1',quality=50,input_port=4950,seconds=2)
            plan=input_plan()
            with patch('reset_probe.input_plan',return_value=plan),patch('reset_probe.ChirunoSource',side_effect=[source,OSError('reconnect refused')]),patch('reset_probe.LumaInputServer') as controller,patch('reset_probe.time.sleep'),redirect_stdout(io.StringIO()):
                controller.return_value.socket.send.return_value=20
                self.assertEqual(run(args),1)
            controller.assert_called_once()
            calls=controller.return_value.socket.send.call_args_list
            self.assertEqual([c.args[0].hex() for c in calls],plan['packets']['RESET'])
            report=json.loads((root/'probe/report.json').read_text())
            self.assertEqual(report['inputs'],{'RESET':1,'START':0,'A':0})
            self.assertEqual(report['status'],'safe_stop')


if __name__=='__main__': unittest.main()
