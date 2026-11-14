"""Timed gift diagnostic using existing Luma input and post-receipt checks.

No navigation OCR. Operator chooses a known saved start. One reset is permitted
only after the existing high-confidence received-message consensus/final check.
"""
import math
from pathlib import Path
import sys
import threading
import time
from automatic_delivery import AutomaticDelivery
from gift_recognition import SafetyStop
from mac_ocr import MacOCR
from tppflush import LumaInputServer

class FixedDelivery(AutomaticDelivery):
    def start(self,saved=False,approved=False,live=False,interval=3.0):
        if not 1<=interval<=5:raise SafetyStop('会話間隔は1〜5秒です。')
        if self.engine.playing:raise SafetyStop('試験中です。')
        if live and (not saved or not approved):raise SafetyStop('受取前セーブと今回の許可が必要です。')
        if live and not self.engine.report.get('fixed_preflight_verified'):
            raise SafetyStop('受取員の前で接続確認を行ってください。')
        # Fixed mode only uses the baseline from this connection's passive check.
        self.baseline=getattr(self.engine,'fixed_baseline',None)
        if live and self.baseline is None:raise SafetyStop('この接続で受取前の接続確認を行ってください。')
        self.engine.transport_healthy()
        self.start_screen='field';self.interval=interval;self.live=live
        self.engine.player=threading.Thread(target=self.run_fixed,args=(live,),daemon=True)
        self.engine.player.start()

    def ready(self,timeout=4):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            frames=self.engine.recognition_frames()
            if frames is not None:
                # Leave room for OCR/final checking; input origin limit stays 2s.
                if all(time.monotonic()-(f.started if f.started is not None else f.received)<=1.5 for f in frames.values()):
                    return frames
            self.engine.stop.wait(.03)
        raise SafetyStop('操作に使える新しい両画面が揃いません。入力しません。')

    def wait(self,seconds,label):
        end=time.monotonic()+seconds;shown=None
        while time.monotonic()<end:
            self.engine.transport_healthy()
            left=math.ceil(end-time.monotonic())
            if left!=shown:self.engine.status(f'{label} · あと{left}秒');shown=left
            self.engine.stop.wait(min(.1,max(0,end-time.monotonic())))

    def click(self,button):
        self.ready()
        if self.actions>=6:raise SafetyStop('固定手順の操作上限です。')
        self.actions+=1;self.engine.pulse(button,self.controller)

    def enter_game(self):
        self.click('START');self.wait(5,'続行画面の読み込み待ち')
        self.click('A');self.wait(12,'セーブデータの読み込み待ち')

    def run_fixed(self,live):
        e=self.engine
        try:
            e.report.update(fixed_sequence=True,fixed_start=self.start_screen,live=live,shiny_verified=False)
            frames=self.ready()
            if not live:
                import json
                refs={}
                for key,frame in frames.items():
                    name=f'fixed-baseline-{key}.png';frame.image.save(e.directory/name);refs[key]=name
                (e.directory/'auto-baseline.json').write_text(json.dumps({'backend':e.backend,'steps':[{'button':'A','references':refs}]}))
                e.fixed_baseline={key:frame.image.copy() for key,frame in frames.items()}
                e.report['fixed_preflight_verified']=True
                e.status('接続確認完了（送信0）。受取前に保存した受取員の前から開始してください。')
                return
            if self.baseline is None:raise SafetyStop('受取前の基準画像がありません。配達員の前で接続確認してください。')
            e.status('受取後の判定器を準備中（操作なし）')
            self.ocr=MacOCR(Path(sys.prefix)/'ocr-cache')
            self.ocr.read(frames['1'].image,timeout=65)  # Warmup only, not navigation.
            self.controller=LumaInputServer(e.console[0],e.input_port)
            for index in range(3):
                e.status(f'受取の固定手順 · A {index+1}/3')
                self.click('A');self.wait(self.interval,'会話の表示待ち')
            e.status('受取後の完了表示を確認中。ここだけ画像判定します。')
            decision,_,image=self.observe('receive',time.monotonic(),timeout=8)
            if decision!='received':raise SafetyStop('固定手順後の受取完了が不明です。追加操作・リセットは送りません。')
            self.ready()
            self.send('RESET',image,[15,170,385,232])
            self.wait(25,'ソフトリセットとタイトルの読み込み待ち')
            self.enter_game()
            e.status('最終チェック：受取前の画面へ戻ったか確認中')
            self.wait_field(time.monotonic())
            e.report['fixed_preflight_verified']=False
            e.report['completed_cycles']+=1
            e.status('固定手順の自動受取→リセット1回→復帰確認が完了しました。')
        except Exception as error:e.fail(error)
        finally:
            if self.controller is not None:self.controller.socket.close()
            if self.ocr is not None:self.ocr.close()
            e.notify('play_finished',None);e.write_report()
