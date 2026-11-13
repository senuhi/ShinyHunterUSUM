"""Native Tk + synthetic loopback video. Never connects to a physical console."""
import os
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import io
import socket
import threading
import time
from unittest.mock import patch
from PIL import Image, ImageDraw
from gift_recognition import Profile
from USUMShinyHunter_GUI import ShinyHunterUSUM
from chiruno_transport import packet, setup_packets


def main(backend):
    with tempfile.TemporaryDirectory() as td:
        os.environ['USUM_DATA_DIR']=str(Path(td)/'settings')
        os.environ['USUM_CAPTURE_DIR']=str(Path(td)/'captures')
        app=ShinyHunterUSUM();app.update_idletasks()
        assert app.General.language.get()=='Japanese'
        assert app.General.dryvar.get() is True
        assert app.General.backend.get()=='ChirunoMod'
        assert app.General.Tab.get()==1
        assert all(str(b['state'])=='disabled' for b in app.Recv.recvbtn[3:])
        assert app.winfo_height()>=app.winfo_reqheight()
        app.General.language.set('English');app.General.language_changed()
        app.General.backend.set(backend);app.General.backend_changed()
        app.General.Tab.set(1);app.Recv.recvvar.set(0)
        assert all(str(b['state'])=='normal' for b in app.Recv.recvbtn[3:])
        app.General.inputport.set('4959')
        app.General.profilevar.set('日本語=profile.json')
        index=app.General.settingGetInd();app.GUI2data(index);app.General.WriteSetting(app.General.data)
        loaded=app.General.LoadSetting()[index]
        assert loaded.profile=='日本語=profile.json' and loaded.backend==backend and loaded.inputport==4959
        app.General.profilevar.set('')
        profile=Profile('English','poipole')
        lower=Image.new('RGB',(320,240),'#222222');lower.paste(profile.templates['party_name'][0],(46,35))
        c=profile.data['colour'];b=c['box']
        ImageDraw.Draw(lower).rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=tuple(round(x) for x in c['normal']))
        upper=Image.new('RGB',(400,240),'#eeeeee')
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(3)
        probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);probe.bind(('127.0.0.1',0))
        stream_port=probe.getsockname()[1];probe.close()
        sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        halted=threading.Event();errors=[]
        threading.excepthook=lambda args:errors.append(('worker_exception',str(args.exc_value)))
        def produce():
            try:
                connection,_=listener.accept();connection.settimeout(3)
                with connection:
                    expected=44 if backend=='ChirunoMod' else 336
                    data=b''
                    while len(data)<expected:data+=connection.recv(expected-len(data))
                    if backend=='ChirunoMod':assert data==b''.join(setup_packets())
                    fid=0
                    while not halted.is_set():
                        for screen,image in enumerate((lower,upper)):
                            if backend=='ChirunoMod':
                                for fraction in range(8):
                                    width=image.width//8
                                    raw=image.crop((fraction*width,0,(fraction+1)*width,240)).rotate(-90,expand=True)
                                    r,g,b=raw.split();raw=Image.merge('RGB',(b,g,r))
                                    buf=io.BytesIO();raw.save(buf,'JPEG',quality=100,subsampling=0)
                                    connection.sendall(packet(1,0x10 if screen==0 else 0,buf.getvalue(),8|fraction))
                            else:
                                buf=io.BytesIO();image.rotate(-90,expand=True).save(buf,'JPEG',quality=100,subsampling=0)
                                data=buf.getvalue();chunks=[data[i:i+1400] for i in range(0,len(data),1400)]
                                for i,chunk in enumerate(chunks):
                                    sender.sendto(bytes([fid,screen|(16 if i==len(chunks)-1 else 0),0,i])+chunk,('127.0.0.1',stream_port))
                        fid=(fid+1)%256;halted.wait(.04)
            except OSError as error:
                if not halted.is_set() and not app.General.stop_event.is_set():errors.append(('producer',str(error)))
        producer=threading.Thread(target=produce,daemon=True);producer.start()
        app.General.IPPC.Entry.delete(0,'end');app.General.IPPC.Entry.insert(0,f'127.0.0.1:{stream_port}')
        app.General.IPDS.Entry.delete(0,'end');app.General.IPDS.Entry.insert(0,f'127.0.0.1:{listener.getsockname()[1]}')
        app.report_callback_exception=lambda *args:errors.append(args)
        deadline=time.monotonic()+8
        def verify():
            messages='\n'.join(app.msgbox.message)
            if 'Dry-run: normal' in messages and app.TIDm is not None and not app.TIDm.is_alive():
                assert not input_server.send.called and not input_server.return_control.called
                cls.assert_called_once_with('127.0.0.1',4959)
                assert str(app.General.ConnectButton['relief'])=='raised'
                app.OpenPopup();app.update_idletasks();app.ClosePopup()
                halted.set();app.on_closing()
            elif time.monotonic()>deadline:
                errors.append(('timeout',messages));halted.set();app.on_closing()
            else:app.after(50,verify)
        with patch('USUMShinyHunter_GUI.LumaInputServer') as cls:
            input_server=cls.return_value
            app.Connect3DS();app.after(50,verify);app.mainloop()
        halted.set();producer.join(2);sender.close();listener.close()
        assert not errors, errors
        print(f'PASS: {backend}, native Tk, synthetic loopback stream, English dry-run NORMAL, zero controller packets, Japanese controls, backend/UTF-8 settings, popup, clean shutdown')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--backend',choices=('NTR-HR','ChirunoMod'),default='NTR-HR')
    main(parser.parse_args().backend)
