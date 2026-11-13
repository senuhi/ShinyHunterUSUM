"""Gift-only controller. Reset is reachable only after fresh NORMAL consensus."""
import json
import time
import tempfile
from datetime import datetime
from pathlib import Path
from gift_recognition import Profile, TARGETS, SafetyStop, colour_verdict
from tppflush import HIDButtons, CPAD_Commands
from hardware_validation import require_hardware


class Evidence:
    def __init__(self, directory, profile):
        parent = Path(directory)
        parent.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(
            prefix='gift-' + datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=parent))
        self.profile = profile
        self.index = 0

    def record(self, event, frame=None, **details):
        self.index += 1
        if frame is not None:
            name = f'{self.index:06d}-{event}.png'
            frame.image.save(self.directory / name)
            details.update(image=name, serial=frame.serial, received=frame.received,
                           changed=frame.changed, assembly_started=frame.started)
        with (self.directory / 'scores.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(dict(time=time.time(), event=event,
                                   language=self.profile.language, target=self.profile.target,
                                   profile_sha256=self.profile.digest, **details), ensure_ascii=False, allow_nan=False) + '\n')


class GiftRunner:
    def __init__(self, tab, profile, dry_run=True):
        self.tab, self.general = tab, tab.General
        self.profile, self.dry_run = profile, dry_run
        self.frames = self.general.frames
        self.cancel = self.general.stop_event
        self.evidence = Evidence(self.general.shotpath, profile)
        self.normal_token = None
        self.last_serial = {}

    def healthy(self):
        if self.cancel.is_set():
            raise SafetyStop('Disconnected by user')
        for screen in (0, 1):
            self.frames.snapshot(screen, **self.profile.data['freshness'])

    def verify_live(self):
        backend = getattr(self.general, 'video_backend', None)
        self.profile.require_ready(live=True, backend=backend)
        if backend == 'ChirunoMod':
            context = getattr(self.general, 'hardware_context', None)
            if not context or context.get('backend') != backend:
                raise SafetyStop('Missing ChirunoMod hardware context')
            require_hardware(context)

    def pause(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.healthy()
            self.cancel.wait(min(.05, max(0, end - time.monotonic())))

    def frame(self, screen, after=0, timeout=2):
        end = time.monotonic() + timeout
        while True:
            self.healthy()
            frame = self.frames.snapshot(screen, **self.profile.data['freshness'])
            if frame.serial > after:
                return frame
            if time.monotonic() >= end:
                raise SafetyStop('No new completed frame')
            self.cancel.wait(.02)

    def send(self):
        self.healthy()
        if self.dry_run:
            raise SafetyStop('Dry-run blocks ALL controller packets')
        self.tab.ir.send(print_sent=False)

    def click(self, button):
        self.healthy()
        self.tab.ir.press(button)
        try:
            self.send()
            self.pause(.08)
        finally:
            self.tab.ir.unpress(button)
            # Releasing buttons is always permitted, including on stale video.
            if not self.dry_run:
                self.tab.ir.send(print_sent=False)
        self.pause(.08)

    def wait_stage(self, name, button=None):
        stage = self.profile.data['stages'][name]
        screen = stage['screen']
        serial = 0
        for attempt in range(stage.get('attempts', 100)):
            frame = self.frame(screen, serial)
            serial = frame.serial
            score, matched = self.profile.score(name, frame.image)
            self.evidence.record('match', frame if matched else None, stage=name,
                                 score=score, threshold=stage['threshold'], matched=matched,
                                 attempt=attempt, sample_serial=serial)
            if matched:
                self.last_serial[screen] = serial
                return frame
            if button is not None:
                self.click(button)
            self.pause(stage.get('interval', .1))
        self.evidence.record('timeout', frame, stage=name, score=score)
        raise SafetyStop(f'Unrecognized/low-confidence stage: {name} ({score:.4f})')

    def classify(self):
        config = self.profile.data['colour']
        anchor = self.profile.data['stages']['party_name']
        screen = config['screen']
        if anchor['screen'] != screen:
            raise SafetyStop('Classification anchor must be on colour screen')
        verdicts, serial = [], self.last_serial.get(screen, 0)
        samples = config['samples']
        if type(samples) is not int or not 3 <= samples <= 20:
            raise SafetyStop('Need 3–20 fresh consensus frames')
        for _ in range(samples):
            frame = self.frame(screen, serial)
            serial = frame.serial
            score, matched = self.profile.score('party_name', frame.image)
            if not matched:
                self.evidence.record('anchor_lost', frame, score=score)
                raise SafetyStop('Summary/party name anchor lost before colour check')
            result = colour_verdict(frame.image, config)
            self.evidence.record('verdict', frame, anchor_score=score, **result)
            verdicts.append(result['verdict'])
            if result['verdict'] == 'unknown' or len(set(verdicts)) > 1:
                raise SafetyStop('Unknown, low-confidence or conflicting colour verdict')
            self.pause(config['sample_interval'])
        if verdicts[0] == 'normal':
            self.normal_token = frame
        return verdicts[0]

    def receive(self):
        target = self.profile.target
        # Poni: approach the saved event trigger using the calibrated movement.
        if target == 'typenull_poni':
            movement = self.profile.data['approach']
            for _ in range(movement['repeats']):
                self.tab.ir.circle_pad_set(CPAD_Commands.CPADRIGHT, movement['x'])
                self.send()
                self.pause(movement['seconds'])
                self.tab.ir.circle_pad_neutral()
                self.send()
        self.wait_stage('dialogue_name', HIDButtons.A)
        if target in ('poipole', 'typenull_aether'):
            self.wait_stage('party_added', HIDButtons.B)
        if target == 'typenull_poni':
            self.wait_stage('dialogue_end', HIDButtons.B)
        elif target == 'typenull_aether':
            self.wait_stage('dialogue_end', HIDButtons.A)
        for _ in range(10):
            self.click(HIDButtons.B)
        self.wait_stage('menu', HIDButtons.X)
        self.wait_stage('party_level', HIDButtons.A)
        # User must leave the Pokémon menu entry selected before saving.
        self.wait_stage('party_name', HIDButtons.DPADUP)

    def reset(self):
        token, self.normal_token = self.normal_token, None
        if self.dry_run or token is None:
            raise SafetyStop('Reset denied: no fresh NORMAL consensus / dry-run')
        self.healthy()
        if time.monotonic() - token.received > 2:
            raise SafetyStop('Reset denied: NORMAL verdict expired')
        current = self.frame(self.profile.data['colour']['screen'], token.serial)
        score, anchor = self.profile.score('party_name', current.image)
        result = colour_verdict(current.image, self.profile.data['colour'])
        self.evidence.record('reset_check', current, anchor_score=score, **result)
        if not anchor or result['verdict'] != 'normal':
            raise SafetyStop('Reset denied: final normal/anchor check failed')
        self.verify_live()
        self.evidence.record('reset_authorized')
        if time.monotonic() - current.received > .5:
            raise SafetyStop('Reset denied: final verdict expired while writing evidence')
        self.healthy()
        for button in (HIDButtons.L, HIDButtons.R, HIDButtons.SELECT):
            self.tab.ir.press(button)
        try:
            self.send()
            self.pause(.15)
        finally:
            self.tab.ir.clear_everything()
            self.tab.ir.send(print_sent=False)
        for _ in range(10):
            self.click(HIDButtons.B)
        self.wait_stage('restart_title', HIDButtons.START)
        self.wait_stage('save_file')  # no blind A until localized save anchor appears
        self.click(HIDButtons.A)
        self.pause(self.profile.data['load_seconds'])
        if self.general.RoundStartHook is not None:
            self.general.RoundStartHook()

    def run(self):
        self.evidence.record('start', dry_run=self.dry_run)
        if self.dry_run:
            self.profile.require_ready()
        else:
            self.verify_live()
        if self.dry_run:
            # Passive preview only: manually navigate to the received Pokémon.
            self.wait_stage('party_name')
            verdict = self.classify()
            self.evidence.record('dry_run_complete', verdict=verdict)
            return f'Dry-run: {verdict}; no input/reset sent'
        # Deliberately NO initial soft reset. Begin at the saved gift trigger.
        while True:
            self.receive()
            verdict = self.classify()
            if verdict == 'shiny':
                self.evidence.record('shiny_stop')
                return 'Shiny candidate: stopped. Verify manually and save the game.'
            # Flush the completed round before reset footage; reset opens the next round.
            self.general.CounterPlusOne()
            self.reset()


def run_gift(tab, language, target, dry_run, profile_path=None):
    runner = None
    try:
        profile = Profile(language, TARGETS[target], profile_path)
        runner = GiftRunner(tab, profile, dry_run)
        tab.msgbox.MsgAppend(runner.run())
    except Exception as e:
        # Every exception exits the procedure; none can fall through to reset.
        if runner is not None:
            try:
                runner.evidence.record('safe_stop', reason=str(e))
                with runner.frames.lock:
                    frames = list(runner.frames.frames.items())
                for screen, frame in frames:
                    runner.evidence.record(f'stop_screen_{screen}', frame)
            except OSError:
                pass
        tab.msgbox.MsgAppend(f'SAFE STOP / 安全停止: {type(e).__name__}: {e}')
    finally:
        tab.General.stop_event.set()
        if tab.ir is not None and not dry_run:
            try:
                tab.ir.clear_everything()
                tab.ir.send(print_sent=False)
                tab.ir.return_control()
            except OSError:
                pass
        tab.General.ConnectState(0)
        tab.General.ConnectState(-1)
