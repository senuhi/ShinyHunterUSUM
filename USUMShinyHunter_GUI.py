import sys, os, time, io, threading, socket, signal, queue
from platform_support import set_window_icon
from ntr_transport import endpoint, FrameStore
from video_stream import console_endpoint, open_video
from hardware_validation import hardware_context, require_hardware
from datetime import datetime

from PIL import Image, ImageTk
from tppflush import *

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from functions import *
import boxBase

from General import *
from Battle  import *
from Recv    import *
from Lotto   import *
from Record  import *
from ScreenPopup import ScreenPopup

VERSION = '1.3.2-macos-ja-preview'

# Define the application class
class ShinyHunterUSUM(tk.Tk):
    def __init__(self, *args, **kwargs):

        ########################################################################
        ############################## Initialize ##############################
        ########################################################################

        # Initialize tk
        tk.Tk.__init__(self, *args, **kwargs)
        self.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.title('Shiny Hunter USUM')
        self.ui_queue = queue.Queue()
        self.closing = False
        self._connecting = False
        self.ir = None
        self._drawn = [None, None]
        self.after(40, self.ui_tick)
        myFont = tkfont.Font(family=FindFont(), size=11)
        self.option_add( '*font', myFont )
        # Load Icons
        set_window_icon(self, resource_path('image0/star.ico'))
        # Locate to the middle
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        # Dimension of the GUI
        w=480
        h=640
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.geometry(f'{w}x{h}+{int(x)}+{int(y)}')
        self.resizable(width=True, height=True)
        self.columnconfigure(0, weight=1)
        # Load images in ./image0
        self.bitmap = load_bitmaps('image0')
        # Parameters
        self.bytes = [b'', b'']
        self.image = [None,None]
        self.frame_curr = -1
        self.index_prev = -1
        self.TID  = None   # connect-pipeline thread
        self.TIDm = None   # hunting thread

        ########################################################################
        ########################## GUI objects : Row 0 #########################
        ########################################################################

        # Frame Row 0
        self.frame0 = tk.LabelFrame(self, text = 'Screen')
        self.frame0.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
        # Frame and objects for upper screen
        self.upperVal   = tk.IntVar()
        self.upperframe = tk.Frame(self.frame0)
        self.upperframe .grid(row=0, column=0, padx=0, pady=0, sticky='w')
        self.upperlabel = tk.Label(self.upperframe, image=self.bitmap['Upper'])
        self.upperlabel .config(height=72, width=120)
        self.upperlabel .grid(row=0, column=0, padx=12, pady=5, sticky='w')
        self.upperbtn   = tk.Checkbutton(self.upperframe, variable=self.upperVal,
                                         command=self.screenSwitch)
        self.upperbtn   .grid(row=1, column=0, padx=10, pady=0)
        # Frame and objects for lower screen
        self.lowerVal   =tk.IntVar()
        self.lowerframe = tk.Frame(self.frame0)
        self.lowerframe .grid(row=0, column=1, padx=0, pady=0, sticky='e')
        self.lowerlabel = tk.Label(self.lowerframe, image=self.bitmap['Lower'])
        self.lowerlabel .config(height=72, width=96)
        self.lowerlabel .grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.lowerbtn   = tk.Checkbutton(self.lowerframe, variable=self.lowerVal,
                                         command=self.screenSwitch)
        self.lowerbtn   .grid(row=1, column=0, padx=5, pady=0)
        # Undock: pop the screens into a borderless window that
        # follows the main window; the button toggles it open/closed
        self.popup = None
        self.undocked = False
        self._lastpos  = None   # main-window position, for move deltas
        self.pop_form  = 0      # popup background: 0 plain / 1 / 2
        self.pop_scale = 1.0    # popup size: 1.0 full / 0.5 half
        self.undockbtn = tk.Button(self.frame0, image=self.bitmap['undock'],
                                   command=self.Undock)
        # bottom-right of the Screen frame, inset 3px left and up
        # from the corner (bordermode 'outside' measures from the
        # frame's outer edges)
        self.undockbtn .place(relx=1.0, rely=1.0, x=-3, y=-3, anchor='se',
                              bordermode='outside')
        self.bind('<Configure>', self.FollowPopup)

        ########################################################################
        ########################## GUI objects : Row 1 #########################
        ########################################################################

        # Notebook for settings and additional features
        self.nb = ttk.Notebook(self)
        self.nb .grid(row=1, column=0, padx=10, pady=0, sticky='ew')
        # Notebook format
        style   = ttk.Style()
        style.theme_create( 'MyStyle', parent=style.theme_use(), settings={
                'TNotebook': {'configure': {'tabmargins': [2, 2, 2, 0]}},
                'TNotebook.Tab': {'configure': {'padding': [5, 0]}},
                'TCombobox': {'configure': {'padding': 2, 'arrowsize': 15}}
                })
        style.theme_use('MyStyle')
        # Notebook tags, additional features are controlled here
        self.nb.framename = ['General', 'Battle', 'Recv', 'Lotto']
        self.nb.frame = [None for i in self.nb.framename]
        for i in range(len(self.nb.framename)):
            self.nb.frame[i]=tk.Frame(self.nb)
            self.nb.frame[i].config(height=105, width=250)
            self.nb.frame[i].pack()
            self.nb.add(self.nb.frame[i], text=self.nb.framename[i])

        ########################################################################
        ############################## Message Box #############################
        ########################################################################

        # Message Box
        self.frame2 = tk.Frame(self)
        self.frame2.grid(row=2, column=0, padx=10, pady=0, sticky='ew')
        self.msgbox = msgBox(self.frame2, 35, 10)
        self.msgbox.MsgAppend('Welcome to USUM Shiny Hunter '
                              f'v.{VERSION}')

        ########################################################################
        ################################ Notebook ##############################
        ########################################################################

        # Connect Notebook object with base class functions
        self.General = General(self.nb, self.msgbox)
        self.General.app = self
        self.General .ConnectButton.config(command=self.Connect3DS)
        self.General .setting.bind('<<ComboboxSelected>>', self.settingswitch)

        self.Lotto  = Lotto (self.nb, self.General, self.msgbox, self.image)
        self.Recv   = Recv  (self.nb, self.General, self.msgbox, self.image)
        self.Battle = Battle(self.nb, self.General, self.msgbox, self.image)
        self.Diagnostics = None
        tk.Button(self.Recv.frame, text='実機テスト（受取・リセット）',
                  command=self.OpenDiagnostics).grid(row=3, column=0, columnspan=3, sticky='ew', padx=3, pady=6)
        self.General.LanguageHook = self.Recv.language_switch
        self.General.RecvLockHook = self.Recv.set_locked
        # Record page: independent of the hunting-mode machinery, so
        # it lives outside nb.framename and the Tab radio buttons
        recframe = tk.Frame(self.nb)
        recframe.config(height=105, width=250)
        recframe.pack()
        self.nb.add(recframe, text='Record')
        self.Record = Record(recframe, self)
        # The hunter and the recorder share one UDP port: the TV icon
        # mirrors whichever stream is active, locked during hunts
        self.General.RecordHook = self.Record.HunterState
        # AFK recording: a finished hunt round flushes the recorder,
        # a starting one drops the reset footage in between
        self.General.RoundHook      = self.Record.RoundEnd
        self.General.RoundStartHook = self.Record.RoundStart
        # Connect waits for the recorder's shiny video to be written
        self.General.RecordBusyHook = self.Record.PendingVideo

        currset = (self.General.lockedslot or 1) - 1
        self.General.setting.set(self.General.settinglist[currset])
        self.data2GUI(currset)
        self.update_idletasks()
        self.minsize(max(480, self.winfo_reqwidth()), self.winfo_reqheight())

    ############################################################################
    ############################## Class Functions #############################
    ############################################################################

    def post_ui(self, callback):
        self.ui_queue.put(callback)

    def OpenDiagnostics(self):
        if self.Diagnostics is not None and self.Diagnostics.winfo_exists():
            self.Diagnostics.lift()
            return
        from rehearsal_gui import RehearsalWindow
        self.Diagnostics = RehearsalWindow(self)

    def call_ui(self, callback):
        if threading.current_thread() is threading.main_thread():
            return callback()
        done = threading.Event()
        result = []
        def invoke():
            try:
                result.append((True, callback()))
            except Exception as error:
                result.append((False, error))
            finally:
                done.set()
        self.post_ui(invoke)
        while not done.wait(.05):
            if self.closing:
                return None  # Tk teardown cancels queued view updates.
        ok, value = result[0]
        if not ok:
            raise value
        return value

    def ui_tick(self):
        if self.closing:
            return
        for _ in range(100):
            try:
                callback = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            callback()
        if hasattr(self, 'image'):
            for screen in (0, 1):
                image = self.image[screen]
                if image is not None and image is not self._drawn[screen]:
                    self.show_frame(screen)
                    self._drawn[screen] = image
        self.after(40, self.ui_tick)

    def on_closing(self):
        self.closing = True
        if self.Diagnostics is not None:
            self.Diagnostics.close()
        self.General.stop_event.set()
        self.Record.stop.set()
        self.ClosePopup()
        for owner in (self.General, self.Record):
            source = getattr(owner, 'video_source', None)
            if source is not None:
                source.close()
            for name in ('tcp_socket', 'udp_socket'):
                sock = getattr(owner, name, None)
                if sock is not None:
                    sock.close()
        if self.ir is not None and not self.General.dry_run:
            try:
                self.ir.clear_everything()
                self.ir.send(print_sent=False)
                self.ir.return_control()
            except OSError:
                pass
        if self.ir is not None:
            self.ir.socket.close()
        if self.General._settinglock is not None:
            self.General._settinglock.close()
        self.destroy()

    def Undock(self):
        # Toggle the undocked screen window
        if self.popup is None:
            self.OpenPopup()
        else:
            self.ClosePopup()

    def OpenPopup(self):
        # The docked previews step aside; the ScreenPopup owns the
        # display and reads pop_form / pop_scale straight off the app
        self.undockbtn.config(relief = 'sunken')
        self.undocked = True
        self.upperlabel.config(image = self.bitmap['Upper'])
        self.lowerlabel.config(image = self.bitmap['Lower'])
        self.popup = ScreenPopup(self)

    def ClosePopup(self):
        if self.popup is not None:
            self.popup.close()
            self.popup = None
        self.undocked = False
        self.undockbtn.config(relief = 'raised')

    def FollowPopup(self, event=None):
        # The main window moved: shift the popup by the same delta so
        # it keeps its relative distance, wherever the user put it.
        # Ignore Configure events bubbling up from child widgets
        if event is not None and event.widget is not self:
            return
        pos = (self.winfo_x(), self.winfo_y())
        if self._lastpos is None:
            self._lastpos = pos
            return
        dx = pos[0] - self._lastpos[0]
        dy = pos[1] - self._lastpos[1]
        self._lastpos = pos
        if self.popup is not None and (dx or dy):
            self.popup.follow(dx, dy)

    def SelScreens(self):
        # Ticked screens, low to high (0 lower, 1 upper)
        sel = []
        if int(self.lowerVal.get()) == 1:
            sel.append(0)
        if int(self.upperVal.get()) == 1:
            sel.append(1)
        return sel

    def screenSwitch(self):
        # Both screens may update at once; an unticked screen falls
        # back to its placeholder
        if int(self.upperVal.get()) == 0:
            self.upperlabel.config(image = self.bitmap['Upper'])
        if int(self.lowerVal.get()) == 0:
            self.lowerlabel.config(image = self.bitmap['Lower'])

    def background_thread(self):
        source = self.General.video_source
        store = self.General.frames
        stop = self.General.stop_event
        while not stop.is_set():
            try:
                frame = source.read()
                store.put(frame.screen, frame.image, frame.started, frame.completed)
                self.image[frame.screen] = frame.image
            except socket.timeout:
                continue
            except OSError as error:
                if not stop.is_set():
                    store.error = str(error)
                return

    def show_frame(self, s):
        # Update screen s (0 = lower, 1 = upper) when its checkbox is
        # on; an unticked screen keeps its placeholder. While
        # undocked the popup owns the display, so the docked previews
        # stay on their placeholders
        if self.undocked:
            return
        val   = (self.lowerVal,   self.upperVal)[s]
        label = (self.lowerlabel, self.upperlabel)[s]
        size  = ((96, 72), (120, 72))[s]
        name  = ('Lower', 'Upper')[s]
        if int(val.get()) == 1:
            img = ImageTk.PhotoImage(self.image[s].resize(size))
            label.config(image = img)
            label.image = img  # keep a reference, or Tk loses the image
        else:
            label.config(image = self.bitmap[name])

    def Connect3DS(self):
        if self.Diagnostics is not None and self.Diagnostics.busy:
            self.msgbox.MsgAppend('実機テストの受信を先に停止してください。')
            return
        if self._connecting:
            return
        if str(self.General.ConnectButton['relief']) != 'raised':
            self.General.stop_event.set()
            self.msgbox.MsgAppend('Stopping...')
            # Worker owns controller handover; prevent a new run until it exits.
            self.General.ConnectButton.config(state='disabled')
            return
        try:
            if not self.Record.stop.is_set():
                raise ValueError('Stop Record streaming first')
            if self.TIDm is not None and self.TIDm.is_alive():
                raise ValueError('Previous hunt is still stopping')
            local = endpoint(self.General.IPPC.Entry.get(), 8001)
            backend = self.General.backend.get()
            console = console_endpoint(self.General.IPDS.Entry.get(), backend)
            input_port = int(self.General.inputport.get())
            if not 1 <= input_port <= 65535:
                raise ValueError('Invalid InputRedirection port')
            count = int(self.General.Counter.Entry.get())
            if count < 1:
                raise ValueError('Counter must be positive')
            language = self.General.language.get()
            target = int(self.Recv.recvvar.get())
            mode = int(self.General.Tab.get())
            if language == 'Japanese' and (mode != 1 or target > 2):
                raise ValueError('Japanese supports only the three gift routes')
            dry_run = bool(self.General.dryvar.get())
            profile_path = self.General.profilevar.get() or None
            if backend == 'ChirunoMod' and (mode != 1 or target > 2):
                raise ValueError('ChirunoMod supports only the three gift routes')
            max_span = 2.0
            if mode == 1 and target <= 2:
                from gift_recognition import Profile, TARGETS
                profile = Profile(language, TARGETS[target], profile_path)
                max_span = profile.data['freshness'].get('max_span', 2.0)
                if not dry_run:
                    profile.require_ready(live=True, backend=backend)
            context = hardware_context(backend, console, input_port, max_span=max_span)
            if not dry_run:
                require_hardware(context)
            if not self.General.AcquireSlot():
                return
            self.General.serverIP, self.General.serverport = local
            self.General.clientIP = console[0]
            self.General.start_count = count
            self.General.dry_run = dry_run
            self.General.video_backend = backend
            self.General.hardware_context = context
            self.Recv.session_options = (language, target, dry_run, profile_path)
            self.General.frames = FrameStore()
            self.General.stop_event = threading.Event()
            self.General.ConnectState(1)
            self.GUI2data(self.General.settingGetInd())
            self.General.WriteSetting(self.General.data)
            self._connecting = True
            self.image[:] = [None, None]
            self.TID = threading.Thread(target=self.main_procedure,
                                        args=(local, console, mode, backend, max_span, input_port), daemon=True)
            self.TID.start()
        except Exception as error:
            self.msgbox.MsgAppend(f'SAFE STOP / 安全停止: {error}')

    def main_procedure(self, local, console, mode, backend, max_span, input_port):
        try:
            self.msgbox.MsgAppend(f'Connecting {backend} (no startup reset)...')
            source = open_video(backend, local, console, max_span=max_span)
            self.General.video_source = source
            self.General.tcp_socket, self.General.udp_socket = source.tcp, source.udp
            self.TIDb = threading.Thread(target=self.background_thread, daemon=True)
            self.TIDb.start()
            # InputRedirection protocol uses UDP 4950. Construction sends no packet.
            if self.ir is not None:
                self.ir.socket.close()
            self.ir = LumaInputServer(console[0], input_port)
            end = time.monotonic() + 30
            while self.image[0] is None or self.image[1] is None:
                if self.General.stop_event.wait(.1):
                    raise OSError('Cancelled')
                if time.monotonic() > end:
                    raise OSError('No complete stream from both screens')
            if self.General.stop_event.is_set():
                raise OSError('Cancelled')
            tab = (self.Battle, self.Recv, self.Lotto)[mode]
            tab.ir = self.ir
            self.TIDm = threading.Thread(target=tab.main_procedure, daemon=True)
            self.TIDm.start()
            self.post_ui(lambda: self.General.ConnectButton.config(state='normal'))
        except Exception as error:
            self.General.stop_event.set()
            self.msgbox.MsgAppend(f'SAFE STOP: {error}')
            if not self.closing:
                self.General.ConnectState(0)
                self.General.ConnectState(-1)
        finally:
            self._connecting = False

    def settingswitch(self, event=None):
        currset = self.General.settingGetInd()
        self.General.setting.selection_clear()
        self.General.data = self.General.LoadSetting()
        self.data2GUI(currset)

    def GUI2data(self,i):
        # Screen selection and undock popup options are main-window
        # settings, saved per Set
        self.General.data[i].upper = int(self.upperVal.get())
        self.General.data[i].lower = int(self.lowerVal.get())
        self.General.data[i].popform = self.pop_form
        self.General.data[i].pophalf = 1 if self.pop_scale == 0.5 else 0
        self.General.GUI2data(i)
        self.Battle.GUI2data(i)
        self.Recv.GUI2data(i)
        self.Lotto.GUI2data(i)
        self.Record.GUI2data(i)

    def data2GUI(self,i):
        self.upperVal.set(1 if self.General.data[i].upper else 0)
        self.lowerVal.set(1 if self.General.data[i].lower else 0)
        self.screenSwitch()   # refresh the placeholders for unticked
        # Restore the undock popup options; rebuild if it is open
        d = self.General.data[i]
        self.pop_form  = d.popform if d.popform in (0, 1, 2) else 0
        self.pop_scale = 0.5 if d.pophalf else 1.0
        if self.popup is not None:
            self.popup.rebuild()
        self.General.data2GUI(i)
        self.Battle.data2GUI(i)
        self.Recv.data2GUI(i)
        self.Lotto.data2GUI(i)
        self.Record.data2GUI(i)

if __name__ == '__main__':
    app = ShinyHunterUSUM()
    if '--hardware-test' in sys.argv[1:]:
        app.OpenDiagnostics()
    app.mainloop()
