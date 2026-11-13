"""Requires a real macOS GUI session. No physical 3DS; synthetic network frames."""
import os
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import io
import socket
import threading
import time
from unittest.mock import patch
from PIL import Image, ImageDraw
from gift_recognition import Profile
from USUMShinyHunter_GUI import ShinyHunterUSUM


def main():
    with tempfile.TemporaryDirectory() as td:
        os.environ['USUM_DATA_DIR']=str(Path(td)/'settings')
        os.environ['USUM_CAPTURE_DIR']=str(Path(td)/'captures')
        app=ShinyHunterUSUM()
        app.update_idletasks()
        assert app.General.language.get()=='Japanese'
        assert app.General.dryvar.get() is True
        assert app.General.Tab.get()==1
        assert all(str(b['state'])=='disabled' for b in app.Recv.recvbtn[3:])
        assert app.winfo_height()>=app.winfo_reqheight()
        app.General.language.set('English');app.General.language_changed()
        app.General.Tab.set(1);app.Recv.recvvar.set(0)
        assert all(str(b['state'])=='normal' for b in app.Recv.recvbtn[3:])
        # Settings migration / round-trip, including language and profile paths.
        app.General.profilevar.set('日本語=profile.json')
        index=app.General.settingGetInd();app.GUI2data(index)
        app.General.WriteSetting(app.General.data)
        assert app.General.LoadSetting()[index].profile=='日本語=profile.json'
        app.General.profilevar.set('')
        profile=Profile('English','poipole')
        lower=Image.new('RGB',(320,240),'#222222')
        lower.paste(profile.templates['party_name'][0],(46,35))
        c=profile.data['colour'];b=c['box']
        ImageDraw.Draw(lower).rectangle((b[0],b[1],b[2]-1,b[3]-1),fill=tuple(round(x) for x in c['normal']))
        upper=Image.new('RGB',(400,240),'#eeeeee')
        udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.bind(('127.0.0.1',0));udp.settimeout(.3)
        stream_port=udp.getsockname()[1]
        sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        tcp,peer=socket.socketpair()
        halted=threading.Event()
        def produce():
            fid=0
            while not halted.is_set():
                for screen,image in enumerate((lower,upper)):
                    buf=io.BytesIO();image.rotate(-90,expand=True).save(buf,'JPEG',quality=100,subsampling=0)
                    data=buf.getvalue();chunks=[data[i:i+1400] for i in range(0,len(data),1400)]
                    for i,chunk in enumerate(chunks):
                        sender.sendto(bytes([fid,screen | (16 if i==len(chunks)-1 else 0),0,i])+chunk,('127.0.0.1',stream_port))
                fid=(fid+1)%256
                halted.wait(.04)
        producer=threading.Thread(target=produce,daemon=True);producer.start()
        app.General.IPPC.Entry.delete(0,'end');app.General.IPPC.Entry.insert(0,f'127.0.0.1:{stream_port}')
        app.General.IPDS.Entry.delete(0,'end');app.General.IPDS.Entry.insert(0,'127.0.0.1')
        errors=[]
        threading.excepthook=lambda args:errors.append(('worker_exception',str(args.exc_value)))
        app.report_callback_exception=lambda *args:errors.append(args)
        deadline=time.monotonic()+8
        def verify():
            messages='\n'.join(app.msgbox.message)
            if 'Dry-run: normal' in messages and app.TIDm is not None and not app.TIDm.is_alive():
                assert not input_server.send.called, 'dry-run sent controller input'
                assert not input_server.return_control.called, 'dry-run changed controller ownership'
                assert str(app.General.ConnectButton['relief'])=='raised'
                app.OpenPopup();app.update_idletasks();app.ClosePopup()
                halted.set();app.on_closing()
            elif time.monotonic()>deadline:
                errors.append(('timeout',messages));halted.set();app.on_closing()
            else:app.after(50,verify)
        with patch('USUMShinyHunter_GUI.open_stream',return_value=(tcp,udp)),patch('USUMShinyHunter_GUI.LumaInputServer') as cls:
            input_server=cls.return_value
            app.Connect3DS();app.after(50,verify);app.mainloop()
        halted.set();producer.join(1);sender.close();peer.close()
        assert not errors, errors
        print('PASS: native Tk startup, Japanese controls, English dry-run over synthetic JPEG UDP, zero controller packets, popup, UTF-8 settings, clean shutdown')

if __name__=='__main__':main()
