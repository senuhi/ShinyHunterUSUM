"""Screen-checked delivery rehearsal. This is NOT a shiny-hunt classifier.

Recording and default playback are passive. A live session needs explicit GUI
approval, a pre-receipt save, one reviewed received-screen reset checkpoint,
and a bounded cycle budget. Fixed navigation uses timed buttons; receipt/reset
checks remain mandatory. No game-save or touch input exists.
"""
import json
import hashlib
from bounded_log import append_json_line
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from gift_recognition import SafetyStop, roi
from ntr_transport import FrameStore
from tppflush import HIDButtons, LumaInputServer
from video_stream import open_video

BUTTONS = ('A', 'B', 'X', 'DPADUP', 'DPADDOWN', 'DPADLEFT', 'DPADRIGHT', 'START', 'RESET')
DEFAULT_BOXES = {0: [0, 0, 320, 240], 1: [0, 0, 400, 240]}


class VideoRecoveryPending(OSError):
    """Input is suspended; no button may be replayed from an older video epoch."""


def image_score(image, reference, box):
    a, b = roi(image, box).convert('RGB'), roi(reference, box).convert('RGB')
    if ImageStat.Stat(b.convert('L')).stddev[0] < 5:
        raise SafetyStop('目印が単色です。文字やアイコンを含む範囲を選択してください。')
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / (3 * 255)


def validate_trace(trace, directory):
    directory = Path(directory).resolve()
    if trace.get('schema') != 1 or trace.get('kind') != 'delivery_rehearsal':
        raise SafetyStop('受取テストの記録ファイルではありません。')
    steps = trace.get('steps', [])
    if not 2 <= len(steps) <= 80 or sum(s.get('button') == 'RESET' for s in steps) != 1:
        raise SafetyStop('手順は2〜80操作、リセットは1周に1回にしてください。')
    reset_index = next(i for i, s in enumerate(steps) if s.get('button') == 'RESET')
    if reset_index == 0 or not steps[reset_index].get('received_confirmed'):
        raise SafetyStop('受取済み画面を確認したリセット地点が必要です。')
    if 'A' not in [s.get('button') for s in steps[:reset_index]]:
        raise SafetyStop('リセット前の受け取り操作がありません。')
    if trace.get('backend') not in ('ChirunoMod', 'NTR-HR'):
        raise SafetyStop('映像方式が不明です。')
    if trace.get('quality') != 50:
        raise SafetyStop('受取テストの記録画質が異なります。')
    for step in steps + [trace.get('finish', {})]:
        if step in steps and step.get('button') not in BUTTONS:
            raise SafetyStop('許可されていない操作です。')
        refs, boxes = step.get('references', {}), step.get('boxes', {})
        if not boxes or set(boxes) - {'0', '1'} or not set(boxes) <= set(refs) or set(refs) != {'0', '1'}:
            raise SafetyStop('画面の照合範囲が不正です。')
        for key, filename in refs.items():
            path = (directory / filename).resolve()
            if not path.is_relative_to(directory):
                raise SafetyStop('参照画像が記録フォルダの外にあります。')
            with Image.open(path) as image:
                if image.size != ((320, 240) if key == '0' else (400, 240)):
                    raise SafetyStop('参照画像の画面サイズが違います。')
                if key in boxes:image_score(image, image, boxes[key])
    reset_step = steps[reset_index]
    different = False
    for key, box in reset_step['boxes'].items():
        with Image.open(directory/reset_step['references'][key]) as received, Image.open(directory/steps[0]['references'][key]) as initial:
            difference=ImageChops.difference(roi(received,box).convert('RGB'),roi(initial,box).convert('RGB'))
            different |= sum(ImageStat.Stat(difference).mean)/(3*255) > .07
    if not different:
        raise SafetyStop('リセット地点が開始画面と似ています。受取済みと分かる名前・情報画面を記録してください。')
    return trace


class Rehearsal:
    def __init__(self, backend, local, console, input_port, output, notify=lambda *args: None):
        self.backend, self.local, self.console = backend, local, console
        self.input_port = input_port
        self.output = Path(output); self.output.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix='delivery-', dir=self.output))
        self.notify = notify
        self.stop = threading.Event(); self.manual_next = threading.Event()
        self.store = FrameStore(); self.source = None; self.reader = None; self.player = None
        self.lock = threading.Lock(); self.log_lock = threading.Lock()
        self.failure_lock=threading.Lock()
        self.video_recovery_enabled=False;self.video_recovering=threading.Event()
        self.video_generation=0;self.video_pause_started=0;self.video_paused_total=0
        self.video_recovery_timeout=90;self.video_recovery_limit=5
        self.video_recovery_error=None;self.video_recovery_lock=threading.Lock()
        self.video_recovery_attempts=0
        self.frozen_reference={}
        self.latest = {}; self.counts = {0: 0, 1: 0}; self.started = time.monotonic()
        self.trace = dict(schema=1, kind='delivery_rehearsal', backend=backend, quality=50,
                          shiny_classification=False, steps=[])
        self.trace_directory = self.directory
        self.passive_verified = False
        self.report = dict(status='受信準備中', controller_packets=0, reset_attempts=0,
                           completed_cycles=0, live=False, shiny_verified=False)

    @property
    def playing(self):
        return self.player is not None and self.player.is_alive()

    @property
    def busy(self):
        return self.playing or (self.reader is not None and self.reader.is_alive())

    def event(self, kind, **details):
        with self.log_lock:
            append_json_line(self.directory/'events.jsonl',
                             dict(event=kind,elapsed=time.monotonic()-self.started,**details))

    def status(self, text):
        self.report['status'] = text; self.notify('status', text)
        self.write_report()

    def write_report(self):
        with self.log_lock:
            (self.directory/'report.json').write_text(json.dumps(dict(self.report,
                frames={str(k): v for k, v in self.counts.items()},
                elapsed=time.monotonic()-self.started), ensure_ascii=False, indent=2)+'\n')

    def fail(self, error):
        # Stop before any disk I/O: even a logging failure cannot leave input enabled.
        with self.failure_lock:
            self.stop.set()
            if self.report.get('failure_cause'):
                return  # Preserve the receiver's cause instead of "receiver stopped".
            self.report['failure_cause']=str(error)
        text='安全停止: '+str(error)
        self.report['status']=text;self.notify('status',text)
        try:
            with self.lock:
                for screen, image in self.latest.items():
                    image.save(self.directory/f'safe-stop-{screen}.png')
            self.event('safe_stop', error=str(error));self.write_report()
        except OSError as log_error:
            self.report['logging_error']=str(log_error)

    def connect(self):
        self.reader = threading.Thread(target=self._receive, daemon=True)
        self.reader.start()

    def operation_clock(self):
        now=time.monotonic()
        return now-self.video_paused_total-(now-self.video_pause_started if self.video_recovering.is_set() else 0)

    def request_video_recovery(self,error):
        if not self.video_recovery_enabled or self.stop.is_set():raise error
        with self.video_recovery_lock:
            if not self.video_recovering.is_set():
                self.video_pause_started=time.monotonic();self.video_recovery_error=str(error)
                self.video_recovery_attempts=0
                self.frozen_reference={}
                if 'Frozen screen' in str(error) and isinstance(self.store,FrameStore):
                    with self.store.lock:
                        self.frozen_reference={s:hashlib.sha256(f.image.tobytes()).digest() for s,f in self.store.frames.items()}
                self.video_recovering.set()
                self.report['video_recovering']=True
                self.event('video_input_paused',error=str(error),generation=self.video_generation)
                self.notify('status','映像を再接続中。ボタン入力・リセットを停止しています。')

    def _reconnect_video(self):
        """Reader thread only. Discard the decoder, never reuse partial images."""
        if self.source is not None:self.source.close()
        last_error=self.video_recovery_error
        while self.video_recovery_attempts<self.video_recovery_limit:
            if self.stop.is_set():raise SafetyStop('接続復旧を停止しました。')
            if time.monotonic()-self.video_pause_started>self.video_recovery_timeout:break
            self.video_recovery_attempts+=1
            self.event('video_reconnect_attempt',attempt=self.video_recovery_attempts,error=last_error)
            if self.stop.wait(min(.3*self.video_recovery_attempts,2)):raise SafetyStop('接続復旧を停止しました。')
            try:
                self.source=open_video(self.backend,self.local,self.console,quality=50)
                # Retain frame serials, but a newly attached static screen must
                # not inherit an old freeze timestamp. Input remains suspended.
                if isinstance(self.store,FrameStore):
                    with self.store.lock:self.store.hashes.clear()
                self.video_generation+=1
                self.report['video_reconnections']=self.report.get('video_reconnections',0)+1
                return
            except OSError as error:last_error=str(error)
        raise SafetyStop('映像の再接続に失敗しました。入力・リセットは再開しません: '+str(last_error))

    def _resume_video_if_ready(self,counts):
        if not self.video_recovering.is_set() or self.video_recovery_error is not None or min(counts.values())<2:return
        try:frames=self._transport_frames(check_origin=True)
        except OSError:return
        if self.frozen_reference and not any(hashlib.sha256(frame.image.tobytes()).digest()!=self.frozen_reference.get(int(key)) for key,frame in frames.items()):
            return  # New TCP timestamps do not make the same frozen picture live.
        with self.video_recovery_lock:
            self.video_paused_total+=time.monotonic()-self.video_pause_started
            self.video_recovering.clear();self.report['video_recovering']=False
        self.event('video_input_resumed',generation=self.video_generation)
        self.notify('status','新しい両画面を確認。現在画面から操作を再確認して続行します。')

    def _receive(self):
        try:
            self.source = open_video(self.backend, self.local, self.console, quality=50)
            epoch_counts={0:0,1:0};connected=time.monotonic()
            self.status('受信中。記録と照合のみでは入力しません。')
            while not self.stop.is_set():
                if self.video_recovering.is_set() and time.monotonic()-self.video_pause_started>self.video_recovery_timeout:
                    raise SafetyStop('映像の復旧待ちが時間切れです。入力・リセットは停止しています。')
                try:
                    if self.video_recovering.is_set() and self.video_recovery_error is not None:
                        self._reconnect_video();epoch_counts={0:0,1:0};connected=time.monotonic()
                        self.video_recovery_error=None
                    try:frame=self.source.read()
                    except socket.timeout:
                        if self.video_recovering.is_set():
                            if time.monotonic()-self.video_pause_started>self.video_recovery_timeout:
                                raise SafetyStop('映像の復旧待ちが時間切れです。入力・リセットは停止しています。')
                            if min(epoch_counts.values())<2 and time.monotonic()-connected<5:continue
                        if min(self.counts.values()):self._transport_frames(check_origin=False)
                        elif time.monotonic()-self.started>15:raise SafetyStop('15秒以内に両画面を受信できませんでした。')
                        continue
                except OSError as error:
                    if not self.video_recovery_enabled:raise
                    self.request_video_recovery(error);self.video_recovery_error=str(error)
                    continue
                self.store.put(frame.screen, frame.image, frame.started, frame.completed)
                epoch_counts[frame.screen]+=1
                with self.lock:
                    self.latest[frame.screen] = frame.image
                    self.counts[frame.screen] += 1
                self.event('frame', screen=frame.screen, count=self.counts[frame.screen],
                           span=frame.completed-frame.started)
                self._resume_video_if_ready(epoch_counts)
        except Exception as error:
            if not self.stop.is_set(): self.fail(error)
        finally:
            self.report['video_startup_retries']=getattr(self.source,'startup_retries',0)
            if self.source is not None: self.source.close()
            self.write_report()

    def healthy(self):
        if self.stop.is_set(): raise SafetyStop('受信が停止しています。再接続してください。')
        if self.video_recovering.is_set():raise VideoRecoveryPending('映像復旧中は入力しません。')
        try:return self._transport_frames(check_origin=True)
        except OSError as error:
            if not self.video_recovery_enabled:raise
            self.request_video_recovery(error)
            raise VideoRecoveryPending(str(error)) from error

    def _transport_frames(self,check_origin):
        if self.stop.is_set():raise SafetyStop('受信が停止しています。再接続してください。')
        frames={str(s):self.store.snapshot(s,max_age=2,max_span=2,
                freeze_timeout=float('inf') if self.video_recovery_enabled else 15,
                check_origin=check_origin) for s in (0,1)}
        # The upper Summary page is intentionally static; the lower model moves.
        # A frozen pair, not one static screen, indicates stopped game/video.
        now=self.store.clock() if isinstance(self.store,FrameStore) else time.monotonic()
        if self.video_recovery_enabled and all(now-f.changed>15 for f in frames.values()):
            raise OSError('Frozen screens 0/1')
        return frames

    def transport_healthy(self):
        """Receiver-only check. Input always retains the stricter origin limit."""
        if self.video_recovering.is_set():return {}
        try:return self._transport_frames(check_origin=False)
        except OSError as error:
            if not self.video_recovery_enabled:raise
            self.request_video_recovery(error);return {}

    def recognition_frames(self):
        try:frames=self.healthy()
        except OSError:
            self.transport_healthy()  # Silence, frozen video or bad assembly still stops.
            if not self.report.get('waiting_for_fresh_frames'):
                self.report['waiting_for_fresh_frames']=True
                self.event('input_paused_for_fresh_frames')
                self.notify('status','新しい両画面が揃うまで入力を一時停止しています。')
            return None
        if self.report.pop('waiting_for_fresh_frames',False):self.event('fresh_frames_resumed')
        return frames

    def capture(self, name, boxes):
        frames = self.healthy(); references = {}
        for key, box in boxes.items():
            image_score(frames[key].image, frames[key].image, box)
        for key in ('0','1'):
            filename = name+'-'+key+'.png'; frames[key].image.save(self.directory/filename)
            references[key] = filename
        return dict(boxes=boxes, references=references)

    def record(self, button, boxes, received_confirmed=False):
        if self.playing: raise SafetyStop('再生中は記録できません。')
        if button not in BUTTONS: raise SafetyStop('未対応の操作です。')
        if len(self.trace['steps']) >= 80: raise SafetyStop('記録は80操作までです。')
        if button == 'RESET':
            if not received_confirmed: raise SafetyStop('受取済みの画面を確認してチェックしてください。')
            if any(s['button']=='RESET' for s in self.trace['steps']):
                raise SafetyStop('1周にリセットは1回だけ記録できます。')
        step = dict(button=button, received_confirmed=bool(received_confirmed),
                    **self.capture(f'step-{len(self.trace["steps"])+1:02d}', boxes))
        self.trace['steps'].append(step)
        self.trace.pop('finish', None)
        self.passive_verified = False
        self.save_draft()
        self.event('recorded_passively', button=button, controller_packets=0)
        self.status(f'{button}を記録しました。3DS本体でその操作を1回行ってください。')

    def finish_recording(self, boxes):
        self.passive_verified = False
        self.trace['finish'] = self.capture('finish', boxes)
        validate_trace(self.trace, self.directory)
        path = self.directory/'trace.json'
        path.write_text(json.dumps(self.trace, ensure_ascii=False, indent=2)+'\n')
        self.trace_directory = self.directory
        self.status('記録完了。照合のみ、または許可して再生を選べます。')
        return path

    def save_draft(self):
        (self.directory/'trace-draft.json').write_text(json.dumps(self.trace,ensure_ascii=False,indent=2)+'\n')

    def load(self, path):
        if self.playing: raise SafetyStop('再生中は読み込めません。')
        path = Path(path).resolve(); trace = validate_trace(json.loads(path.read_text()), path.parent)
        if trace['backend'] != self.backend: raise SafetyStop('記録と現在の映像方式が違います。')
        for index, step in enumerate(trace['steps']+[trace['finish']]):
            for key, filename in list(step['references'].items()):
                copied=f'loaded-{index:02d}-{key}.png'
                source=(path.parent/filename).resolve(); destination=self.directory/copied
                if source != destination:shutil.copyfile(source,destination)
                step['references'][key]=copied
        self.trace, self.trace_directory = trace, self.directory
        self.passive_verified = False
        self.save_draft()
        self.status('記録を読み込みました。開始画面へ戻して再生してください。')

    def _wait_match(self, step, since, timeout=25):
        references = {key: Image.open(self.trace_directory/name).convert('RGB')
                      for key, name in step['references'].items()}
        end = time.monotonic()+timeout; serials = {}; consensus = 0
        while time.monotonic() < end:
            frames = self.healthy()
            keys = step['boxes']
            if not all(frames[k].serial > serials.get(k, 0) and
                       frames[k].started is not None and frames[k].started >= since for k in keys):
                self.stop.wait(.03); continue
            serials = {k: frames[k].serial for k in keys}
            scores = {k: image_score(frames[k].image, references[k], step['boxes'][k]) for k in keys}
            matched = all(value <= .035 for value in scores.values())
            self.event('recognition', scores=scores, matched=matched, serials=serials)
            self.notify('scores', scores)
            consensus = consensus+1 if matched else 0
            if consensus >= 3:
                for k, frame in frames.items():
                    frame.image.save(self.directory/f'checkpoint-{self.report.get("cycle", 0)}-{self.report.get("step", 0)}-{k}.png')
                return
            self.stop.wait(.03)
        raise SafetyStop('記録した次の画面を認識できません。追加入力・リセットは送りません。')

    def _send(self, name, controller, step):
        current=self.healthy()
        for key, box in step['boxes'].items():
            with Image.open(self.trace_directory/step['references'][key]) as reference:
                if image_score(current[key].image,reference,box) > .035:
                    raise SafetyStop('送信直前に画面が変わりました。入力しません。')
        self.pulse(name,controller)

    def pulse(self, name, controller, before_send=None, copies=1):
        """Existing Luma button transport, with no navigation image matching."""
        if name not in BUTTONS:raise SafetyStop('未対応の操作です。')
        if type(copies) is not int or not 1<=copies<=3:raise SafetyStop('送信回数が不正です。')
        self.healthy()
        buttons = (HIDButtons.L, HIDButtons.R, HIDButtons.SELECT) if name=='RESET' else (getattr(HIDButtons, name),)
        for button in buttons: controller.press(button)
        self.event('input_attempt', button=name)
        try:
            self.healthy()
            if before_send is not None:before_send()
            if name=='RESET': self.report['reset_attempts'] += 1
            for _ in range(copies):
                controller.send(print_sent=False); self.report['controller_packets'] += 1
            self.stop.wait(.15 if name=='RESET' else .08)
        finally:
            try:
                controller.clear_everything()
                for _ in range(copies):
                    controller.send(print_sent=False); self.report['controller_packets'] += 1
            finally:
                controller.return_control(); self.report['controller_packets'] += 1
        self.event('input_completed', button=name)

    def play(self, cycles=1, live=False, saved=False, approved=False):
        if self.playing: raise SafetyStop('すでに再生中です。')
        if type(cycles) is not int or not 1 <= cycles <= 3: raise SafetyStop('試験は1〜3周です。')
        validate_trace(self.trace, self.trace_directory)
        if live and (not saved or not approved): raise SafetyStop('受取前セーブと今回の実行許可が必要です。')
        if live and not self.passive_verified: raise SafetyStop('まず「照合のみ」で1周を完了してください。')
        self.healthy()
        self.report.update(live=live, cycle=0, step=0, completed_cycles=0)
        self.player = threading.Thread(target=self._play, args=(cycles, live), daemon=True)
        self.player.start()

    def _play(self, cycles, live):
        controller = None; since = time.monotonic()
        try:
            if live: controller = LumaInputServer(self.console[0], self.input_port)
            for cycle in range(1, cycles+1):
                self.report['cycle'] = cycle
                for index, step in enumerate(self.trace['steps'], 1):
                    self.report['step'] = index
                    self.manual_next.clear()
                    self.status(f'{cycle}/{cycles}周 · {index}/{len(self.trace["steps"])}操作 · {step["button"]}の前画面を照合中')
                    self._wait_match(step, since)
                    if live:
                        self._send(step['button'], controller, step)
                    else:
                        self.status(f'一致: 3DSで{step["button"]}を操作して「手動操作済み」を押してください。送信0。')
                        self.notify('manual_ready', True)
                        while not self.manual_next.wait(.05): self.healthy()
                        self.healthy(); self.notify('manual_ready', False)
                    since = time.monotonic()
                self.status(f'{cycle}/{cycles}周 · 最後の復帰画面を照合中')
                self.report['step'] = 'finish'
                self._wait_match(self.trace['finish'], since)
                self.report['completed_cycles'] += 1
            self.status(f'{cycles}周の受取テスト完了。色違い判定の検証は含みません。')
            if not live:self.passive_verified = True
        except Exception as error:
            self.fail(error)
        finally:
            if controller is not None: controller.socket.close()
            self.notify('manual_ready', False); self.notify('play_finished', None)
            self.write_report()

    def disconnect(self):
        self.stop.set(); self.manual_next.set()
        if self.source is not None: self.source.close()
        self.status('停止しました。送信済み操作の自動再試行はしません。')
