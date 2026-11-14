# macOS Apple Silicon / 日本語版ギフト厳選（検証前プレビュー）

[u93132/ShinyHunterUSUM](https://github.com/u93132/ShinyHunterUSUM) のforkです。
改修元は `f49910affd7ed35b38af8e2b5b35499dcc554f0d`（v1.2.0）。
日本語版USUMの **ベベノム、タイプ：ヌル（ポニ／エーテル）** の受け取り厳選に対応する構造を追加しています。

**旧3DSのUSUMで映像・基本入力・1回のソフトリセット復帰を確認しました。色違い判定は未検証です。**
日本語の受け取り認識テンプレートは未収集です。
現在そのまま使えるのはネイティブGUI、自前の映像受信・画像収集、校正／再判定と安全停止の仕組みです。
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

初代3DS LLは **ChirunoMod v0.2.2＋ChLoad_HIMEM** 用の自前受信を使います。
**公式ChokistreamやJavaは不要です。** MacからTCP 6464へ直接接続します。
[旧3DS・HIMEMの準備と受信専用テスト](docs/OLD3DS_HIMEM_JA.md) を先に実施してください。
HIMEM＋USUM起動後にInputRedirectionを本体側で有効化し、ゲーム中の両画面受信を確認しました
（30秒で上61枚・下62枚）。その後、基本キーと1回のリセット復帰を確認しました。ギフト自動厳選のliveは校正完了まで拒否します。

| 機種／映像方式 | Video backend | 映像の接続 |
| --- | --- | --- |
| 初代3DS LL／ChirunoMod | ChirunoMod | Mac→3DS TCP 6464、JPEG・両画面・非インターレース |
| New 3DS／New 2DS／NTR-HR | NTR-HR | TCP 8000で設定、MacのUDP 8001で従来JPEGを受信 |

NTR-HRは旧3DS用ではありません。旧3DS向け実装はNTR受信コードをそのまま使わず、
TCPフレーミング、8分割画面の組み立て、色順補正を専用アダプターへ分離しています。
NTR-HR独自のFEC/KCP形式は対象外です。

共通の操作接続はLuma3DSの **InputRedirection UDP 4950** です。
L+下+SELECT → RosalinaのMiscellaneous options → Start InputRedirectionで有効にし、
3DSのIPを控えます。[Luma3DS公式資料](https://github.com/LumaTeam/Luma3DS/wiki/Rosalina)も参照してください。
Old 3DSでは**HIMEM／ゲーム起動後**の有効状態を再確認します。Start表示は未起動、Stop表示は起動中です。
今回、HIMEM起動後に未起動だったサービスを有効化して、ゲーム中の映像受信が復帰しました。

Macと3DSを同じLANへ接続します。GUIの **PC IP** にMacのLAN IPv4（例 `192.168.0.29:8001`）、
**3DS IP** に3DSのIPv4（例 `192.168.0.31`）、**Input UDP port** に4950を指定します。
ChirunoModではPC IPのポート部分は使わず、TCP送信元のIPv4だけを使います。
3DS IPは `IP:port` で映像TCPポートを変更できます。初期の127.0.0.1は実機には使えません。
MacのWi-Fiアドレスは `ipconfig getifaddr en0` 等で確認します（機器によりインターフェイス名は異なります）。
Macでローカルネットワーク通信の許可が表示されたら許可します。別ビューアとは同時接続しません。
起動直後の最初のJPEGだけが既知の2×50ピクセルになる場合は、映像接続を1回だけ自動でやり直します。
ボタンやゲームのリセットは送りません。再発・正常な映像の受信後の異常・停止操作後は再接続せず、安全停止します。

ゲームの文字速度は「はやい」、手持ちは空きを確保し、同種の別個体を入れず、
メニューの「ポケモン」を最初に開ける状態で受け取り直前に保存します。
ポニの古道とエーテルパラダイスは別のルートとして校正してください。

## アプリ内で自動受取・リセットを試す（色違い判定なし）

`run_hardware_test.command` を開くか、Recvの「実機テスト（受取・リセット）」を押します。
**日本語版ピカチュウの受け取り→リセット1回→タイトル→つづきから→フィールド復帰**を
アプリから試す診断です。手動の操作記録は不要です。
この成功は、ベベノム／タイプ：ヌルの色違い認識や自動厳選の検証完了を意味しません。

1. 配達員前・受取前に**本体でレポート保存**し、手持ちの空きを1つ以上確保します。
2. IPとChirunoModを設定して「受信開始（操作なし）」。上下画面が映ることを確認します。
3. **「1. 認識確認（送信0）」** を押します。ボタンは送らず、現在のフィールド／受取会話を確認します。
   フィールドから始めると開始位置を自動記録します。会話中なら前回の開始位置の記録がある場合に使えます。
4. 確認が通ったら、配達員前・受取前セーブ・手持ちの空きを確認してチェックし、
   **「2. 自動テスト1周」** を押します。操作範囲と上限をアプリで確認し、今回の1周を許可します。
5. アプリが会話を進め、ピカチュウの受取完了を確認できた場合だけリセットを1回送信します。
   タイトルのSTART、続行のA、開始画面への復帰まで自動で確認して終了します。
   **受取後のレポート保存はしません。自動セーブもありません。**

認識できない会話・低信頼度の受取文・映像停止・通信断では安全停止します。
リセットの自動再試行はなく、1回の診断は最大15操作です。色違い判定は行いません。
停止した場合は「記録フォルダを開く」で画像・OCR結果・停止理由を確認できます。
ログはPictures/ShinyHunterUSUMの `delivery-…` に保存され、毎回Codexにボタン操作を依頼する必要はありません。

自動診断の文字認識は**Mac内のApple Vision**で行い、外部OCRサービスやAPIは使いません。
Xcode Command Line Toolsが未導入の場合は `xcode-select --install` で準備します。
Swiftヘルパーは初回に自動ビルドしてキャッシュします。OCRの初回準備には約40〜60秒かかる場合があり、
その間は入力しません。準備後の保存画像の読取は、このMacで約0.1〜0.3秒でした。

受取完了は、補正ありOCRの高いスコア・補正なしOCRとの完了文一致・新しい複数フレームで確認し、
送信直前にも再確認します。疑問文・引用・未来形を完了として扱いません。スコアは確率ではありません。
タイトル・続行・ロトム画面の共通画像は実機の保存画像から作成しました。
日本語版ウルトラサンの現在のデータ用の診断で、実際の受け取りの完走は実機テストで確認します。

「詳細（手動記録）」には従来の1周記録・受動照合・最大3周再生も残しています。
主画面のギフト厳選と検証記録は独立しており、この診断では厳選のliveを解禁しません。

## 画像校正と安全な使い方

`Game Language` はJapanese／Englishを切り替えます。日本語版ではRecvの3ルートだけを選択できます。
**dry-runは起動・設定スロット変更・言語変更・映像方式変更のたびにONへ戻ります。**
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
.venv/bin/python tests/gui_smoke.py --backend ChirunoMod
.venv/bin/python tests/gui_smoke.py --backend NTR-HR
# macOS専用: GUI + Vision + 模擬3DSのTCP/UDP。実機には接続しません
.venv/bin/python tests/gui_auto_delivery_smoke.py
```

[旧3DS対応計画](docs/OLD3DS_PLAN.md)、[変更計画と事前調査](docs/IMPLEMENTATION_PLAN.md)、[検証結果と制限](docs/VALIDATION.md) を参照してください。
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
