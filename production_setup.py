"""Operator's two-route Japanese production preparation; no device control."""
import json
from pathlib import Path
from gift_recognition import SafetyStop

ROOT=Path(__file__).parent
PRODUCTION_TARGETS=('poipole','typenull_aether')
DEFAULT_PARTY_BEFORE=1
SUMMARY_PROFILES={'poipole':'poipole-summary-ja.json','typenull_aether':'typenull-aether-summary-ja.json'}


def summary_profile(target):
    if target not in PRODUCTION_TARGETS:raise SafetyStop('本番対象はベベノムとエーテルのヌルです。')
    return ROOT/'profiles'/SUMMARY_PROFILES[target]


def preparation():
    config=json.loads((ROOT/'profiles'/'production-ja.json').read_text())
    if (config['schema']!=1 or config['language']!='Japanese' or
        type(config['party_before']) is not int or config['party_before']!=DEFAULT_PARTY_BEFORE or
        set(config['targets'])!=set(PRODUCTION_TARGETS) or
        config['verdict_source']!='summary_star' or config['body_can_authorize_reset'] is not False or
        config['dry_run_default'] is not True):
        raise SafetyStop('本番準備の対象・手持ち数・安全設定が不正です。')
    from summary_check import summary_buttons
    config['received_slot']=config['party_before']+1
    config['summary_buttons']=[{'button':button,'wait_seconds':seconds}
                                for button,seconds in summary_buttons(config['party_before'])]
    return config
