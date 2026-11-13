"""Operator attestation of Old 3DS HIMEM video/input coexistence.

Neither successful TCP connection nor UDP send is hardware verification.
This is a local, explicitly operator-confirmed gate, not automatic certification.
"""
import hashlib
import json
from pathlib import Path
from platform_support import data_directory


def hardware_context(backend, console, input_port=4950, quality=80, max_span=2.0):
    return dict(backend=backend, console=list(console), input_port=input_port,
                quality=quality, max_span=float(max_span))


def receipt_path(context, directory=None):
    key = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:20]
    return Path(directory or data_directory()) / f'old3ds-himem-{key}.json'


def require_hardware(context, directory=None):
    if context['backend'] != 'ChirunoMod':
        return
    try:
        receipt = json.loads(receipt_path(context, directory).read_text(encoding='utf-8'))
        report_path = Path(receipt['report'])
        content = report_path.read_bytes()
        report = json.loads(content)
        if (receipt.get('schema') != 1 or receipt.get('context') != context or
            receipt.get('operator_confirmed_coexistence') is not True or
            receipt.get('operator_confirmed_manual_reset_continuity') is not True or
            receipt.get('environment') != dict(console='Old 3DS LL', luma='13.4',
                streamer='ChirunoMod 0.2.2', loader='ChLoad_HIMEM', game='Japanese USUM') or
            hashlib.sha256(content).hexdigest() != receipt['report_sha256'] or
            report.get('context') != context or report.get('status') != 'observed' or
            report.get('input_probe_completed') is not True or
            report.get('reported_himem_usum') is not True or
            not all(report.get('frames_after_input', {}).get(str(s), 0) >= 3 for s in (0,1))):
            raise ValueError('Incomplete/mismatched Old 3DS coexistence evidence')
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise OSError('ChirunoMod live blocked: Old 3DS HIMEM video + input coexistence '
                      'and manual reset continuity need operator-verified evidence; '
                      'see docs/OLD3DS_HIMEM_JA.md') from error
