"""Stable summary-page checks; reuse the upstream star ROI and colour classifier.

The shipped colour values are upstream references, not Japanese calibration.
Name/context anchors are mandatory even if an arbitrary patch matches a colour.
"""
import hashlib
import json
import re
from pathlib import Path
from PIL import Image
from automatic_delivery import normalized
from gift_recognition import SafetyStop, colour_verdict

CONFIG = Path(__file__).parent / 'profiles' / 'pikachu-diagnostic-ja.json'


def load_config(path=CONFIG):
    raw=Path(path).read_bytes();config=json.loads(raw)
    if config.get('schema')!=1 or config.get('language')!='Japanese' or config.get('target') not in ('ピカチュウ','ベベノム','タイプ：ヌル'):
        raise SafetyStop('情報画面の診断設定が不正です。')
    if config['colour']['screen'] not in (0,1):raise SafetyStop('色判定の画面が不正です。')
    if config['samples']!=3 or config['name_threshold']!=.9 or config['context_threshold']!=.8:
        raise SafetyStop('診断の判定条件が変更されています。')
    colour_verdict(Image.new('RGB',((320 if config['colour']['screen']==0 else 400),240)),config['colour'])
    config['digest']=hashlib.sha256(raw).hexdigest()
    return config


def check_summary(images,ocr,config):
    rows={key:ocr.read(image) for key,image in images.items()}
    name=any(normalized(config['target']) in normalized(row['text']) and row['confidence']>=config['name_threshold']
             for values in rows.values() for row in values)
    text=' '.join(normalized(row['text']) for values in rows.values() for row in values
                  if row['confidence']>=config['context_threshold'])
    # A party list or context menu has no OT/ID/experience fields. Require two
    # independent groups, not just a Pokemon name or the word "summary".
    groups=(('おや','親'),('IDNO','IDナンバ'),('けいけんち','経験値'),('つぎのレベル','次のレベル'))
    anchors=[group[0] for group in groups if any(token in text for token in group)]
    method='high_score_name';raw_name_rows=None
    if not name and config.get('name_verification')=='dual_screen_exact_uncorrected' and len(anchors)>=2:
        # Native Vision's CJK scores are discrete, not probabilities. A rare
        # species may be read exactly at .3 on BOTH screens. Do not lower the
        # single-read threshold: require exact labels on both screens plus an
        # uncorrected read of both, then the caller's three-frame consensus and
        # final reset recheck. One weak label alone cannot authorize anything.
        pattern=r'(?:名前)?'+re.escape(normalized(config['target']))+r'(?:[♂♀]|LV\.?[0-9]{1,3})*'
        def exact(values):
            return any(row['confidence']>=.3 and re.fullmatch(pattern,normalized(row['text'])) for row in values)
        if all(exact(rows[key]) for key in ('0','1')):
            raw_name_rows={key:ocr.read(images[key],correction=False) for key in ('0','1')}
            name=all(exact(raw_name_rows[key]) for key in ('0','1'))
            method='dual_screen_exact_uncorrected' if name else 'uncorrected_name_mismatch'
    result=colour_verdict(images[str(config['colour']['screen'])],config['colour'])
    result.update(name_matched=name,context=anchors,rows=rows,name_verification=method)
    if raw_name_rows is not None:result['uncorrected_name_rows']=raw_name_rows
    if not name or len(anchors)<2:result['verdict']='unknown'
    return result


def native_summary_images(upper,lower):
    images={}
    for key,path,size in (('0',lower,(320,240)),('1',upper,(400,240))):
        with Image.open(path) as image:
            if image.size!=size:raise SafetyStop('情報画面の原寸PNGが必要です（下320×240、上400×240）。')
            images[key]=image.convert('RGB')
    return images


def replay_summary(target,upper,lower,ocr):
    """Read-only native image replay. Screenshots of other scenes fail closed."""
    from production_setup import summary_profile
    config=load_config(summary_profile(target));images=native_summary_images(upper,lower)
    result=check_summary(images,ocr,config)
    return dict(result,target=target,profile_sha256=config['digest'],
                calibration_status=config['calibration_status'],controller_packets=0,reset_authorized=False)


def summary_buttons(party_before):
    """Saved menu entry: Pokemon; party cursor: first. Gift occupies last slot."""
    if type(party_before) is not int or not 1<=party_before<=5:
        raise SafetyStop('受取前の手持ち数は1〜5匹です。')
    # Reuse upstream's ten B presses to clear nickname and remaining dialogue.
    sequence=[('B',.5)]*10+[('X',2),('A',3)]
    row,column=divmod(party_before,2)
    if column:sequence.append(('DPADRIGHT',1))
    sequence += [('DPADDOWN',1)]*row
    return sequence+[('A',1),('A',3)]
