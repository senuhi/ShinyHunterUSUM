"""Repeated UDP masks form one hold; failed final guards send no reset-down."""
import tempfile
import unittest
from rehearsal import Rehearsal
from gift_recognition import SafetyStop
from tppflush import HIDButtons

class Controller:
    def __init__(self):self.mask=0;self.packets=[]
    def press(self,button):self.mask|=button
    def send(self,**options):self.packets.append(self.mask)
    def clear_everything(self):self.mask=0
    def return_control(self):self.packets.append('return')

class ReliablePulseTests(unittest.TestCase):
    def test_upstream_three_down_three_up_are_one_hold(self):
        with tempfile.TemporaryDirectory() as td:
            e=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td)
            e.healthy=lambda:{};ir=Controller()
            e.pulse('A',ir,copies=3)
            self.assertEqual(ir.packets,[HIDButtons.A]*3+[0]*3+['return'])
            self.assertEqual(e.report['controller_packets'],7)

    def test_final_guard_failure_cannot_send_any_repeated_reset_down(self):
        with tempfile.TemporaryDirectory() as td:
            e=Rehearsal('ChirunoMod',('127.0.0.1',8001),('127.0.0.1',6464),4950,td)
            e.healthy=lambda:{};ir=Controller()
            def veto():raise SafetyStop('shiny')
            with self.assertRaises(SafetyStop):e.pulse('RESET',ir,copies=3,before_send=veto)
            self.assertEqual(ir.packets,[0]*3+['return'])
            self.assertEqual(e.report['reset_attempts'],0)

if __name__=='__main__':unittest.main()
