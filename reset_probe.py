"""Bounded, operator-supervised reset diagnostic; separate from the hunt runner.

Default is offline dry-run. Live mode sends one reset only, then permits at most
one START and two A presses against operator-reviewed, fresh screen references.
Video-only reconnects are bounded; neither disconnects nor unknown images reset.
"""
import argparse
import json
import socket
import time
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageChops, ImageStat
from chiruno_transport import ChirunoSource
from ntr_transport import FrameStore, endpoint
from tppflush import HIDButtons, LumaInputServer


def input_plan():
    class OfflineSocket:
        def __init__(self, *args): self.packets = []
        def settimeout(self, value): pass
        def connect(self, address): pass
        def send(self, data): self.packets.append(bytes(data).hex()); return len(data)
    plan = {}
    with patch('tppflush.socket.socket', OfflineSocket):
        for name, buttons in [('RESET', (HIDButtons.L, HIDButtons.R, HIDButtons.SELECT)),
                              ('START', (HIDButtons.START,)), ('A', (HIDButtons.A,))]:
            ir = LumaInputServer('127.0.0.1')
            for button in buttons: ir.press(button)
            ir.send(print_sent=False)
            ir.clear_everything(); ir.send(print_sent=False); ir.return_control()
            plan[name] = ir.socket.packets
    return dict(reset_limit=1, continuation_limits={'START': 1, 'A': 2},
                hold_seconds={'RESET': .15, 'START': .08, 'A': .08},
                video_reconnect_limit=3, max_age=2, max_span=2,
                packets=plan, saved_game_confirmed=False,
                unknown_action='block input; no repeated reset')


def distance(image, reference):
    if image.size != reference.size: raise ValueError('Reference dimensions differ')
    return sum(ImageStat.Stat(ImageChops.difference(
        image.convert('RGB'), reference.convert('RGB'))).mean) / (3 * 255)


def run(args):
    plan = input_plan()
    if not args.execute:
        print(json.dumps(dict(mode='dry_run', network_packets_sent=0, **plan), indent=2))
        return 0
    if not args.accept_unsaved or not args.initial_reference:
        raise ValueError('Live diagnostic requires explicit unsaved-state acceptance and field reference')
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=False)
    reference = Image.open(args.initial_reference).convert('RGB')
    local, console = endpoint(args.local, 8001), endpoint(args.console, 6464)
    start = time.monotonic(); source = None; store = FrameStore(); counts = {0: 0, 1: 0}
    used = {'RESET': 0, 'START': 0, 'A': 0}; reconnects = 0; command_id = 0
    report = dict(status='starting', counts=counts, inputs=used, reconnects=0,
                  saved_game_confirmed=False, operator_accepted_unsaved=True,
                  automatic_hunt_enabled=False, actions=[])

    def event(kind, **values):
        with (out/'events.jsonl').open('a') as f:
            f.write(json.dumps(dict(event=kind, elapsed=time.monotonic()-start, **values))+'\n')

    def publish():
        report.update(elapsed=time.monotonic()-start, reconnects=reconnects)
        temp=out/'progress.tmp'; temp.write_text(json.dumps(report, indent=2)+'\n')
        temp.replace(out/'progress.json')

    def healthy():
        return [store.snapshot(s, max_age=2, max_span=2, freeze_timeout=15) for s in (0, 1)]

    def send(name):
        limit = 1 if name in ('RESET', 'START') else 2
        if name not in used or used[name] >= limit: raise ValueError('Input budget exceeded')
        healthy()
        # Consume BEFORE opening/sending: an exception cannot authorize a retry.
        used[name] += 1
        ir=LumaInputServer(console[0], args.input_port)
        def datagram(index):
            raw=plan['packets'][name][index]
            event('send_attempt', name=name, part=index, hex=raw)
            sent=ir.socket.send(bytes.fromhex(raw))
            event('sent', name=name, part=index, bytes=sent)
            if sent != 20: raise OSError('Short input datagram')
        try:
            try:
                datagram(0); time.sleep(plan['hold_seconds'][name])
            finally:
                try: datagram(1)
                finally: datagram(2)
        finally:
            ir.socket.close()
        report['actions'].append(dict(name=name, elapsed=time.monotonic()-start))
        event('input_completed', name=name)

    try:
        source=ChirunoSource(local, console, quality=args.quality)
        report['status']='preflight'
        while time.monotonic()-start < args.seconds:
            if (out/'stop-request.json').exists():
                report['status']='operator_ended'; break
            try:
                frame=source.read()
            except socket.timeout:
                frame=None
            except OSError as error:
                event('video_error', error=str(error))
                if not used['RESET'] or reconnects >= 3: raise
                source.close(); source=None; reconnects+=1
                # Only reception recovers. No input or reset is sent here.
                store=FrameStore(); counts={0: 0, 1: 0}; report['counts']=counts
                publish()
                time.sleep(.5)
                source=ChirunoSource(local, console, quality=args.quality)
                continue
            if frame is not None:
                counts[frame.screen]+=1
                store.put(frame.screen, frame.image, frame.started, frame.completed)
                label=('lower', 'upper')[frame.screen]
                temp=out/f'{label}.tmp'; frame.image.save(temp, 'PNG'); temp.replace(out/f'latest-{label}.png')
                event('frame', screen=frame.screen, count=counts[frame.screen],
                      span=frame.completed-frame.started)
            if min(counts.values()) >= 3:
                try: current=healthy()
                except OSError as error:
                    report['status']='input_blocked_stale_video'; event('input_blocked', error=str(error))
                    publish(); continue
                if not used['RESET']:
                    score=distance(current[0].image, reference)
                    event('pre_reset_reference', score=score)
                    if score > .06: raise OSError('Pre-reset field does not match reviewed reference')
                    for s in (0, 1): current[s].image.save(out/f'before-reset-{s}.png')
                    send('RESET'); report['status']='waiting_for_reviewed_title'
                    # Old frames cannot authorize continuation.
                    store=FrameStore(); counts={0: 0, 1: 0}; report['counts']=counts
                else:
                    report['status']='waiting_for_reviewed_next_state'
                    command=out/'command.json'
                    if command.exists():
                        request=json.loads(command.read_text())
                        if request['id'] > command_id:
                            if request['id'] != command_id+1 or request['button'] not in ('START', 'A'):
                                raise ValueError('Invalid reviewed continuation')
                            if request.get('reviewed_state') not in ('title', 'continue_selected'):
                                raise ValueError('Unrecognized continuation state')
                            reviewed=Image.open(request['reference']).convert('RGB')
                            screen=request.get('screen', 0)
                            score=distance(current[screen].image, reviewed)
                            event('continuation_reference', id=request['id'], score=score)
                            if score > .04: raise OSError('Reviewed continuation screen changed')
                            if request['button']=='START' and request['reviewed_state']!='title':
                                raise ValueError('START allowed only at reviewed title')
                            if request['button']=='A' and request['reviewed_state']!='continue_selected':
                                raise ValueError('A allowed only at reviewed continue selection')
                            for s in (0, 1): current[s].image.save(out/f'before-command-{request["id"]}-{s}.png')
                            send(request['button']); command_id=request['id']
                            report['status']='waiting_for_reviewed_next_state'
                            store=FrameStore(); counts={0: 0, 1: 0}; report['counts']=counts
            publish()
        else: report['status']='bounded_window_ended'
    except (OSError, ValueError, KeyError, KeyboardInterrupt) as error:
        report.update(status='safe_stop', error=str(error)); event('safe_stop', error=str(error))
    finally:
        if source is not None: source.close()
        publish(); (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 1 if report['status']=='safe_stop' else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--accept-unsaved', action='store_true')
    parser.add_argument('--initial-reference')
    parser.add_argument('--local', default='127.0.0.1')
    parser.add_argument('--console', default='127.0.0.1')
    parser.add_argument('--input-port', type=int, default=4950)
    parser.add_argument('--quality', type=int, default=50)
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--output', default='captures/reset-diagnostic')
    args=parser.parse_args()
    if not 1 <= args.seconds <= 180 or not 1 <= args.input_port <= 65535:
        parser.error('Invalid duration or input port')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
