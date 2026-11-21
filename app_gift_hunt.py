"""App-owned Japanese gift loop using the existing video/input/Summary guards.

This mode localizes the receipt checkpoint with local Vision, rather than
pretending missing English-derived Japanese templates are calibrated. It does
not issue hardware attestations. Native shiny accuracy remains unverified.
"""
from pathlib import Path
import json
from PIL import Image
import re
import sys
import time
from automatic_delivery import DIALOGUE_BOX,normalized
from fixed_delivery import FixedDelivery
from gift_recognition import SafetyStop
from mac_ocr import MacOCR
from production_setup import PRODUCTION_TARGETS,preparation,summary_profile
from summary_check import load_config
from gift_navigation import NavigationAnchors
from rehearsal import image_score
from tppflush import LumaInputServer,CPAD_Commands


class AppGiftHunt(FixedDelivery):
    button_copies=3
    def __init__(self,engine,target='poipole',resume_directory=None):
        super().__init__(engine)
        if target not in PRODUCTION_TARGETS:raise SafetyStop('本番対象はベベノム／ヌル・ポニです。')
        self.resume_directory=Path(resume_directory).expanduser().resolve() if resume_directory else None
        self.resume_pending=self.resume_directory is not None
        self.target=target;self.route=preparation()['targets'][target]
        self.target_name=self.route['name'];self.cycle_limit=1;self.receipt_timeout=75
        self.start_retry_interval=2.0;self.max_start_retries=3
        self.navigation=NavigationAnchors();self.navigation_timeout=120

    def configuration(self):return load_config(summary_profile(self.target))

    def start(self,saved=False,approved=False,live=False,party_before=1,stop_at_summary=True,cycles=1,interval=1):
        if self.engine.playing:raise SafetyStop('すでに周回中です。')
        if party_before!=1:raise SafetyStop('日本語の本番周回は受取前の手持ち1匹が前提です。')
        if type(cycles) is not int or not 0<=cycles<=100000:raise SafetyStop('周回数は0（連続）〜100000です。')
        self.cycle_limit=cycles
        if live and self.resume_pending:
            source=json.loads((self.resume_directory/'report.json').read_text())
            if (source.get('mode')!='app_gift_hunt' or source.get('target')!=self.target or
                source.get('round')!=source.get('completed_cycles',0)+1 or
                source.get('reset_attempts')!=source.get('completed_cycles') or
                source.get('summary_verdict')!='unknown' or
                source.get('summary_scores',{}).get('context') or
                not (self.resume_directory/'received-message.png').exists()):
                raise SafetyStop('受取後の中断記録を安全に引き継げません。リセットしません。')
            baseline={}
            for key,size in (('0',(320,240)),('1',(400,240))):
                with Image.open(self.resume_directory/f'fixed-baseline-{key}.png') as image:
                    if image.size!=size:raise SafetyStop('復旧用の開始画像サイズが不正です。')
                    baseline[key]=image.convert('RGB')
            # The operator starts this recovery explicitly. The old baseline is
            # used only when the current map/field matches the same gift site.
            current=self.ready()
            if (image_score(current['1'].image,baseline['1'],[0,0,400,145])>.05 or
                self.navigation.map_score(current['0'].image,baseline['0'])>.13 or
                image_score(current['1'].image,baseline['1'],[0,0,400,240])<=.05):
                raise SafetyStop('中断した受取場所と現在画面が一致しません。操作しません。')
            self.engine.fixed_baseline=baseline
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
        serial=0;attempts=0;since=0;dialogue_seen=False;field_stable=0;start_retries=0
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
            # A single UDP start press may have no visible effect. Retry only
            # before ANY dialogue, on three new saved-field matches. Blank or
            # unknown transition screens do not receive blind A presses.
            visible=any(row['confidence']>=.5 and re.search(r'[ぁ-んァ-ヶ一-龯]',row['text']) for row in rows)
            dialogue_seen |= visible
            retry_start=False
            if attempts and not dialogue_seen and not rows and self.baseline is not None:
                field_score=image_score(frame.image,self.baseline['1'],[0,0,400,240])
                field_stable=field_stable+1 if field_score<=.05 else 0
                if field_stable>=3 and time.monotonic()-since>=self.start_retry_interval:
                    if start_retries>=self.max_start_retries:
                        raise SafetyStop('開始Aの再送後も会話が始まりません。InputRedirectionを確認してください。リセットしません。')
                    start_retries+=1;retry_start=True
                    self.engine.event('receipt_start_retry',retry=start_retries,field_score=field_score,serial=frame.serial)
                    self.engine.status(f'受取前の位置を確認。開始Aを再送します（{start_retries}/{self.max_start_retries}）。')
            else:field_stable=0
            if attempts==0 or visible or retry_start:
                if attempts>=30:raise SafetyStop('受取のA操作上限です。リセットしません。')
                self.click('A');attempts+=1;since=time.monotonic();field_stable=0
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

    def navigation_state(self,frames):
        lower=frames['0'].image;upper=frames['1'].image
        state,scores=self.navigation.identify(lower)
        details={'anchor_scores':scores}
        if state=='menu':return state,details
        if state=='party':
            cursor,counts=self.navigation.cursor(lower)
            details['cursor_pixels']=counts
            return ('party_first' if cursor==1 else 'party_second' if cursor==2 else 'party_uncertain'),details
        lower_rows=self.ocr.read(lower)
        details['lower_rows']=lower_rows
        combined=' '.join(normalized(row['text']) for row in lower_rows if row['confidence']>=.3)
        if any(token in combined for token in ('つよさをみる','強さを見る')):return 'party_context',details
        # Menus change the lower screen while the upper field can remain visible.
        # Require a lower map/HUD match as well before X/B field recovery.
        map_score=self.navigation.map_score(lower,self.baseline['0'])
        details['map_score']=map_score
        top_score=image_score(upper,self.baseline['1'],[0,0,400,145])
        details['field_top_score']=top_score
        if top_score<=.05 and map_score<=.13:
            full_score=image_score(upper,self.baseline['1'],[0,0,400,240])
            details['field_score']=full_score
            return ('field' if full_score<=.05 else 'field_dialogue'),details
        rows=self.ocr.read(upper)
        text=' '.join(normalized(row['text']) for row in rows+lower_rows if row['confidence']>=.8)
        groups=(('おや','親'),('IDNO','IDナンバ'),('けいけんち','経験値'),('つぎのレベル','次のレベル'))
        anchors=sum(any(token in text for token in group) for group in groups)
        details.update(upper_rows=rows,summary_anchors=anchors)
        if anchors>=2:return 'summary',details
        upper_text=' '.join(normalized(row['text']) for row in rows if row['confidence']>=.3)
        if any(token in upper_text for token in ('とうろくかんりょう','図鑑に登録されます')):return 'registration',details
        return 'unknown',details

    def navigate_summary(self):
        """Closed-loop upstream menu/party navigation; no reset in recovery.

        A is sent only after a menu, selected second slot or Summary context is
        recognized. Late NPC dialogue returns to B cleanup, not blind A presses.
        """
        end=time.monotonic()+self.navigation_timeout
        serials={};since=time.monotonic();previous=None;stable=0;actions=0;unknown_since=None
        while time.monotonic()<end:
            frames=self.ready()
            if not all(frame.serial>serials.get(key,0) and frame.started is not None and frame.started>=since for key,frame in frames.items()):
                self.engine.stop.wait(.03);continue
            serials={key:frame.serial for key,frame in frames.items()}
            state,details=self.navigation_state(frames)
            self.engine.healthy()
            if any(time.monotonic()-frame.started>2 for frame in frames.values()):
                raise SafetyStop('画面遷移の確認中に映像が古くなりました。リセットしません。')
            self.engine.event('gift_navigation',state=state,serials=serials,**details)
            if state=='summary':return
            stable=stable+1 if state==previous else 1;previous=state
            if state in ('unknown','party_uncertain'):
                if unknown_since is None:
                    unknown_since=time.monotonic()
                    self.engine.status('画面の切替を確認中。次の操作はまだ送りません。')
                if time.monotonic()-unknown_since>10:raise SafetyStop('情報画面へ進む画面を認識できません。リセットしません。')
                self.engine.stop.wait(.1);continue
            unknown_since=None
            if stable<2:self.engine.stop.wait(.03);continue
            actions+=1
            if actions>90:raise SafetyStop('情報画面への操作上限です。リセットしません。')
            button,delay={'field':('X',2),'field_dialogue':('B',.5),'registration':('B',.5),
                          'menu':('A',3),'party_first':('DPADRIGHT',1),
                          'party_second':('A',1),'party_context':('A',3)}[state]
            labels={'field':'メニューを開く','field_dialogue':'会話を閉じる','registration':'図鑑登録を進める',
                    'menu':'ポケモンを開く','party_first':'受取個体を選ぶ','party_second':'受取個体のメニュー',
                    'party_context':'つよさをみる'}
            self.engine.status(f'情報画面へ · {labels[state]}（{button}）')
            self.click(button);since=time.monotonic();stable=0;previous=None
            self.wait(delay,'画面遷移の表示待ち')
        raise SafetyStop('情報画面への遷移が時間切れです。リセットしません。')

    def summary_sample(self,frames,label):
        return super().summary_sample(frames,f'round-{self.engine.report.get("round",0):06d}-{label}')

    def run_fixed(self,live):
        if not live:
            super().run_fixed(False)
            if self.resume_pending and self.engine.report.get('fixed_preflight_verified'):
                self.engine.status('接続確認完了（送信0）。開始すると受取済みの個体から情報画面へ復旧します。')
            return
        e=self.engine
        try:
            e.report.update(mode='app_gift_hunt',target=self.target,live=True,party_before=1,
                stop_at_summary=self.stop_at_summary,cycle_limit=self.cycle_limit,
                native_shiny_verified=False,recognition='local_Vision_and_shared_star_guard',
                button_copies=self.button_copies,navigation_mode='observed_states',
                summary_profile_sha256=self.summary_config['digest'])
            if self.baseline is None:raise SafetyStop('接続確認の開始画像がありません。')
            e.status('日本語認識を準備中。まだ操作しません。')
            self.ocr=MacOCR(Path(sys.prefix)/'ocr-cache')
            self.ocr.read(self.ready()['1'].image,timeout=65)
            self.controller=LumaInputServer(e.console[0],e.input_port)
            while self.cycle_limit==0 or e.report['completed_cycles']<self.cycle_limit:
                self.ready();self.actions=0;self.max_actions=180
                self.reset_sent=False;self.normal_summary_token=None
                e.report['round']=e.report['completed_cycles']+1
                e.status(f'{self.target_name} · {e.report["round"]}周目：受取を開始')
                if self.resume_pending:
                    e.report['resumed_from']=str(self.resume_directory)
                    e.event('resume_pending_receipt',source=str(self.resume_directory))
                    self.resume_pending=False
                    e.status('受取済みの個体を引き継ぎ、情報画面へ復旧しています。')
                else:self.receive()
                self.clear_receipt()
                self.navigate_summary()
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
