"""App-owned Japanese gift loop using the existing video/input/Summary guards.

This mode localizes the receipt checkpoint with local Vision, rather than
pretending missing English-derived Japanese templates are calibrated. It does
not issue hardware attestations. Native shiny accuracy remains unverified.
"""
from pathlib import Path
import re
import sys
import time
from automatic_delivery import DIALOGUE_BOX,normalized
from fixed_delivery import FixedDelivery
from gift_recognition import SafetyStop
from mac_ocr import MacOCR
from production_setup import PRODUCTION_TARGETS,preparation,summary_profile
from summary_check import load_config
from rehearsal import image_score
from tppflush import LumaInputServer,CPAD_Commands


class AppGiftHunt(FixedDelivery):
    def __init__(self,engine,target='poipole'):
        super().__init__(engine)
        if target not in PRODUCTION_TARGETS:raise SafetyStop('本番対象はベベノム／ヌル・ポニです。')
        self.target=target;self.route=preparation()['targets'][target]
        self.target_name=self.route['name'];self.cycle_limit=1;self.receipt_timeout=75

    def configuration(self):return load_config(summary_profile(self.target))

    def start(self,saved=False,approved=False,live=False,party_before=1,stop_at_summary=True,cycles=1,interval=1):
        if self.engine.playing:raise SafetyStop('すでに周回中です。')
        if party_before!=1:raise SafetyStop('日本語の本番周回は受取前の手持ち1匹が前提です。')
        if type(cycles) is not int or not 0<=cycles<=100000:raise SafetyStop('周回数は0（連続）〜100000です。')
        self.cycle_limit=cycles
        super().start(saved,approved,live,interval,party_before,stop_at_summary)

    def approach(self):
        if self.target!='typenull_poni':return
        # Same upstream Poni approach: right .1s -> neutral, three times.
        for _ in range(3):
            self.ready();self.engine.event('input_attempt',button='CPADRIGHT')
            try:
                self.engine.healthy()
                self.controller.circle_pad_set(CPAD_Commands.CPADRIGHT,1.0)
                self.controller.send(print_sent=False);self.engine.report['controller_packets']+=1
                self.wait(.1,'受取イベントへ右移動')
            finally:
                try:
                    self.controller.circle_pad_neutral();self.controller.send(print_sent=False)
                    self.engine.report['controller_packets']+=1
                finally:
                    self.controller.return_control();self.engine.report['controller_packets']+=1
            self.engine.event('input_completed',button='CPADRIGHT')

    def receipt_kind(self,rows):
        """Navigation hint only. Never authorizes a reset or a colour verdict."""
        raw=''.join(row['text'] for row in rows)
        text=normalized(raw);name=normalized(self.target_name)
        if any(c in raw for c in '?？「」『』'):return 'unknown',text
        registration=(text.startswith(name+'のデタが新しく') and
                      text.endswith('ポケモン図鑑に登録されます'))
        added=re.fullmatch(re.escape(name)+r'(?:は|が)(?:手持ち|てもち)に(?:加わった|くわわった)',text)
        past=re.fullmatch(r'(?:[\wぁ-んァ-ヶ一-龯]{1,12}は)?'+re.escape(name)+r'を(?:うけとった|受け取った|受けとった|もらった)',text)
        return ('received' if registration or added or past else 'unknown'),text

    def receive(self):
        """A advances reception; a completion hint switches to B cleanup.

        Keep upstream A/B ordering, but do not switch to B merely because a
        future-tense offer mentions the name in a different Japanese position.
        """
        self.approach();end=time.monotonic()+self.receipt_timeout
        serial=0;attempts=0;since=0
        while time.monotonic()<end:
            frames=self.ready();frame=frames['1']
            if frame.serial<=serial or (frame.started is not None and frame.started<since):
                self.engine.stop.wait(.03);continue
            serial=frame.serial;crop=frame.image.crop(DIALOGUE_BOX)
            rows=self.ocr.read(crop);decision,text=self.receipt_kind(rows)
            self.engine.healthy()
            if time.monotonic()-(frame.started if frame.started is not None else frame.received)>2:
                raise SafetyStop('受取確認中に映像が古くなりました。追加入力しません。')
            self.engine.event('gift_receipt_read',target=self.target,rows=rows,decision=decision,text=text)
            self.engine.notify('ocr',text or '受取会話の表示待ち')
            if decision=='received':
                # Receipt OCR only selects when to stop advancing with A. It is
                # not safety-critical colour evidence; requiring an independent
                # OCR agreement here blocked clear native receipt screens.
                # Field return, Summary identity/colour and final reset checks
                # remain independent and mandatory.
                frame.image.save(self.engine.directory/'received-message.png')
                self.engine.status('受取表示を確認。図鑑登録・会話の終了を待ちます。')
                return
            if any(word in text for word in ('レポト','セブ','逃が','にがす','交換','ニックネム','ボックス','満杯')):
                raise SafetyStop('想定外の受取メニューです。追加操作・リセットは送りません。')
            # A is bounded and only advances visible dialogue (or the initial
            # saved field). Blank transition frames do not cause extra input.
            visible=any(row['confidence']>=.5 and re.search(r'[ぁ-んァ-ヶ一-龯]',row['text']) for row in rows)
            if attempts==0 or visible:
                if attempts>=30:raise SafetyStop('受取のA操作上限です。リセットしません。')
                self.click('A');attempts+=1;since=time.monotonic()
                self.wait(1,'受取会話を進めています')
            else:self.engine.stop.wait(.1)
        raise SafetyStop('日本語の受取完了が確認できません。リセットしません。')

    def clear_receipt(self,timeout=60):
        """Wait out first-time registration before opening the party menu.

        Upstream advances with B until reception dialogue ends. A fixed ten B
        presses can expire during the first Pokedex animation. Do not issue X
        until three fresh upper frames match this connection's saved field.
        """
        if self.baseline is None:raise SafetyStop('受取前の開始画像がありません。')
        end=time.monotonic()+timeout;serial=0;stable=0;presses=0;since=time.monotonic()
        while time.monotonic()<end:
            frames=self.ready();frame=frames['1']
            if frame.serial<=serial or frame.started is None or frame.started<since:
                self.engine.stop.wait(.03);continue
            serial=frame.serial
            score=image_score(frame.image,self.baseline['1'],[0,0,400,240])
            self.engine.event('gift_dialogue_field_match',score=score,presses=presses)
            if score<=.05:
                stable+=1
                if stable>=3:return
                self.engine.stop.wait(.03);continue
            stable=0
            if presses>=60:raise SafetyStop('図鑑登録・会話の終了を確認できません。メニュー操作・リセットは送りません。')
            self.click('B');presses+=1;since=time.monotonic()
            self.wait(.5,'図鑑登録・会話の終了待ち')
        raise SafetyStop('図鑑登録・会話の終了待ちが時間切れです。メニュー操作・リセットは送りません。')

    def summary_sample(self,frames,label):
        return super().summary_sample(frames,f'round-{self.engine.report.get("round",0):06d}-{label}')

    def run_fixed(self,live):
        if not live:return super().run_fixed(False)
        e=self.engine
        try:
            e.report.update(mode='app_gift_hunt',target=self.target,live=True,party_before=1,
                stop_at_summary=self.stop_at_summary,cycle_limit=self.cycle_limit,
                native_shiny_verified=False,recognition='local_Vision_and_shared_star_guard',
                summary_profile_sha256=self.summary_config['digest'])
            if self.baseline is None:raise SafetyStop('接続確認の開始画像がありません。')
            e.status('日本語認識を準備中。まだ操作しません。')
            self.ocr=MacOCR(Path(sys.prefix)/'ocr-cache')
            self.ocr.read(self.ready()['1'].image,timeout=65)
            self.controller=LumaInputServer(e.console[0],e.input_port)
            while self.cycle_limit==0 or e.report['completed_cycles']<self.cycle_limit:
                self.ready();self.actions=0;self.max_actions=100
                self.reset_sent=False;self.normal_summary_token=None
                e.report['round']=e.report['completed_cycles']+1
                e.status(f'{self.target_name} · {e.report["round"]}周目：受取を開始')
                self.receive()
                self.clear_receipt()
                # The B cleanup prefix is now bounded by saved-field proof.
                for button,delay in self.summary_sequence[10:]:
                    e.status(f'{e.report["round"]}周目：情報画面へ · {button}')
                    self.click(button);self.wait(delay,'画面の表示待ち')
                verdict=self.observe_summary(time.monotonic())
                e.report['fixed_preflight_verified']=False
                if verdict=='shiny':
                    e.status('色違い候補を検出。リセットせず停止しました。目視確認して手動保存してください。')
                    e.notify('shiny',self.target_name);return
                if self.stop_at_summary:
                    e.status('通常色候補。情報画面で停止しました（リセットなし）。');return
                self.reset_from_summary();self.wait(25,'リセット・タイトルの読み込み待ち')
                self.enter_game();self.wait_field(time.monotonic())
                e.report['completed_cycles']+=1;e.write_report()
                # Keep recent normal evidence bounded. Candidate/failure frames
                # belong to the current round and are never purged here.
                old=e.report['completed_cycles']-10
                if old>0:
                    for path in e.directory.glob(f'round-{old:06d}-*.png'):path.unlink()
            e.status(f'{e.report["completed_cycles"]}周が完了しました。')
        except Exception as error:e.fail(error)
        finally:
            e.report['fixed_preflight_verified']=False
            if self.controller is not None:self.controller.socket.close()
            if self.ocr is not None:self.ocr.close()
            # Normal completion or a candidate must not later be overwritten
            # by a frozen-static-Summary monitor error.
            e.stop.set()
            if e.source is not None:e.source.close()
            e.notify('play_finished',None);e.write_report()
