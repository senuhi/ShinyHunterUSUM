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
        app=ShinyHunterUSUM();app.OpenDiagnostics();app.update()
        window=app.Diagnostics
        app.title('模擬テスト · 実機未接続');window.title('模擬自動テスト · 実機未接続')
        assert not window.advanced.get() and not window.record_frame.winfo_ismapped()
        assert window.auto_frame.winfo_ismapped() and window.engine is None
        assert window.winfo_reqheight()+45 < window.winfo_screenheight()
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen();server.settimeout(3)
        inputs=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);inputs.bind(('127.0.0.1',0));inputs.settimeout(.1)
        halted=threading.Event();lock=threading.Lock();state=[0];downs=[];errors=[]
        font=ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',18)
        assets=ROOT/'templates/ja/Diagnostics';manifest=json.loads((assets/'manifest.json').read_text())['stages']
        expected=[int(HIDButtons.A)]*3+[int(HIDButtons.L|HIDButtons.R|HIDButtons.SELECT),int(HIDButtons.START),int(HIDButtons.A)]
        delays=[];jitter_injected=[False]
        def native_image(screen,phase,tick):
            image=Image.new('RGB',((320 if screen==0 else 400),240),(60+(tick%3),95,75))
            draw=ImageDraw.Draw(image)
            if screen==0:
                if phase in (0,1,2,3):image.paste(Image.open(assets/'field_hud.png'),(0,0))
                else:draw.rectangle((10,10,300,200),fill='#406080')
            elif phase in (1,2,3):
                draw.rectangle((15,170,385,232),fill='#30281c' if phase==3 else 'white')
                text='とあるおかたから ピカチュウを' if phase in (1,2) else 'ピカチュウを 受け取った！'
                draw.text((25,184),text,font=font,fill='white' if phase==3 else 'black')
            elif phase in (4,5):
                draw.text((20,80),'NO NAVIGATION MATCHING FIXTURE',fill='white')
            else:draw.rectangle((20,20,180,100),fill='white')
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
                if not halted.is_set():errors.append(('stream',str(error)))
        def receive_inputs():
            try:
                while not halted.is_set():
                    try:data,_=inputs.recvfrom(100)
                    except socket.timeout:continue
                    assert len(data)==20
                    if data.hex()=='ff0f000000000002fff77f008100808000000000':continue
                    assert data[16:]==bytes(4)
                    buttons=(~int.from_bytes(data[:4],'little')) & 0xffffffff
                    if buttons:
                        assert len(downs)<len(expected) and buttons==expected[len(downs)],(downs,buttons)
                        downs.append(buttons)
                        with lock:state[0]=(state[0]+1)%6
            except Exception as error:errors.append(('input',str(error)))
        producer=threading.Thread(target=produce,daemon=True);consumer=threading.Thread(target=receive_inputs,daemon=True)
        producer.start();consumer.start()
        window.local.set('127.0.0.1:8001');window.console.set(f'127.0.0.1:{server.getsockname()[1]}')
        window.input_port.set(str(inputs.getsockname()[1]));window.saved.set(True)
        window.connect_button.invoke()
        phase=['receive'];deadline=time.monotonic()+70
        app.report_callback_exception=lambda *args:errors.append(('GUI',str(args)))
        def watch():
            engine=window.engine
            if engine is not None and engine.stop.is_set():errors.append(('safe_stop',engine.report['status']))
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
            elif phase[0]=='live' and not engine.playing and engine.report['completed_cycles']==1:
                assert downs==expected
                assert engine.report['reset_attempts']==1 and engine.report['controller_packets']==len(expected)*3
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
        assert delays==[3,3,3,25,5,12],delays
        assert jitter_injected[0]
        print(f'PASS: fixed GUI, loopback TCP/UDP, post-receipt Vision only, delayed fractions, {len(expected)*3} datagrams; timers shortened; NO HARDWARE')


if __name__=='__main__':main()
