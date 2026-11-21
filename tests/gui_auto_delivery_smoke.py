"""Native GUI + real loopback Chiruno TCP/Luma UDP + local Vision OCR.

All game images/transitions are synthetic. This never accesses a physical 3DS.
"""
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont
from chiruno_transport import packet, setup_packets
from tppflush import HIDButtons
from summary_check import summary_buttons
from gift_navigation import ROOT as NAV_ROOT
from USUMShinyHunter_GUI import ShinyHunterUSUM

ROOT=Path(__file__).resolve().parents[1]


def main():
    def audit(event,args):
        if event=='socket.connect' and args[1][0]!='127.0.0.1':
            raise RuntimeError('Test forbids non-loopback connections')
    sys.addaudithook(audit)
    with tempfile.TemporaryDirectory() as td:
        os.environ['USUM_DATA_DIR']=str(Path(td)/'settings')
        os.environ['USUM_CAPTURE_DIR']=str(Path(td)/'captures')
        production='--production' in sys.argv[1:]
        packets_per_press=7 if production else 3
        navigation_manifest=json.loads((NAV_ROOT/'manifest.json').read_text())
        null_target='--null' in sys.argv[1:]
        drop_start=production and '--drop-first-start' in sys.argv[1:]
        resume_pending=production and '--resume-pending' in sys.argv[1:]
        late_dialogue=production and '--late-dialogue' in sys.argv[1:]
        pending_dialogue=[resume_pending];late_triggered=[False]
        target_name=('タイプ：ヌル' if null_target else 'ベベノム') if production else 'ピカチュウ'
        app=ShinyHunterUSUM()
        if resume_pending:app.resume_receipt_directory=str(Path(td)/'previous')
        if production:app.OpenGiftHunt()
        else:app.OpenDiagnostics()
        app.update()
        window=app.Diagnostics
        app.title('模擬テスト · 実機未接続');window.title('模擬自動テスト · 実機未接続')
        assert not window.advanced.get() and not window.record_frame.winfo_ismapped()
        assert window.auto_frame.winfo_ismapped() and window.engine is None
        assert window.stop_at_summary.get() is True and window.party_before.get()==1
        assert window.winfo_reqheight()+45 < window.winfo_screenheight()
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen();server.settimeout(3)
        inputs=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);inputs.bind(('127.0.0.1',0));inputs.settimeout(.1)
        halted=threading.Event();lock=threading.Lock();state=[0];downs=[];errors=[]
        font=ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',18)
        assets=ROOT/'templates/ja/Diagnostics'
        party_before=1 if '--party-one' in sys.argv[1:] else 4
        nav=summary_buttons(party_before);summary_phase=3+len(nav)
        only_summary='--summary-only' in sys.argv[1:]
        if production:
            window.target.set('ヌル・ポニ' if null_target else 'ベベノム');window.cycle_limit.set(1)
        shiny_summary='--summary-shiny' in sys.argv[1:]
        expect_stop=only_summary or shiny_summary
        expected_verdict='shiny' if shiny_summary else 'normal'
        expected=[int(HIDButtons.A)]*(4 if drop_start else 3)+[int(getattr(HIDButtons,b)) for b,_ in nav]
        if resume_pending:expected=[int(HIDButtons.B)]+[int(getattr(HIDButtons,b)) for b,_ in nav[10:]]
        elif late_dialogue:expected[13:13]=[int(HIDButtons.X),int(HIDButtons.B)]
        if not expect_stop:expected += [int(HIDButtons.L|HIDButtons.R|HIDButtons.SELECT),int(HIDButtons.START),int(HIDButtons.A)]
        delays=[];jitter_injected=[False]
        def native_image(screen,phase,tick):
            dialogue_here=production and phase==13 and pending_dialogue[0]
            if production and phase==13:phase=0  # registration/dialogue has ended
            image=Image.new('RGB',((320 if screen==0 else 400),240),(60+(tick%3),95,75))
            draw=ImageDraw.Draw(image)
            if screen==0:
                if phase in (0,1,2,3):image.paste(Image.open(assets/'field_hud.png'),(0,0))
                else:draw.rectangle((10,10,300,200),fill='#406080')
            elif phase in (1,2,3):
                draw.rectangle((15,170,385,232),fill='#30281c' if phase==3 else 'white')
                text='とあるおかたから '+target_name+'を' if phase in (1,2) else target_name+'を 受け取った！'
                draw.text((25,184),text,font=font,fill='white' if phase==3 else 'black')
            elif phase>=4:
                draw.text((20,80),'NO NAVIGATION MATCHING FIXTURE',fill='white')
            else:draw.rectangle((20,20,180,100),fill='white')
            if dialogue_here and screen==1:
                draw.rectangle((15,170,385,235),fill='white')
                draw.text((25,184),'ありがとう アローラの人',font=font,fill='black')
            if production and screen==0 and phase in (14,15,16):
                kind='menu' if phase==14 else 'party'
                for item in navigation_manifest['states'][kind]:
                    with Image.open(NAV_ROOT/item['template']) as part:image.paste(part,item['box'][:2])
                if phase in (15,16):
                    x,y=(3,32) if phase==15 else (173,48)
                    draw.rectangle((x,y,x+8,y+10),fill=(230,35,20))
            if production and phase==17 and screen==0:
                draw.text((60,150),'つよさをみる',font=font,fill='white')
            if phase==summary_phase:
                image=Image.new('RGB',image.size,(129,242,74));draw=ImageDraw.Draw(image)
                if screen==0:
                    draw.text((20,20),target_name,font=font,fill='black')
                    draw.text((20,60),'おや サトシ',font=font,fill='black')
                    draw.text((20,95),'IDNo. 12345',font=font,fill='black')
                    draw.rectangle((59,184,66,191),fill=(129,242,74))
                    if shiny_summary:
                        # Keep the main patch normal: the alternate-position
                        # red star must independently prevent any reset.
                        draw.rectangle((47,188,52,193),fill=(210,55,15))
                else:
                    if production:draw.text((20,20),target_name,font=font,fill='black')
                    draw.text((20,60),'けいけんち',font=font,fill='black')
                    draw.text((20,95),'つぎのレベルまで',font=font,fill='black')
            if screen==0 and phase==0 and len(downs)>=len(expected):
                # A real post-reset Rotom question differs from the map; the
                # upper saved-location scene is the final return criterion.
                image=Image.new('RGB',image.size,'#eac090')
                ImageDraw.Draw(image).text((20,60),'ROTOM QUESTION',fill='black')
            return image
        def produce():
            try:
                connection,_=server.accept()
                with connection:
                    connection.settimeout(3);data=b''
                    while len(data)<44:data+=connection.recv(44-len(data))
                    assert data==b''.join(setup_packets(50))
                    tick=0
                    while not halted.is_set():
                        with lock:phase=state[0]
                        images={screen:native_image(screen,phase,tick) for screen in (1,0)}
                        for i in range(8):
                            for screen in (1,0):
                                image=images[screen];width=image.width//8
                                raw=image.crop((i*width,0,(i+1)*width,240)).rotate(-90,expand=True)
                                r,g,b=raw.split();raw=Image.merge('RGB',(b,g,r))
                                buffer=io.BytesIO();raw.save(buffer,'JPEG',quality=50)
                                connection.sendall(packet(1,0x11 if screen==0 else 1,buffer.getvalue(),8|i))
                            if phase==3 and i==4 and not jitter_injected[0]:
                                jitter_injected[0]=True;halted.wait(1.1)
                            halted.wait(.065)
                        tick+=1
            except Exception as error:
                if not halted.is_set() and not (production and window.engine.stop.is_set()):errors.append(('stream',str(error)))
        def receive_inputs():
            held=0
            try:
                while not halted.is_set():
                    try:data,_=inputs.recvfrom(100)
                    except socket.timeout:continue
                    assert len(data)==20
                    if data.hex()=='ff0f000000000002fff77f008100808000000000':held=0;continue
                    assert data[16:]==bytes(4)
                    buttons=(~int.from_bytes(data[:4],'little')) & 0xffffffff
                    if not buttons:held=0
                    if buttons and buttons!=held:
                        held=buttons
                        assert len(downs)<len(expected) and buttons==expected[len(downs)],(downs,buttons)
                        downs.append(buttons)
                        if late_dialogue and state[0]==13 and buttons==int(HIDButtons.X) and not late_triggered[0]:
                            late_triggered[0]=True;pending_dialogue[0]=True
                        elif state[0]==13 and pending_dialogue[0] and buttons==int(HIDButtons.B):
                            pending_dialogue[0]=False
                        elif not (drop_start and len(downs)==1):
                            with lock:state[0]=(state[0]+1)%(summary_phase+3)
            except Exception as error:errors.append(('input',str(error)))
        if resume_pending:
            previous=Path(td)/'previous';previous.mkdir()
            for key in (0,1):native_image(key,0,0).save(previous/f'fixed-baseline-{key}.png')
            native_image(1,3,0).save(previous/'received-message.png')
            (previous/'report.json').write_text(json.dumps(dict(mode='app_gift_hunt',target="typenull_poni" if null_target else "poipole",round=1,completed_cycles=0,reset_attempts=0,summary_verdict='unknown',summary_scores={'context':[]})))
            state[0]=13
        producer=threading.Thread(target=produce,daemon=True);consumer=threading.Thread(target=receive_inputs,daemon=True)
        producer.start();consumer.start()
        window.local.set('127.0.0.1:8001');window.console.set(f'127.0.0.1:{server.getsockname()[1]}')
        window.input_port.set(str(inputs.getsockname()[1]));window.saved.set(True)
        window.stop_at_summary.set(only_summary);window.party_before.set(party_before)
        window.connect_button.invoke()
        phase=['receive'];deadline=time.monotonic()+70
        app.report_callback_exception=lambda *args:errors.append(('GUI',str(args)))
        def watch():
            engine=window.engine
            if engine is not None and engine.stop.is_set() and (not production or engine.report['status'].startswith('安全停止')):errors.append(('safe_stop',engine.report['status']))
            if errors or time.monotonic()>deadline:
                if not errors:errors.append(('timeout',engine.report if engine else None))
                if engine is not None:
                    events=[json.loads(line) for line in (engine.directory/'events.jsonl').read_text().splitlines()]
                    print(json.dumps([row for row in events if row['event']!='frame'][-18:],ensure_ascii=False,indent=2))
                halted.set();app.on_closing();return
            if phase[0]=='receive' and engine is not None and min(engine.counts.values())>=3:
                phase[0]='dry_run';window.auto_check_button.invoke()
            elif phase[0]=='dry_run' and not engine.playing and engine.report.get('fixed_preflight_verified') and str(window.auto_live_button['state'])=='normal':
                assert engine.report['controller_packets']==0 and not downs
                phase[0]='live';window.auto_live_button.invoke()
            elif phase[0]=='live' and not engine.playing and (engine.report.get('summary_verdict')==expected_verdict if expect_stop else engine.report['completed_cycles']==1):
                assert downs==expected
                assert engine.report['reset_attempts']==(0 if expect_stop else 1) and engine.report['controller_packets']==len(expected)*packets_per_press+(9 if production and null_target else 0)
                assert engine.report['summary_verdict']==expected_verdict
                assert engine.report['completed_cycles']==(0 if expect_stop else 1)
                phase[0]='passed';halted.set();app.on_closing();return
            app.after(50,watch)
        from fixed_delivery import FixedDelivery
        original_wait=FixedDelivery.wait
        def fast_wait(runner,seconds,label):
            delays.append(seconds);return original_wait(runner,.1,label)
        try:
            with patch('rehearsal_gui.messagebox.askyesno',return_value=True),patch.object(FixedDelivery,'wait',fast_wait):
                app.after(50,watch);app.mainloop()
        finally:
            halted.set();producer.join(2);consumer.join(2);server.close();inputs.close()
        assert not errors,errors
        assert phase[0]=='passed',phase
        receipt_delays=([.1]*3 if null_target else [])+[1]*(4 if drop_start else 3) if production else [3]*3
        expected_delays=receipt_delays+[d for _,d in nav]
        if resume_pending:expected_delays=[.5]+[d for _,d in nav[10:]]
        elif late_dialogue:expected_delays=receipt_delays+[.5]*10+[2,.5]+[d for _,d in nav[10:]]
        assert delays==expected_delays+([] if expect_stop else [25,5,12]),delays
        if not resume_pending:assert jitter_injected[0]
        if drop_start:
            events=[json.loads(line) for line in (window.engine.directory/'events.jsonl').read_text().splitlines()]
            assert len([row for row in events if row['event']=='receipt_start_retry'])==1
        print(f'PASS: fixed GUI, loopback TCP/UDP, receipt and summary Vision, verdict={expected_verdict}, resets={0 if expect_stop else 1}, delayed fractions, {len(expected)*packets_per_press+(9 if production and null_target else 0)} datagrams; production={production}; missed_start={drop_start}; resume={resume_pending}; late_dialogue={late_dialogue}; timers shortened; NO HARDWARE')


if __name__=='__main__':main()
