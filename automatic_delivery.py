"""One opt-in automatic Japanese Pikachu-delivery diagnostic, not shiny hunting."""
import json
import re
import sys
import threading
import time
import unicodedata
from pathlib import Path
from PIL import Image, ImageChops, ImageStat, ImageOps
from gift_recognition import SafetyStop, template_score
from mac_ocr import MacOCR
from rehearsal import image_score
from tppflush import LumaInputServer

DIALOGUE_BOX = [15, 170, 385, 232]


def normalized(text):
    return re.sub(r'[\s！!？?。、,・：:「」『』ー\-]', '', unicodedata.normalize('NFKC', text)).upper()


def recognize(rows, stage):
    # Low-confidence rows cannot authorize any action, especially a reset.
    text=normalized(''.join(r['text'] for r in rows))
    if stage=='receive':
        if any(word in text for word in ('いっぱい','満杯','ボックス','あずけますか','預けますか','逃が','にがす','ニックネム','レポト','セブ','交換')):
            return 'unknown',text
        past=r'ピカチュウを(?:うけとった|受け取った|受けとった|もらった)'
        if re.search(past,text):
            if any(mark in ''.join(r['text'] for r in rows) for mark in ('?','？','「','」','『','』')):
                return 'unknown',text
            relevant=[r for r in rows if normalized(r['text']) and not re.fullmatch(r'.{1,12}は',normalized(r['text']))]
            if relevant and all(r['confidence']>=.9 for r in relevant) and re.fullmatch(r'(?:[\wぁ-んァ-ヶ一-龯]{1,12}は)?'+past,text):
                return 'received',text
            return 'unknown',text
        confident=normalized(''.join(r['text'] for r in rows if r['confidence']>=.5))
        known=('さんですね','とあるおかたから','とある方から','おあずかりして',
               'とあるお方から',
               'お預かりして','おくりものを','贈り物を','おとどけもの','お届け物',
               'ピカチュウを','ピカチュウが','ピカチュウです','サトシの')
        if any(word in confident for word in known):return 'dialogue',text
    elif stage=='title':
        if 'PUSHSTARTBUTTON' in text:return 'title',text
    elif stage=='continue':
        if any(word in text for word in ('続きからはじめる','つづきからはじめる')) and any(word in text for word in ('図鑑','プレイ時間')):
            return 'continue',text
    return 'unknown',text


def screen_stage(image, stage):
    root=Path(__file__).parent/'templates/ja/Diagnostics'
    config=json.loads((root/'manifest.json').read_text())['stages'][stage]
    if not 0 < config['threshold'] <= .15:raise SafetyStop('診断画像のしきい値が不正です。')
    with Image.open(root/config['template']) as reference:
        score=template_score(image,config['box'],reference)
    return score<=config['threshold'],score,config['box']


def dialogue_visible(image):
    r,g,b=image.crop(DIALOGUE_BOX).convert('RGB').split()
    mask=ImageChops.multiply(ImageChops.multiply(r.point(lambda p:255 if p>=160 else 0),
        g.point(lambda p:255 if p>=180 else 0)),b.point(lambda p:255 if p>=170 else 0))
    return ImageStat.Stat(mask).mean[0]/255 >= .35


def corroborates_receipt(rows, expected):
    raw=''.join(r['text'] for r in rows)
    return bool(rows and all(r['confidence']>=.5 for r in rows)
                and not any(c in raw for c in ('?','？','「','」','『','』'))
                and normalized(raw)==expected)


def receipt_ocr_image(image):
    """Keep small diacritics visible, including the dark receipt message box."""
    gray=image.convert('L')
    binary=gray.point(lambda value:255 if value>140 else 0)
    return ImageOps.invert(binary) if ImageStat.Stat(gray).median[0]<128 else binary


def field_baseline(engine):
    """Use the passive field screenshot already recorded, never game data edits."""
    candidates=[]
    if engine.trace.get('steps'):candidates.append((engine.trace,engine.trace_directory))
    paths=list(engine.output.glob('delivery-*/trace-draft.json'))+list(engine.output.glob('delivery-*/auto-baseline.json'))
    for path in sorted(paths,key=lambda p:p.stat().st_mtime,reverse=True):
        try:candidates.append((json.loads(path.read_text()),path.parent))
        except (OSError,ValueError):continue
    for trace,directory in candidates:
        if trace.get('backend')!=engine.backend or not trace.get('steps'):continue
        step=trace['steps'][0]
        if step.get('button')!='A':continue
        result={}
        for key in ('0','1'):
            path=(Path(directory)/step.get('references',{}).get(key,'missing')).resolve()
            if not path.is_relative_to(Path(directory).resolve()):break
            try:
                with Image.open(path) as image:
                    if image.size != ((320,240) if key=='0' else (400,240)):break
                    result[key]=image.convert('RGB')
            except OSError:break
        if len(result)==2:return result
    return None


class AutomaticDelivery:
    def __init__(self,engine):
        self.engine=engine;self.ocr=None;self.controller=None;self.actions=0;self.reset_sent=False
        self.baseline=field_baseline(engine)

    def start(self,saved=False,approved=False,live=False,resume_received=False):
        if self.engine.playing:raise SafetyStop('別の試験が動作中です。')
        if live and (not saved or not approved):raise SafetyStop('受取前のセーブと今回の実行許可が必要です。')
        if live and not self.engine.report.get('automatic_dry_run_verified'):
            raise SafetyStop('先に「認識確認（送信0）」を完了してください。')
        if live and self.baseline is None:raise SafetyStop('開始位置の基準画像がありません。フィールド画面から認識確認を行ってください。')
        ready=self.engine.report.get('automatic_ready_state')
        if live and ready=='received' and not resume_received:
            raise SafetyStop('受取済みです。「受取後の復帰テスト」を選んでください。')
        if live and resume_received and ready!='received':
            raise SafetyStop('受取済み画面の認識確認が必要です。')
        self.resume_received=bool(resume_received)
        self.engine.healthy()
        self.engine.player=threading.Thread(target=self.run,args=(live,),daemon=True)
        self.engine.player.start()

    def observe(self,stage,since,previous='',timeout=25):
        end=time.monotonic()+timeout;serials={};last=None;stable=0;fresh=0
        while time.monotonic()<end:
            frames=self.engine.healthy()
            if not all(frames[k].serial>serials.get(k,0) and frames[k].started is not None and frames[k].started>=since for k in ('0','1')):
                self.engine.stop.wait(.03);continue
            serials={k:f.serial for k,f in frames.items()};fresh+=1
            if fresh<3:continue
            image=frames['1'].image
            if stage in ('title','continue'):
                matched,score,_=screen_stage(image,stage)
                self.engine.event('automatic_screen_match',stage=stage,score=score,matched=matched)
                self.engine.notify('scores',{'1':score})
                stable=stable+1 if matched else 0
                if stable>=3:return stage,stage,image
                continue
            crop=image.crop(DIALOGUE_BOX) if stage=='receive' else image
            rows=self.ocr.read(crop)
            decision,text=recognize(rows,stage)
            if time.monotonic()-frames['1'].received>2:
                stable=0;continue
            if decision=='received':
                raw_rows=self.ocr.read(receipt_ocr_image(crop),correction=False)
                corroborated=corroborates_receipt(raw_rows,text)
                self.engine.event('automatic_receipt_corroboration',rows=raw_rows,matched=corroborated)
                if not corroborated:decision='unknown'
                if time.monotonic()-frames['1'].received>2:
                    stable=0;continue
            if decision=='unknown' and self.actions==0 and not dialogue_visible(image):
                hud,_,_=screen_stage(frames['0'].image,'field_hud')
                if hud and not self.live:
                    self.baseline={k:f.image.copy() for k,f in frames.items()}
                    refs={}
                    for k,im in self.baseline.items():
                        filename=f'auto-baseline-{k}.png';im.save(self.engine.directory/filename);refs[k]=filename
                    (self.engine.directory/'auto-baseline.json').write_text(json.dumps({'backend':self.engine.backend,'steps':[{'button':'A','references':refs}]}))
                if self.baseline is not None and hud:
                    scores={k:image_score(frames[k].image,self.baseline[k],[0,0,*self.baseline[k].size]) for k in ('0','1')}
                    if all(s<=.035 for s in scores.values()):decision,text='field','verified_field'
            self.engine.event('automatic_ocr',stage=stage,rows=rows,decision=decision,text=text)
            self.engine.notify('ocr',text or '文字を認識できません')
            self.engine.healthy()
            if decision!='unknown' and text!=previous:
                signature=(decision,text)
                stable=stable+1 if signature==last else 1;last=signature
                if stable>=2:return decision,text,image
            else:stable=0;last=None
            self.engine.stop.wait(.2)
        raise SafetyStop(f'{stage}: 日本語画面を確実に認識できません。追加入力・リセットを送りません。')

    def send(self,button,image,box):
        if button=='RESET' and self.reset_sent:raise SafetyStop('リセットは1回だけです。')
        if button=='RESET':self.reset_sent=True
        if self.actions>=15:raise SafetyStop('操作回数の上限です。')
        self.actions+=1
        if button=='RESET':
            current=self.engine.healthy()['1']
            rows=self.ocr.read(current.image.crop(DIALOGUE_BOX))
            decision,text=recognize(rows,'receive')
            raw=self.ocr.read(receipt_ocr_image(current.image.crop(DIALOGUE_BOX)),correction=False)
            self.engine.event('automatic_final_reset_check',rows=rows,raw_rows=raw,decision=decision)
            if decision!='received' or not corroborates_receipt(raw,text) or time.monotonic()-current.received>2:
                raise SafetyStop('送信直前の受取完了確認が不明です。リセットしません。')
            image=current.image
        filename=f'auto-before-{self.actions:02d}.png';image.save(self.engine.directory/filename)
        step={'references':{'1':filename},'boxes':{'1':box}}
        self.engine._send(button,self.controller,step)

    def wait_field(self,since):
        if self.baseline is None:raise SafetyStop('復帰の基準画像がありません。追加操作せず停止します。')
        end=time.monotonic()+45;stable=0;serials={}
        while time.monotonic()<end:
            frames=self.engine.healthy()
            if not all(frames[k].serial>serials.get(k,0) and frames[k].started is not None and frames[k].started>=since for k in ('0','1')):
                self.engine.stop.wait(.03);continue
            serials={k:f.serial for k,f in frames.items()}
            scores={k:image_score(frames[k].image,self.baseline[k],[0,0,*self.baseline[k].size]) for k in ('0','1')}
            self.engine.event('automatic_field_match',scores=scores)
            stable=stable+1 if all(v<=.05 for v in scores.values()) else 0
            if stable>=3:
                for k,f in frames.items():f.image.save(self.engine.directory/f'auto-restored-field-{k}.png')
                return
        raise SafetyStop('リセット後の開始位置を確認できません。再リセットしません。')

    def run(self,live=False):
        engine=self.engine
        self.live=live
        resume_received=getattr(self,'resume_received',False)
        try:
            engine.report.update(live=live,automatic_delivery=True,shiny_verified=False,resume_received=resume_received)
            engine.status('日本語OCRを準備中。3DSへの入力はまだ送りません。')
            self.ocr=MacOCR(Path(sys.prefix)/'ocr-cache')
            # Initial framework/model preparation is passive. Its result NEVER
            # authorizes input; fresh frames are collected again afterwards.
            self.ocr.read(engine.healthy()['1'].image,timeout=65)
            since=time.monotonic();previous=''
            if live:self.controller=LumaInputServer(engine.console[0],engine.input_port)
            while True:
                engine.status('日本語の受取会話を確認中。読めない画面は操作しません。')
                decision,text,image=self.observe('receive',since,previous)
                if not live:
                    engine.report['automatic_dry_run_verified']=decision in ('field','dialogue','received')
                    engine.report['automatic_ready_state']=decision
                    engine.event('automatic_dry_run',next_action='RESET' if decision=='received' else 'A',controller_packets=0)
                    engine.status('認識確認完了（送信0）。'+('受取済みです。「受取後の復帰テスト」で続けられます。' if decision=='received' else '自動テストを開始できます。'))
                    return
                if decision=='received':
                    engine.status('ピカチュウ受取完了を複数の新しい映像で確認。リセットを1回送信します。')
                    self.send('RESET',image,DIALOGUE_BOX);break
                if resume_received:raise SafetyStop('受取済み画面を確認できません。受取操作もリセットも送りません。')
                if self.actions>=12:raise SafetyStop('受取前の操作上限です。追加操作・リセットは送りません。')
                self.send('A',image,[0,0,400,240] if decision=='field' else DIALOGUE_BOX)
                previous=text;since=time.monotonic()
            since=time.monotonic();engine.status('リセット後のタイトルを待っています。')
            _,_,image=self.observe('title',since,timeout=50)
            self.send('START',image,screen_stage(image,'title')[2])
            since=time.monotonic();engine.status('「続きから はじめる」を確認中。')
            _,_,image=self.observe('continue',since)
            self.send('A',image,screen_stage(image,'continue')[2])
            engine.status('開始位置への復帰を確認中。')
            self.wait_field(time.monotonic())
            engine.report['automatic_dry_run_verified']=False
            engine.report['automatic_ready_state']=None
            if resume_received:
                engine.report['completed_recoveries']=engine.report.get('completed_recoveries',0)+1
                engine.status('受取後の復帰確認が完了しました。次は「認識確認→自動テスト1周」で一連の動作を確認できます。')
            else:
                engine.report['completed_cycles']+=1
                engine.status('自動受取→リセット1回→開始位置への復帰を確認しました。色違い判定は未検証です。')
        except Exception as error:engine.fail(error)
        finally:
            if self.controller is not None:self.controller.socket.close()
            if self.ocr is not None:self.ocr.close()
            engine.notify('play_finished',None);engine.write_report()
