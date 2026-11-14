"""Native Tk delivery-test window; all game input is opt-in and bounded."""
import json
import queue
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import ImageTk
from ntr_transport import endpoint
from rehearsal import Rehearsal, BUTTONS, DEFAULT_BOXES
from video_stream import console_endpoint


class RehearsalWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app; self.engine = None; self.events = queue.Queue(); self.closed = False
        self.title('実機テスト · 受取と情報画面判定')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.columnconfigure(0, weight=1)
        self.photos = {}; self.drawn = {}; self.drag_start = {}; self.rectangles = {}
        self.boxes = {s: list(b) for s, b in DEFAULT_BOXES.items()}
        self.backend = tk.StringVar(value=app.General.backend.get())
        self.local = tk.StringVar(value=app.General.IPPC.Entry.get())
        self.console = tk.StringVar(value=app.General.IPDS.Entry.get())
        self.input_port = tk.StringVar(value=app.General.inputport.get())
        self.passive = tk.BooleanVar(value=True); self.saved = tk.BooleanVar(value=False)
        self.party_before=tk.IntVar(value=4);self.stop_at_summary=tk.BooleanVar(value=True)
        self.received = tk.BooleanVar(value=False); self.cycles = tk.IntVar(value=1)
        self.button = tk.StringVar(value='A'); self.status_text = tk.StringVar(value='未接続。受信開始はボタン入力を送りません。')
        self.stats = tk.StringVar(value='上 0枚 / 下 0枚 · 入力 0 · リセット 0')
        self.scores = tk.StringVar(value='照合スコア: 未測定（一致は0に近い値）')
        self.log_path = tk.StringVar(value='記録先は受信開始後に表示します。')
        body = ttk.Frame(self, padding=10); body.grid(sticky='nsew'); body.columnconfigure(0, weight=1)
        ttk.Label(body, text='日本語ピカチュウ · 固定手順で受取とリセットを試験', font=('', 14, 'bold')).grid(row=0, sticky='w')
        ttk.Label(body, text='開始は「受取前に保存した受取員の前・会話なし」のみ。手持ちに空きを1つ以上確保。\n受信開始 → 接続確認（送信0）→ 受取と情報画面テスト。受取後は保存しません。').grid(row=1, sticky='w', pady=(4, 8))

        connection = ttk.Frame(body); connection.grid(row=2, sticky='ew')
        self.settings = []
        for col, (label, variable, width) in enumerate((('Mac IP', self.local, 18), ('3DS IP', self.console, 18), ('入力ポート', self.input_port, 7))):
            ttk.Label(connection, text=label).grid(row=0, column=col, sticky='w')
            entry=ttk.Entry(connection, textvariable=variable, width=width); entry.grid(row=1, column=col, padx=(0, 8)); self.settings.append(entry)
        self.backend_box=ttk.Combobox(connection, textvariable=self.backend, values=('ChirunoMod','NTR-HR'), state='readonly', width=12)
        self.backend_box.grid(row=1, column=3, padx=(0, 8))
        self.connect_button=ttk.Button(connection, text='受信開始（操作なし）', command=self.connect)
        self.connect_button.grid(row=1, column=4)
        ttk.Button(connection, text='停止', command=self.stop).grid(row=1, column=5, padx=(8,0))

        previews=ttk.Frame(body); previews.grid(row=3, sticky='w', pady=8)
        self.canvases={}; self.enabled={}; self.box_labels={}
        for col, (screen, width, label) in enumerate(((1,400,'上画面'),(0,320,'下画面'))):
            frame=ttk.Frame(previews); frame.grid(row=0,column=col,sticky='nw',padx=(0,8))
            canvas=tk.Canvas(frame,width=int(width*.75),height=180,background='#202020',highlightthickness=1)
            canvas.grid(row=0,column=0,columnspan=2); self.canvases[screen]=canvas
            self.enabled[screen]=tk.BooleanVar(value=True)
            ttk.Checkbutton(frame,text=label+'を照合',variable=self.enabled[screen]).grid(row=1,column=0,sticky='w')
            text=tk.StringVar(value='全画面');self.box_labels[screen]=text
            ttk.Label(frame,textvariable=text).grid(row=1,column=1,sticky='e')
            canvas.bind('<ButtonPress-1>',lambda event,s=screen:self.begin_region(s,event))
            canvas.bind('<B1-Motion>',lambda event,s=screen:self.drag_region(s,event))
            canvas.bind('<ButtonRelease-1>',lambda event,s=screen:self.end_region(s,event))
        help_row=ttk.Frame(body);help_row.grid(row=4,sticky='ew')
        self.help_text=tk.StringVar()
        ttk.Label(help_row,textvariable=self.help_text).pack(side='left')
        self.reset_roi_button=ttk.Button(help_row,text='範囲を全画面に戻す',command=self.reset_regions)
        self.advanced=tk.BooleanVar(value=False)
        ttk.Checkbutton(help_row,text='詳細（手動記録）',variable=self.advanced,command=self.toggle_advanced).pack(side='right',padx=8)

        record=ttk.LabelFrame(body,text='1. 手動操作の1周を記録',padding=6);record.grid(row=5,sticky='ew',pady=6)
        ttk.Combobox(record,textvariable=self.button,values=BUTTONS,state='readonly',width=12).grid(row=0,column=0)
        self.record_button=ttk.Button(record,text='この画面と次の操作を記録',command=self.record)
        self.record_button.grid(row=0,column=1,padx=6)
        ttk.Button(record,text='最後の操作を削除',command=self.undo).grid(row=0,column=2)
        ttk.Checkbutton(record,text='受取済み画面を確認した（RESETの記録に必要）',variable=self.received).grid(row=1,column=0,columnspan=3,sticky='w',pady=4)
        self.finish_button=ttk.Button(record,text='開始位置へ復帰したので記録完了',command=self.finish_recording)
        self.finish_button.grid(row=0,column=3,padx=6)
        self.steps=tk.Listbox(record,height=3,exportselection=False);self.steps.grid(row=2,column=0,columnspan=4,sticky='ew')
        record.columnconfigure(3,weight=1)

        play=ttk.LabelFrame(body,text='2. 記録した手順を試験',padding=6);play.grid(row=6,sticky='ew')
        ttk.Checkbutton(play,text='照合のみ（3DSの操作は自分で行う）',variable=self.passive).grid(row=0,column=0,columnspan=3,sticky='w')
        ttk.Checkbutton(play,text='受取前のレポートを保存済み',variable=self.saved).grid(row=1,column=0,columnspan=3,sticky='w')
        ttk.Label(play,text='周回数').grid(row=0,column=3)
        ttk.Spinbox(play,from_=1,to=3,textvariable=self.cycles,width=3).grid(row=0,column=4)
        self.play_button=ttk.Button(play,text='試験を開始',command=self.play);self.play_button.grid(row=0,column=5,padx=6)
        self.next_button=ttk.Button(play,text='手動操作済み · 次へ',command=self.manual_next,state='disabled')
        self.next_button.grid(row=1,column=5,padx=6)
        ttk.Button(play,text='記録を読み込む',command=self.load).grid(row=1,column=3,columnspan=2)
        self.record_frame=record;self.play_frame=play
        self.auto_frame=ttk.LabelFrame(body,text='開始位置を固定した1周テスト',padding=8)
        ttk.Label(self.auto_frame,text='受取 → 会話をBで終了 → X → ポケモン → 受取個体 → つよさをみる → 星の色を判定\n通常色でリセットを許可した場合だけ、リセット1回 → START → 続行 → 元の場所へ。約1〜2分。').grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,6))
        self.saved_check=ttk.Checkbutton(self.auto_frame,text='受取員の前・会話なしで保存済み／メニューはポケモン・手持ちは先頭を選択',variable=self.saved)
        self.saved_check.grid(row=1,column=0,columnspan=3,sticky='w')
        options=ttk.Frame(self.auto_frame);options.grid(row=2,column=0,columnspan=3,sticky='w',pady=4)
        ttk.Label(options,text='受取前の手持ち数').pack(side='left')
        self.party_box=ttk.Spinbox(options,from_=1,to=5,textvariable=self.party_before,width=3)
        self.party_box.pack(side='left',padx=6)
        ttk.Checkbutton(options,text='情報画面で停止（リセットしない・初期設定）',variable=self.stop_at_summary).pack(side='left',padx=8)
        self.auto_check_button=ttk.Button(self.auto_frame,text='1. 接続確認（送信0）',command=lambda:self.fixed(False))
        self.auto_check_button.grid(row=3,column=0,pady=8,sticky='w')
        self.auto_live_button=ttk.Button(self.auto_frame,text='2. 受取→情報画面テスト',command=lambda:self.fixed(True))
        self.auto_live_button.grid(row=3,column=1,padx=8,pady=8,sticky='w')
        ttk.Label(self.auto_frame,text='色設定は上流の参照値で日本語実機では未校正です。最初は情報画面で結果を確認してください。').grid(row=4,column=0,columnspan=3,sticky='w')
        self.toggle_advanced()
        ttk.Label(body,text='色違い候補・判定不能・通信／映像異常ではリセットしません。ゲーム内セーブは行いません。').grid(row=7,sticky='w',pady=(6,0))
        ttk.Label(body,textvariable=self.status_text,wraplength=740).grid(row=8,sticky='w',pady=4)
        ttk.Label(body,textvariable=self.stats).grid(row=9,sticky='w')
        ttk.Label(body,textvariable=self.scores).grid(row=10,sticky='w')
        footer=ttk.Frame(body);footer.grid(row=11,sticky='ew',pady=(4,0))
        ttk.Button(footer,text='記録フォルダを開く',command=self.open_folder).pack(side='left')
        ttk.Label(footer,textvariable=self.log_path,wraplength=570).pack(side='left',padx=8)
        self.update_idletasks();self.minsize(self.winfo_reqwidth(),self.winfo_reqheight())
        self.after(100,self.tick)

    @property
    def busy(self): return self.engine is not None and self.engine.busy

    def attempt(self, action):
        try: return action()
        except Exception as error: self.status_text.set('操作しません: '+str(error));return None

    def require_engine(self):
        if self.engine is None or self.engine.stop.is_set(): raise ValueError('先に受信開始してください。')
        return self.engine

    def connect(self):
        def action():
            if self.busy: raise ValueError('すでに接続中です。停止してから再接続してください。')
            if not self.app.General.stop_event.is_set() or not self.app.Record.stop.is_set() or self.app._connecting:
                raise ValueError('メイン画面の厳選・Record接続を先に停止してください。')
            if any(worker is not None and worker.is_alive() for worker in
                   (self.app.TIDm, self.app.Record.TID, getattr(self.app.Record,'TIDb',None))):
                raise ValueError('先の処理が停止するまで待ってください。')
            port=int(self.input_port.get())
            if not 1<=port<=65535:raise ValueError('入力ポートが不正です。')
            self.engine=Rehearsal(self.backend.get(),endpoint(self.local.get(),8001),
                console_endpoint(self.console.get(),self.backend.get()),port,self.app.General.shotpath,
                lambda kind,value:self.events.put((kind,value)))
            general=self.app.General
            for entry,value in ((general.IPPC.Entry,self.local.get()),(general.IPDS.Entry,self.console.get())):
                entry.delete(0,'end');entry.insert(0,value)
            general.backend.set(self.backend.get());general.inputport.set(str(port))
            general.GUI2data(general.settingGetInd());general.WriteSetting(general.data)
            self.engine.connect();self.drawn.clear();self.steps.delete(0,'end')
            self.log_path.set(str(self.engine.directory));self.received.set(False)
        self.attempt(action)

    def selected_boxes(self):
        boxes={str(s):list(self.boxes[s]) for s in (0,1) if self.enabled[s].get()}
        if not boxes:raise ValueError('上画面か下画面の照合を有効にしてください。')
        return boxes

    def refresh_steps(self):
        self.steps.delete(0,'end')
        for i,step in enumerate(self.engine.trace['steps'],1):
            self.steps.insert('end',f'{i:02d}  {step["button"]}   '+('受取済み確認地点' if step['button']=='RESET' else ''))
        self.steps.see('end')

    def record(self):
        def action():
            engine=self.require_engine()
            engine.record(self.button.get(),self.selected_boxes(),self.received.get())
            self.received.set(False);self.refresh_steps()
        self.attempt(action)

    def undo(self):
        def action():
            engine=self.require_engine()
            if engine.playing:raise ValueError('再生中は編集できません。')
            if engine.trace['steps']:
                engine.trace['steps'].pop();engine.trace.pop('finish',None)
                engine.passive_verified=False;engine.save_draft()
            self.refresh_steps()
        self.attempt(action)

    def finish_recording(self):
        def action():
            path=self.require_engine().finish_recording(self.selected_boxes());self.log_path.set(str(path))
        self.attempt(action)

    def load(self):
        def action():
            engine=self.require_engine()
            path=filedialog.askopenfilename(parent=self,title='受取テストのtrace.json',filetypes=[('JSON','*.json')])
            if path:engine.load(path);self.refresh_steps()
        self.attempt(action)

    def play(self):
        def action():
            engine=self.require_engine();cycles=int(self.cycles.get());live=not self.passive.get()
            if not 1<=cycles<=3:raise ValueError('試験は1〜3周です。')
            if live and not self.saved.get():raise ValueError('受取前に手動セーブし、保存済みにチェックしてください。')
            approved=False
            if live:
                sequence=' → '.join(s['button'] for s in engine.trace['steps'])
                approved=messagebox.askyesno('今回の実機テストを開始',
                    f'{cycles}周だけ操作します。リセットは最大{cycles}回です。\n\n{sequence}\n\n色違い判定・ゲーム内セーブは行いません。未知の画面では停止します。\n実行してよいですか？',parent=self)
                if not approved:return
            engine.play(cycles,live,self.saved.get(),approved)
        self.attempt(action)

    def toggle_advanced(self):
        if self.advanced.get():
            self.help_text.set('ドラッグで照合する文字・アイコンの範囲を指定できます。')
            self.reset_roi_button.pack(side='right')
            self.auto_frame.grid_remove();self.record_frame.grid();self.play_frame.grid()
        else:
            self.help_text.set('毎回、受取前に保存した受取員の前から開始します。手動記録は不要です。')
            self.reset_roi_button.pack_forget()
            self.record_frame.grid_remove();self.play_frame.grid_remove()
            self.auto_frame.grid(row=5,sticky='ew',pady=6)

    def fixed(self, live):
        def action():
            engine=self.require_engine()
            if live and not self.saved.get():raise ValueError('受取前セーブ・配達員の前・手持ちの空きを確認してください。')
            from fixed_delivery import FixedDelivery
            from summary_check import summary_buttons
            party=self.party_before.get();summary_buttons(party)
            stop_at_summary=self.stop_at_summary.get()
            runner=FixedDelivery(engine)
            if live and not engine.report.get('fixed_preflight_verified'):
                raise ValueError('受取員の前で「1. 接続確認（送信0）」を行ってください。')
            approved=False
            if live:
                budget=3+len(summary_buttons(party))+(0 if stop_at_summary else 3)
                text=f'受取員の前（会話なし）から、Aを3秒間隔で3回送ります。\nB×10→X→ポケモン→{party+1}番目→つよさをみる、の固定手順です。\nメニューはポケモン・手持ちカーソルは先頭の状態で保存してください。\n'
                text+=('情報画面で判定して停止し、リセットしません。' if stop_at_summary else '通常色の3フレーム一致と送信直前の再判定を確認した場合だけ、\nリセット1回→25秒→START→5秒→A→12秒→復帰確認。')
                text+=f'\n\n最大{budget}操作。途中の会話・メニュー・タイトルは画像判定しません。'
                approved=messagebox.askyesno('情報画面まで実行（リセットなし）' if stop_at_summary else '通常色だけリセットして1周を実行',
                    text+'\n\n日本語の色座標・色参照値は実機未校正です。セーブは行いません。\n色違い候補・判定不能・映像停止・通信断ではリセットしません。\n\n今回の試験を実行しますか？',parent=self)
                if not approved:return
            runner.start(saved=self.saved.get(),approved=approved,live=live,party_before=party,stop_at_summary=stop_at_summary)
        self.attempt(action)

    def manual_next(self):
        if self.engine is not None:self.engine.manual_next.set();self.next_button.config(state='disabled')

    def stop(self):
        if self.engine is not None:self.engine.disconnect()

    def begin_region(self,screen,event):
        self.drag_start[screen]=(max(0,int(event.x/.75)),max(0,int(event.y/.75)))

    def drag_region(self,screen,event):
        if screen not in self.drag_start:return
        self.canvases[screen].delete('roi')
        x,y=self.drag_start[screen]
        self.canvases[screen].create_rectangle(x*.75,y*.75,event.x,event.y,outline='#ffcc00',width=2,tags='roi')

    def end_region(self,screen,event):
        if screen not in self.drag_start:return
        x,y=self.drag_start.pop(screen);w=DEFAULT_BOXES[screen][2]
        x2,y2=max(0,min(w,int(event.x/.75))),max(0,min(240,int(event.y/.75)))
        box=[min(x,x2),min(y,y2),max(x,x2),max(y,y2)]
        if box[2]-box[0]<8 or box[3]-box[1]<8:self.reset_regions();return
        self.boxes[screen]=box;self.box_labels[screen].set(','.join(map(str,box)))

    def reset_regions(self):
        for s,b in DEFAULT_BOXES.items():
            self.boxes[s]=list(b);self.box_labels[s].set('全画面');self.canvases[s].delete('roi')

    def tick(self):
        if self.closed:return
        for _ in range(100):
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='status':self.status_text.set(value)
            elif kind=='scores':self.scores.set('照合スコア: '+' / '.join(('下' if k=='0' else '上')+f' {v:.4f}' for k,v in value.items())+'（上限0.035）')
            elif kind=='manual_ready':self.next_button.config(state='normal' if value else 'disabled')
            elif kind=='ocr':self.scores.set('読取: '+value[:120])
            elif kind=='summary':
                names={'normal':'通常色候補','shiny':'色違い候補','unknown':'判定不能'}
                self.scores.set(f'情報画面: {names[value["verdict"]]} · 通常距離 {value["normal_distance"]:.3f} / 色違い距離 {value["shiny_distance"]:.3f} · 目印 {len(value["context"])}個')
        if self.engine is not None:
            with self.engine.lock:latest=dict(self.engine.latest);counts=dict(self.engine.counts)
            for s,image in latest.items():
                if image is self.drawn.get(s):continue
                self.photos[s]=ImageTk.PhotoImage(image.resize((int(image.width*.75),180)),master=self)
                self.canvases[s].delete('video');self.canvases[s].create_image(0,0,image=self.photos[s],anchor='nw',tags='video')
                self.canvases[s].tag_lower('video');self.drawn[s]=image
            report=self.engine.report
            self.stats.set(f'上 {counts[1]}枚 / 下 {counts[0]}枚 · 入力 {report["controller_packets"]}パケット · リセット {report["reset_attempts"]}回 · 情報画面 {report.get("summary_verdict","未判定")} · 完了 {report["completed_cycles"]}周')
            state='disabled' if self.engine.playing else 'normal'
            for widget in (self.record_button,self.finish_button,self.play_button,self.auto_check_button,self.auto_live_button):widget.config(state=state)
            for widget in self.settings:widget.config(state='disabled' if self.busy else 'normal')
            self.backend_box.config(state='disabled' if self.busy else 'readonly')
        self.after(100,self.tick)

    def open_folder(self):
        if self.engine is None:return
        path=str(self.engine.directory)
        if sys.platform=='darwin':subprocess.Popen(['open',path])
        elif sys.platform=='win32':
            import os
            os.startfile(path)
        else:subprocess.Popen(['xdg-open',path])

    def close(self):
        if self.closed:return
        self.closed=True
        if self.engine is not None:
            self.engine.disconnect()
            for worker in (self.engine.player,self.engine.reader):
                if worker is not None:worker.join(timeout=.5)
        self.destroy()
