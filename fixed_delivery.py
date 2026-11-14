"""Timed gift diagnostic using existing Luma input and post-receipt checks.

No navigation OCR. Operator chooses a known saved start. One reset is permitted
only after a fresh NORMAL summary-page consensus and final recheck.
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
from summary_check import check_summary,load_config,summary_buttons
from rehearsal import image_score

class FixedDelivery(AutomaticDelivery):
    def start(self,saved=False,approved=False,live=False,interval=3.0,party_before=4,stop_at_summary=True):
        sequence=summary_buttons(party_before)
        if type(stop_at_summary) is not bool:raise SafetyStop('情報画面で停止する設定が不正です。')
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
        self.summary_sequence=sequence;self.party_before=party_before
        self.stop_at_summary=stop_at_summary;self.summary_config=load_config()
        self.normal_summary_token=None
        self.max_actions=3+len(sequence)+3
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
        if self.actions>=self.max_actions:raise SafetyStop('固定手順の操作上限です。')
        self.actions+=1;self.engine.pulse(button,self.controller)

    def enter_game(self):
        self.click('START');self.wait(5,'続行画面の読み込み待ち')
        self.click('A');self.wait(12,'セーブデータの読み込み待ち')

    def summary_sample(self,frames,label):
        e=self.engine
        result=check_summary({key:frame.image for key,frame in frames.items()},self.ocr,self.summary_config)
        e.healthy()
        if any(time.monotonic()-(f.started if f.started is not None else f.received)>2 for f in frames.values()):
            raise SafetyStop('情報画面の判定中に映像が古くなりました。リセットしません。')
        for key,frame in frames.items():frame.image.save(e.directory/f'{label}-{key}.png')
        e.event('summary_verdict',phase=label,profile_sha256=self.summary_config['digest'],
                serials={key:f.serial for key,f in frames.items()},**result)
        e.report['summary_verdict']=result['verdict'];e.report['summary_scores']=result
        e.notify('summary',result)
        return result['verdict']

    def observe_summary(self,since,timeout=12):
        end=time.monotonic()+timeout;serials={};verdicts=[]
        while time.monotonic()<end:
            frames=self.ready()
            if not all(f.serial>serials.get(key,0) and f.started is not None and f.started>=since for key,f in frames.items()):
                self.engine.stop.wait(.03);continue
            serials={key:f.serial for key,f in frames.items()}
            verdict=self.summary_sample(frames,f'summary-{len(verdicts)+1}')
            if verdict=='unknown':raise SafetyStop('情報画面・対象名・色判定が不明です。リセットしません。')
            verdicts.append(verdict)
            if len(set(verdicts))>1:raise SafetyStop('情報画面の判定が一致しません。リセットしません。')
            if len(verdicts)>=self.summary_config['samples']:
                self.summary_serials=serials
                if verdict=='normal':self.normal_summary_token=frames
                return verdict
        raise SafetyStop('情報画面の判定が時間内に揃いません。リセットしません。')

    def reset_from_summary(self):
        if self.reset_sent:raise SafetyStop('リセットは1回だけです。')
        self.reset_sent=True
        token,self.normal_summary_token=self.normal_summary_token,None
        if token is None or self.stop_at_summary:
            raise SafetyStop('通常色の一致判定と今回のリセット許可がありません。')
        if any(time.monotonic()-f.received>2 for f in token.values()):
            raise SafetyStop('通常色の判定が古くなりました。リセットしません。')
        end=time.monotonic()+4
        while time.monotonic()<end:
            frames=self.ready()
            if all(f.serial>self.summary_serials.get(key,0) for key,f in frames.items()):break
            self.engine.stop.wait(.03)
        else:raise SafetyStop('最終判定に使う新しい映像がありません。リセットしません。')
        if self.summary_sample(frames,'summary-final-reset-check')!='normal':
            raise SafetyStop('送信直前の通常色確認が不明です。リセットしません。')
        self.click('RESET')

    def wait_field(self,since):
        # Rotom may independently open a question after loading. It is not a
        # failure to return to the saved location; use the upper field scene.
        end=time.monotonic()+20;stable=0;serial=0
        while time.monotonic()<end:
            frames=self.ready();frame=frames['1']
            if frame.serial<=serial or frame.started is None or frame.started<since:
                self.engine.stop.wait(.03);continue
            serial=frame.serial
            score=image_score(frame.image,self.baseline['1'],[0,0,400,240])
            self.engine.event('fixed_field_match',score=score)
            stable=stable+1 if score<=.05 else 0
            if stable>=3:
                for key,frame in frames.items():frame.image.save(self.engine.directory/f'auto-restored-field-{key}.png')
                return
        raise SafetyStop('受取前の場所への復帰を確認できません。再リセットしません。')

    def run_fixed(self,live):
        e=self.engine
        try:
            e.report.update(fixed_sequence=True,fixed_start=self.start_screen,live=live,shiny_verified=False,
                            party_before=self.party_before,stop_at_summary=self.stop_at_summary,
                            summary_profile_sha256=self.summary_config['digest'])
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
            for button,delay in self.summary_sequence:
                e.status(f'情報画面への固定手順 · {button}')
                self.click(button);self.wait(delay,'画面の表示待ち')
            verdict=self.observe_summary(time.monotonic())
            e.report['fixed_preflight_verified']=False
            if verdict=='shiny':
                e.status('色違い候補：情報画面で停止しました。リセットしません。目視確認してください。')
                return
            if self.stop_at_summary:
                e.status('通常色候補：情報画面で停止しました（初期設定・リセットなし）。判定画像と設定を確認してください。')
                return
            self.reset_from_summary()
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
