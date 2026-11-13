# macOS Apple Silicon / 日本語版ギフト厳選（検証前プレビュー）

[u93132/ShinyHunterUSUM](https://github.com/u93132/ShinyHunterUSUM) のforkです。
改修元は `f49910affd7ed35b38af8e2b5b35499dcc554f0d`（v1.2.0）。
日本語版USUMの **ベベノム、タイプ：ヌル（ポニ／エーテル）** の受け取り厳選に対応する構造を追加しています。

**日本語版の実画像は未収集、3DS実機での映像・操作・色違い判定は未検証です。**
現在そのまま使えるのはネイティブGUI、受信・画像収集、校正／再判定と安全停止の仕組みです。
日本語テンプレートはプレースホルダで、実画像とルートごとの検証記録がないlive実行は拒否します。
完全自動厳選の実機動作確認済みリリースではありません。

## Macでのセットアップと起動

Apple Siliconのarm64ターミナルで実行します。Rosetta、Wine、Windowsは不要です。
Python標準ライブラリとTkinter、Pillowのみを使います。OpenCV／NumPyは追加していません。

```sh
brew install python@3.12 python-tk@3.12
git clone --branch macos-japanese-gifts https://github.com/senuhi/ShinyHunterUSUM.git
cd ShinyHunterUSUM
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m tkinter
.venv/bin/python USUMShinyHunter_GUI.py
```

Tkのテストウィンドウを閉じてから本体を起動します。
2回目からは `./run_macos.command`、またはFinderで同ファイルを開けます。
Pythonとpython-tkのバージョンを揃えてください。
Homebrew以外では、Tkを含む[python.orgのmacOS版](https://www.python.org/download/mac/tcltk/)も利用できます。
[Homebrew python-tk@3.12](https://formulae.brew.sh/formula/python-tk@3.12) が対応依存です。
署名済み `.app` の配布はこの改修に含みません。

設定は `~/Library/Application Support/ShinyHunterUSUM/`、認識画像とスコアは
`~/Pictures/ShinyHunterUSUM/` に保存します。作業ディレクトリによらず画像リソースを読み込みます。
`USUM_DATA_DIR` と `USUM_CAPTURE_DIR` 環境変数で保存先を変更できます。
設定スロットの排他はmacOSではfcntl、Windowsではmsvcrtを使います。

## 3DS側と通信の準備

1. Luma3DS導入済みの **New 3DS／New 2DS** と日本語版ウルトラサン／ウルトラムーンを用意します。
   旧3DSは対象外です。上流はLuma3DS v13以降を前提としています。
2. [NTR-HRの公式配布・説明](https://github.com/xzn/ntr-hr)に従って、New 3DS用のNTR-HRを導入し起動します。
   本ツールは上流と同じ従来形式のJPEG/UDPストリームを使用します。新しいHR独自のFEC/KCP形式を
   直接デコードする実装ではありません。従来互換ストリームが受信できる構成で使用してください。
3. L+下+SELECTでRosalinaを開き、Miscellaneous options → Start InputRedirectionを有効にし、
   3DSのIPを控えます。[Luma3DS Rosalina公式資料](https://github.com/LumaTeam/Luma3DS/wiki/Rosalina)も参照してください。
4. Macと3DSを同一LANに接続します。Macは有線LAN、3DSは同じルーターのWi-Fiを推奨します。
   APのクライアント分離を無効にし、macOSでローカルネットワーク／受信通信の許可が出たら許可します。
5. GUIの **PC IP** にMacの実際のLAN IPv4と受信ポート（例 `192.168.1.10:8001`）、
   **3DS IP** に3DSのIPv4（例 `192.168.1.50`）を入力します。初期の127.0.0.1は実機には使えません。
   MacのWi-Fiアドレスは `ipconfig getifaddr en0` 等で確認できます。インターフェイス名は環境により異なります。
6. ゲームの文字速度を「はやい」にし、対象を受け取る直前で保存します。手持ちに空きを作り、
   同種の別個体を入れず、メニューは最初に「ポケモン」を開ける状態にします。

Mac→3DSはNTR設定用TCP 8000、操作用UDP 4950、3DS→Macは映像用UDP 8001（変更可能）です。
3DS IPには任意のNTR TCPポートも `IP:port` で指定できます。InputRedirectionの4950はLuma標準です。
通信ライブラリの `LumaInputServer(host, port=4950)` はカスタムポートも尊重します。
NTRへ接続する前に受信UDPをbindし、指定したMacのローカルIPからTCP接続します。
NTRの映像ポートを変更した場合は3DSを再起動してください。他のNTRビューアとは同時に接続しません。

## 画像校正と安全な使い方

`Game Language` はJapanese／Englishを切り替えます。日本語版ではRecvの3ルートだけを選択できます。
**dry-runは起動・設定スロット変更・言語変更のたびにONへ戻ります。**
検証前はこれを維持してください。受信と認識だけを行い、ボタン入力もリセットも送信しません。

日本語版の必須素材、座標・色しきい値の調整、PNG収集、オフライン再判定、
検証記録の作成は [日本語版の校正手順](docs/CALIBRATION_JA.md) にまとめています。
英語版の3ギフトも同じ安全制御を使い、上流テンプレートを流用しますが、save_file画像と実機検証が必要です。
日本語・英語の保存先は `templates/ja/Recv` と `templates/en/Recv`、設定は `profiles/ja.json` と `profiles/en.json` です。
カスタムJSONはGUIの **Profile JSON** にパスを指定できます（空欄なら標準プロファイル）。

- ギフト厳選は受け取り直前から開始し、初回の無条件リセットを行いません。
- 通常色／色違い／unknownを分け、対象名と新しい複数フレームの判定一致を要求します。
- 判定不明、低信頼度、認識タイムアウト、画像停止、通信異常では安全停止します。
- 通常色判定が有効な間だけ最終再確認をし、1回限りのリセットを許可します。
- 認識画像・対象名のスコア・色距離・判定・停止理由をPNG／JSONLへ保存します。スコアは確率ではありません。
- ギフトのBoostは無効です。自動保存はせず、色違い候補で停止して目視確認と手動保存を待ちます。

英語版のBattle／Lotto／その他Recv／Recordの実装と元画像は残しています。
新しい日本語対応と安全なギフト判定の対象は上記3ルートです。既存英語機能の実機回帰は未実施です。
Recordは言語によらず受信できます。旧機能も既定dry-runでは自動操作を始めません。

## 開発者向け検証

```sh
.venv/bin/python -m unittest discover -s tests -v
# GUIセッションがあるMacでだけ実行（模擬3DS映像を使います）
.venv/bin/python tests/gui_smoke.py
```

[変更計画と事前調査](docs/IMPLEMENTATION_PLAN.md)、[検証結果と制限](docs/VALIDATION.md) を参照してください。
CIはmacOS／Windows／Linuxのオフラインテストを定義しています。CIの成功は実機動作を保証しません。

---

以下は上流の英語READMEです。Windows版や元の英語版機能の説明であり、
このforkの日本語対応の検証状態は上記を優先してください。

# Shiny Hunter USUM (AFK)

A Windows program that does the shiny hunting on Pokémon Ultra Sun / Ultra Moon
for you. It watches the 3DS screens through NTR-HR streaming, presses the
buttons through input redirection, soft-resets the game round after round, and
stops — with a screenshot and optionally a video — when the shiny shows up.

Thanks to xzn (zbash92 on GBAtemp) for NTR-HR and its greatly improved
streaming stability, to TuxSH for Luma3DS, and to hlixed's TPPFLUSH for the
input redirection, this AFK procedure is possible and, since 2026, a lot more
stable than it was.

- Discussion and walkthrough videos: https://gbatemp.net/threads/shiny-hunter-usum-afk.648378
- Source code: https://github.com/u93132/ShinyHunterUSUM

## Demo

One hunt round captured by the Record tab's AFK mode, framed in the New 3DS XL
console picture (This is compressed to GIF for the purpose of demo and not to
flood your browser. You can have high quality recording using this app):
[Original quality of this recording](https://github.com/u93132/ShinyHunterUSUM/blob/main/demo/AFK_1_1725.png)

![AFK recording demo](demo/demo_afk.gif)

Also a real-time recording of an early version of ShinyHunterUSUM working with
the N3DS — a shiny Lugia:
![Watch the real-time recording](demo/Shiny_Lugia_realtime.gif)

## Features

1. Shiny hunting during battles
2. Shiny hunting when receiving Pokémon (Poipole, Type: Null, the starters, Pikachu in a hat)
3. Roto Loto
4. Settings are auto-saved when the PC and 3DS connect; 12 saving slots (Sets)
5. Auto screenshot when a shiny appears
6. Real-time streaming, plus a Record page for screenshots, bursts and videos — including one video per hunt round

Only the English version of the games is supported. The game version is
detected automatically on the first reset:

| Hunt | US/UM | S/M |
|------|:-----:|:---:|
| Battle | all four trigger / type combinations | Move + no aura only |
| Recv | every target | Type: Null (Aether) and the starters |
| Lotto | ✓ | – |

## Limitations

1. English-version gameplay only.
2. This is a real-time streaming / control loop: the latency between PC and 3DS has to be small.
3. Only New 3DS / New 2DS are supported.

## What you need

1. A hacked New 3DS / New 2DS on the latest firmware (11.17) with Luma3DS v13.0 or above.
2. Homebrew **NTR-HR**: https://gbatemp.net/threads/rel-improved-hopefully-ntr-streamer-for-n3ds-xl-ll.644726/
   - Old NTR versions work but do not support multiple instances and crash the 3DS often.
   - A static IP on the 3DS is better, but optional.
3. A network the PC and the 3DS share. Most stable first:
   1. PC wired to the Wi-Fi router, 3DS on the router's Wi-Fi.
   2. PC, 3DS and router all wireless.
   3. A hosted network (mobile hotspot) from the PC's WLAN card — the defaults `192.168.137.1` / `192.168.137.50` assume this.
4. A Pokémon Ultra Sun / Ultra Moon cartridge.
5. The packed `USUMShinyHunter.exe` from Releases, or Python 3.10+ to run from source.

Setting the 3DS clock rate to 268 MHz makes crashes rarer.

## Setup

**PC side**

1. Put the PC and the 3DS on the same network (see above). If Windows asks, make the network **Private** — on a Public network the firewall silently drops the inbound stream.
2. Find your PC IP address.

**3DS side**

1. Install the latest NTR-HR.
2. Press **L + Down + Select** for the Luma menu, then *Miscellaneous options → Start InputRedirection*.
3. Write down the 3DS IP address.
4. Open bootNTR and load NTR 3.6-HR. If you replaced an older NTR, long-press Select when opening it.
5. You are back on the home menu: start Ultra Sun / Ultra Moon.
6. Set the in-game text speed to **fast**.

## How to use

1. Enter your PC IP with the port number (`8001` is NTR's default) in **PC IP**.
2. Enter the 3DS IP in **3DS IP**.
3. Set the counter.
4. Pick a hunt on the Tab radio buttons and configure it on its page (see *Detail settings*).
5. Click the 3DS icon ![](image0/General/connect.gif). The log walks through the five steps — TCP link, stream setup, UDP listener, input redirection, hunt — and the window turns **yellow** (Battle), **cyan** (Recv) or **lime** (Lotto) when the hunt is done, **red** if the connection is lost.
6. Click the 3DS icon again to disconnect whenever you want to pause.

- Note 1: the physical buttons of the 3DS are locked during the hunt.
- Note 2: the 3DS icon stays locked for a few seconds after each click while it finishes its work. Please be patient.
- Note 3: NTR fixes its streaming port the first time it initializes. If you change the port in the app, reboot the 3DS.

## Multi-instance

One PC can drive several 3DS. Start the program once per console: each instance locks the first free Set (#1, #2, …) at start-up and on connect, so two instances can never write the same settings or counter. Give each its own stream port:

```
Hunter 1                         Hunter 2
PC IP:  192.168.137.1:8001       PC IP:  192.168.137.1:8002
3DS IP: 192.168.137.50           3DS IP: 192.168.137.60
```

Every saved file carries the instance's Set number (`Encounter_1_0042.jpg`, `Upper_2_0001.jpg`), so instances can share one folder.

## Detail settings

### Battle

Two triggers and two Pokémon types give four kinds of hunt:

| Trigger | Type | Pokémon |
|---------|------|---------|
| Move | no aura | Legendaries in Ultra Wormholes, normal grass encounters |
| Move | with aura | Stakataka, Blacephalon |
| Talk | no aura | (no Pokémon belongs here) |
| Talk | with aura | Ultra Beasts in Ultra Wormholes |

Save right beside (as close as possible to) the event trigger point, or in the middle of the grass.

### Receiving Pokémon

| Target | Where to save | US/UM | S/M |
|--------|---------------|:-----:|:---:|
| **Poipole** | in front of the NPC that gives you Poipole | ✓ | – |
| **Type: Null (Poni)** | on the left of the event trigger point | ✓ | – |
| **Type: Null (Aether)** | in front of the NPC | ✓ | ✓ |
| **Rowlet / Litten / Popplio** | in front of the grass where the event triggers | ✓ | ✓ |
| **Pikachu** | in front of the NPC | ✓ | – |

**Boost** reads the shiny colour straight from the cutscene for Poipole, Type: Null and the starters instead of opening the summary page: much faster per round. Both Type: Null routes share the same check, and it is calibrated on US/UM and S/M footage alike.

### Roto Loto

1. Save away from the NPC so the A presses are not swallowed by conversations.
2. Tick the Roto prizes you want; multi-select is allowed. The hunt stops at the first prize you ticked.

### Record

The Record page captures the stream — during a hunt, or on its own.

1. When the AFK hunt is running the stream is ready to be recorded; the TV icon ![](image0/Record/TVon.gif) mirrors it.
2. Without a hunt, click the TV icon ![](image0/Record/TVoff.gif) to start the Record page's own stream.
3. Buttons, left to right (each click cycles to the next icon):
   - **Shot form** — ![](image0/Record/image.gif) picture only → ![](image0/Record/redconsole.gif) red console → ![](image0/Record/blueconsole.gif) blue console. The console forms paste the ticked screens into an N3DS XL picture at native resolution (the other screen blacked out) and save as PNG.
   - **Capture mode** — ![](image0/Record/camera.gif) one shot → ![](image0/Record/auto.gif) burst → ![](image0/Record/video.gif) video (60 s max) → ![](image0/Record/afk.gif) AFK.
   - **Format** (video modes) — ![](image0/Record/aviicon.gif) AVI (MJPEG, the stream's own quality) → ![](image0/Record/gificon.gif) GIF → ![](image0/Record/apngicon.gif) APNG.
   - **Run** ![](image0/Record/run.png) — fires the capture; for burst, video and AFK it starts and stops. It pops up when the capture ends and stays greyed out until the file is written.
   - **Only shiny run** (AFK) — keep just the round that found the shiny (default), or every round.
4. The **Screen** checkboxes on the main window choose which screens go in; both ticked gives one combined picture.
5. **AFK mode** records one video per hunt round, from the save-data screen to the shiny check (the newest 200 s of a round are kept, so a frozen game cannot fill memory). When the shiny shows up the hunt lingers a few seconds so the video carries the animation, then the recorder disarms together with the hunt. Arm it before connecting or in the middle of a hunt — recording then starts with the next round.

Files go to the *Save to* folder: `Upper_1_0001.jpg`, `Combined_1_0001.jpg`, `N3DSRed_1_0001.png`, `Video_1_0001.avi`, `AFK_1_0042.avi`… AFK videos carry the round number, matching the hunter's `Encounter_1_0042.jpg` / `Recv_1_0042.jpg`.

The Record page's folder, shot form, capture mode, format and *Only shiny run* are saved per Set like every other setting.

### Undock — a floating Screen window

The ![](image0/undock.gif) button at the bottom-right of the **Screen** box pops the live screens out into a separate window that follows the main window. It is meant for streaming: give your capture software a clean, fixed-size view of the game instead of the whole app.

- A toolbar across the top: ![](image0/Record/image.gif) plain / ![](image0/Record/redconsole.gif) red console / ![](image0/Record/blueconsole.gif) blue console background, then ![](image0/oneicon.gif) full and ![](image0/halficon.gif) half size.
- The console backgrounds frame the screens inside an N3DS XL picture; the **Screen** checkboxes choose which screens show (tick one for one screen, both for both).
- The window is titled **Screen** so Discord/OBS *window* capture can find it. Its title-bar controls are disabled — it can only be opened and closed with the undock button, and it keeps a fixed size and follows the main window so it never drifts off your scene.
- The background and size choices are saved per Set.

While the window is open the docked previews step aside; press the undock button again to close it and bring them back.

## Troubleshooting

- **No stream from 3DS** — the network profile on Windows must be *Private*; check the PC IP and port; reboot the 3DS if you changed the port (see Note 3).
- **Error NNN in the log** — the hundreds digit is the stage: `101` the target's name never appeared; `2xx` walking the dialogue; `3xx` starter selection; `5xx` summary page; `6xx` Boost cutscene check. A `Debug_*` screenshot of that moment is saved next to the exe.
- **Red window, "N3DS crush?" / "3DS connection lost"** — the console stopped answering; the app has unlocked itself, check the 3DS and reconnect.
- **"Setting #N locked by another instance"** — that Set belongs to a running instance; pick another one.
- **Discord/OBS cannot find the undock window** — use *window* capture and pick the window named **Screen**; if it still will not list, capture the whole monitor instead.

## Running from source / building the exe

```bash
py -3 -m pip install -r requirements.txt
py -3 USUMShinyHunter_GUI.py
```

`make.bat` packs the single-file exe with PyInstaller (Python 3.10+ required).

## Updates

- v0.3.4: fixed receiving Type: Null.
- v0.3.5: full IP address support.
- v0.4.0: starter Pokémon added — save in front of the grass where the event triggers.
- v1.0.0: recording functions, Pikachu in a hat, Sun / Moon officially supported.
- v1.1.0: Record page capture modes (burst, 60 s video, one video per AFK round with *Only shiny run*), AVI / GIF / APNG output, red and blue console shot forms, per-Set Record settings, Set-numbered filenames for multi-instance, and the hunt lingers after a shiny so the video keeps the animation.
- v1.2.0: Floating Screen window & S/M starters

**2026 edit.** Most of the potential bugs are cleaned up and template matching is faster. Features that depended on low latency were removed. Thanks to AI, programming is much faster now — whether that is a good sign or not.

## Acknowledgements

- [NTR-HR](https://github.com/xzn/ntr-hr/tree/ntr_bins) by xzn (zbash92 on GBAtemp) — screen streaming
- [TPPFLUSH](https://github.com/hlixed/TPPFLUSH) by hlixed — input redirection
- [Luma3DS](https://github.com/LumaTeam/Luma3DS) by TuxSH — custom firmware

## License

See [LICENSE](LICENSE).
