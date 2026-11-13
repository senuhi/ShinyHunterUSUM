"""Old 3DS HIMEM diagnostics. Default passive; optional B only; NEVER resets."""
import argparse
import hashlib
import json
import socket
import time
from pathlib import Path
from ntr_transport import endpoint, FrameStore
from video_stream import BACKENDS, console_endpoint, open_video
from hardware_validation import hardware_context, receipt_path, require_hardware
from tppflush import LumaInputServer, HIDButtons


def probe(args):
    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    context = hardware_context(args.backend, console_endpoint(args.console, args.backend),
                               args.input_port, args.quality, args.max_span)
    report = dict(schema=1, context=context, status='incomplete',
                  reported_himem_usum=args.himem_usum, input_probe_completed=False,
                  frames={'0':0, '1':0}, frames_after_input={'0':0, '1':0},
                  operator_confirmation_required=True, controller_effect_verified=False)
    store = FrameStore()
    source = None
    ir = None
    last_save = {0:0, 1:0}
    start = time.monotonic()
    try:
        source = open_video(args.backend, endpoint(args.local,8001), tuple(context['console']),
                            args.quality, args.max_span)
        while time.monotonic() - start < args.seconds:
            try:
                frame = source.read()
            except socket.timeout:
                frame = None
            now = time.monotonic()
            if frame is not None:
                store.put(frame.screen, frame.image, frame.started, frame.completed)
                key = str(frame.screen)
                report['frames'][key] += 1
                if report['input_probe_completed']:
                    report['frames_after_input'][key] += 1
                with (out/'frames.jsonl').open('a',encoding='utf-8') as log:
                    log.write(json.dumps(dict(screen=frame.screen, started=frame.started,
                        completed=frame.completed, assembly_span=frame.completed-frame.started,
                        after_input=report['input_probe_completed']))+'\n')
                if now-last_save[frame.screen] >= .5:
                    frame.image.save(out/f'{("lower","upper")[frame.screen]}-{report["frames"][key]:05d}.png')
                    last_save[frame.screen] = now
            if not all(report['frames'].values()):
                if now-start > 15:
                    raise OSError('No complete pass from both screens')
                continue
            for screen in (0,1):
                store.snapshot(screen,max_age=args.max_age,max_span=args.max_span)
            if args.send_b and ir is None and min(report['frames'].values()) >= 3:
                # Only B, with fresh video BEFORE sending. No combined/special buttons.
                for screen in (0,1):
                    store.snapshot(screen,max_age=args.max_age,max_span=args.max_span).image.save(out/f'before-input-{screen}.png')
                ir = LumaInputServer(context['console'][0],args.input_port)
                try:
                    ir.press(HIDButtons.B)
                    ir.send(print_sent=False)
                    time.sleep(.08)
                finally:
                    ir.unpress(HIDButtons.B)
                    ir.send(print_sent=False)
                    ir.return_control()
                report['input_probe_completed'] = True
                print('B sent and released; UDP has no acknowledgement. Confirm its effect on the console.')
        if all(n >= 3 for n in report['frames'].values()):
            report['status'] = 'observed'
        if args.send_b and not all(n >= 3 for n in report['frames_after_input'].values()):
            raise OSError('Need at least 3 fresh complete passes per screen after B')
    except (OSError, ValueError, KeyboardInterrupt) as error:
        report.update(status='safe_stop', error=str(error))
        message = getattr(source, 'last_message', None)
        if message is not None:
            kind, flags, sub_b, payload = message
            (out/'last-packet.bin').write_bytes(payload)
            report['last_packet'] = dict(kind=kind,flags=flags,subtype_b=sub_b,length=len(payload))
    finally:
        report['elapsed'] = time.monotonic()-start
        if ir is not None:
            ir.socket.close()
        if source is not None:
            source.close()
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='observed' else 1


def attest(report_path):
    path = Path(report_path).expanduser().resolve()
    content = path.read_bytes()
    report = json.loads(content)
    context = report['context']
    if context['backend'] != 'ChirunoMod':
        raise ValueError('This attestation is for Old 3DS ChirunoMod HIMEM only')
    receipt = dict(schema=1, context=context, report=str(path),
        report_sha256=hashlib.sha256(content).hexdigest(),
        operator_confirmed_coexistence=True, operator_confirmed_manual_reset_continuity=True,
        environment=dict(console='Old 3DS LL',luma='13.4',streamer='ChirunoMod 0.2.2',
                         loader='ChLoad_HIMEM',game='Japanese USUM'),
        operator_attested_at=time.time())
    output = receipt_path(context)
    # Validate using the same runtime gate before installing an attestation.
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        receipt_path(context,directory).write_text(json.dumps(receipt),encoding='utf-8')
        require_hardware(context,directory)
    output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Operator attestation (not automatic hardware proof): {output}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command',required=True)
    check = commands.add_parser('probe')
    check.add_argument('--backend',choices=BACKENDS,default='ChirunoMod')
    check.add_argument('--local',required=True,help='Mac IPv4[:NTR UDP port]; ChirunoMod binds TCP source IP only')
    check.add_argument('--console',required=True,help='3DS IPv4[:video TCP port]')
    check.add_argument('--input-port',type=int,default=4950)
    check.add_argument('--quality',type=int,default=80)
    check.add_argument('--max-age',type=float,default=2.0)
    check.add_argument('--max-span',type=float,default=2.0)
    check.add_argument('--seconds',type=float,default=10)
    check.add_argument('--output',required=True)
    check.add_argument('--send-b',action='store_true',help='Explicitly send B once; manually open a harmless menu first')
    check.add_argument('--himem-usum',action='store_true',help='Operator reports ChLoad_HIMEM and USUM currently running')
    approve = commands.add_parser('attest')
    approve.add_argument('--report',required=True)
    approve.add_argument('--coexistence-observed',action='store_true',required=True)
    approve.add_argument('--manual-reset-continuity-observed',action='store_true',required=True)
    args = p.parse_args()
    if args.command == 'probe':
        if (not 1 <= args.input_port <= 65535 or not 1 <= args.quality <= 100 or
            not .1 <= args.max_age <= 10 or not .1 <= args.max_span <= 10 or
            not 1 <= args.seconds <= 120):
            p.error('Invalid port, quality, freshness or duration')
        return probe(args)
    attest(args.report)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f'SAFE STOP: {error}')
