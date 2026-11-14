"""Capture, crop and replay native 3DS frames; never sends controller input."""
import argparse
import hashlib
import json
import socket
import time
import sys
from pathlib import Path
from PIL import Image
from gift_recognition import Profile, TARGETS, SafetyStop, roi, colour_verdict
from ntr_transport import endpoint
from video_stream import BACKENDS, console_endpoint, open_video


def replay(profile, manifest):
    manifest = Path(manifest).resolve()
    cases = json.loads(manifest.read_text(encoding='utf-8'))
    results = []
    for case in cases:
        with Image.open(manifest.parent / case['image']) as source:
            image = source.convert('RGB')
        if 'stage' in case:
            score, matched = profile.score(case['stage'], image)
            actual = 'match' if matched else 'no_match'
            result = dict(stage=case['stage'], score=score)
        else:
            score, anchor = profile.score('party_name', image)
            result = colour_verdict(image, profile.data['colour']) if anchor else dict(verdict='unknown')
            result['anchor_score'] = score
            actual = result['verdict']
        results.append(dict(case=case, actual=actual, passed=actual == case['expected'], **result))
    return results


def capture(args):
    local = endpoint(args.local, 8001)
    console = console_endpoint(args.console, args.backend)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    source = open_video(args.backend, local, console)
    end = time.monotonic() + args.seconds
    last = {0: 0, 1: 0}
    n = {0: 0, 1: 0}
    try:
        while time.monotonic() < end:
            try:
                frame = source.read()
            except socket.timeout:
                continue
            screen, image = frame.screen, frame.image
            now = time.monotonic()
            if now - last[screen] < args.interval:
                continue
            last[screen] = now
            n[screen] += 1
            image.save(out / f'{("lower", "upper")[screen]}-{n[screen]:04d}.png')
    finally:
        source.close()
    print(json.dumps(dict(captured=n, controller_packets=0)))
    if not all(n.values()):
        raise SafetyStop('No frames from one or both screens; capture not verified')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('prepare',help='Read-only two-route / one-member production plan')
    summary=commands.add_parser('summary-replay',help='Local Vision on native saved summary images; no network/input')
    summary.add_argument('--target',choices=('poipole','typenull_poni'),required=True)
    summary.add_argument('--upper',required=True)
    summary.add_argument('--lower',required=True)
    summary.add_argument('--output',required=True)
    cap = commands.add_parser('capture', help='Direct video capture; no controller input')
    cap.add_argument('--backend', choices=BACKENDS, default='ChirunoMod')
    cap.add_argument('--local', required=True, help='Mac IPv4:stream-port')
    cap.add_argument('--console', required=True, help='3DS IPv4[:video-TCP-port]')
    cap.add_argument('--output', required=True)
    cap.add_argument('--seconds', type=float, default=10)
    cap.add_argument('--interval', type=float, default=.5)
    for name in ('inspect', 'crop', 'replay', 'attest'):
        sub = commands.add_parser(name)
        sub.add_argument('--language', choices=('Japanese','English'), default='Japanese')
        sub.add_argument('--target', choices=TARGETS, required=True)
        sub.add_argument('--profile', help='Custom profile JSON')
        if name == 'crop':
            sub.add_argument('--stage', required=True)
            sub.add_argument('--image', required=True)
            sub.add_argument('--output', required=True)
        if name in ('replay','attest'):
            sub.add_argument('--cases', required=True, help='JSON fixture manifest')
        if name == 'attest':
            sub.add_argument('--backend', choices=BACKENDS, default='NTR-HR')
            sub.add_argument('--hardware-verified', action='store_true', required=True,
                             help='Operator attests the hardware checklist has actually passed')
    args = parser.parse_args()
    if args.command=='prepare':
        from production_setup import preparation
        print(json.dumps(preparation(),ensure_ascii=False,indent=2));return
    if args.command=='summary-replay':
        from summary_check import replay_summary,native_summary_images
        from mac_ocr import MacOCR
        images=native_summary_images(args.upper,args.lower)
        ocr=MacOCR(Path(sys.prefix)/'ocr-cache')
        try:
            ocr.read(images['1'],timeout=65)
            result=replay_summary(args.target,args.upper,args.lower,ocr)
            Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(result,ensure_ascii=False,indent=2))
        finally:ocr.close()
        return
    if args.command == 'capture':
        if not 0 < args.seconds <= 3600 or not .05 <= args.interval <= 60:
            parser.error('Invalid capture duration/interval')
        capture(args)
        return
    profile = Profile(args.language, args.target, args.profile)
    if args.command == 'inspect':
        print(json.dumps(dict(sha256=profile.digest, missing=profile.missing,
                              calibration=profile.data['calibration_status']), ensure_ascii=False, indent=2))
    elif args.command == 'crop':
        with Image.open(args.image) as image:
            roi(image, profile.data['stages'][args.stage]['box']).save(args.output)
        print(args.output)
    else:
        results = replay(profile, args.cases)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        if not results or not all(r['passed'] for r in results):
            raise SafetyStop('Replay failed; live mode remains blocked')
        if args.command == 'attest':
            profile.require_ready(live=False)
            if profile.missing:
                raise SafetyStop('All stage templates must be present before attestation')
            classes = {r['case']['expected'] for r in results if 'stage' not in r['case']}
            if not {'normal','shiny','unknown'} <= classes:
                raise SafetyStop('Need normal, shiny AND unknown/negative real fixtures')
            for stage in profile.data['stages']:
                expectations = {r['case']['expected'] for r in results if r.get('stage') == stage}
                if not {'match','no_match'} <= expectations:
                    raise SafetyStop(f'Need positive and negative fixtures for stage {stage}')
            evidence = Path(args.cases).resolve()
            output = profile.path.parent / f'{profile.path.stem}-{profile.target}.validated.json'
            output.write_text(json.dumps(dict(profile_sha256=profile.digest, target=profile.target,
                hardware_verified=True, video_backend=args.backend, evidence=str(evidence),
                evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
                operator_attested_at=time.time()), indent=2) + '\n', encoding='utf-8')
            print(f'Operator validation receipt: {output}')


if __name__ == '__main__':
    try:
        main()
    except (SafetyStop, OSError, ValueError, KeyError) as error:
        raise SystemExit(f'SAFE STOP: {error}')
