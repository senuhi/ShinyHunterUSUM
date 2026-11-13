# 初代3DS LL：自前受信とHIMEM・InputRedirectionの検証

このforkはChirunoMod v0.2.2へ **Macから直接TCP接続** します。
**公式Chokistream、Java、OBS、画面キャプチャソフトのインストールは不要です。**
Chokistreamのソースは通信仕様の調査に使っただけで、実行時には呼び出しません。
受信に必要なMac側依存はPythonとPillow、GUIの場合はTkinterです。

## 現在の確認状況

2026-11-13、操作者から初代3DS LL／Luma3DS v13.4／ChirunoMod v0.2.2／通常ChLoad／
HOME画面と申告された環境へ、実際に自前受信機能で接続しました。
再確認試験10.28秒で、上画面・下画面各15枚の完全な8分割パスを受信し、
400×240／320×240の日本語HOME画面として向きと色を確認しました。
組み立て時間は上画面0.44〜1.36秒、下画面0.45〜1.38秒でした。
InputRedirectionは作成せず、操作UDPの送信もリセットも行っていません。

最初の接続ではJPEG寸法の不一致で安全停止しました。原因は未確定です。
その後にヘッダー／寸法を受信専用で調査し、再接続試験で成功しています。
起動直後を含めた安定性が確認済みという意味ではありません。

**ChLoad_HIMEM＋日本語版USUMでは受信専用試験を行い、現在の状態では接続に失敗しました。**
TCP 6464は約5秒でタイムアウト、上0枚／下0枚。追加診断もping応答0/3、ARPエントリーなし、
TCPは `EHOSTUNREACH` でした。USUM起動後のAP接続喪失／ローカル無線への切り替えが候補ですが、
3DS側の実状態やHzLog.log未確認のため断定できません。
[開発者の無線モード資料](https://github.com/Eiim/Chokistream/wiki/Technical-info-on-bugs-and-quirks)にもUSUMが記載されています。
この試験では操作ポートを使わず、ボタン入力・リセット・無線設定変更を行っていません。
InputRedirectionの同時動作とリセット後の継続は未検証です。
HOME受信の成功をHIMEMの成功に読み替えません。最新の実機記録はVALIDATION.mdも参照してください。

## 構成とプロトコルの違い

| 対象 | 映像 | 操作 |
| --- | --- | --- |
| 初代3DS LL＋ChirunoMod | Mac→3DS TCP 6464で直接接続。8バイトヘッダー＋JPEGデータ | Luma InputRedirection UDP 4950を別接続 |
| New 3DS＋NTR-HR（既存） | TCP 8000で設定、MacのUDP 8001へJPEG分割データを受信 | 同じく別接続のUDP 4950 |

GUIの **Video backend** は `ChirunoMod` を選びます。
**3DS IP** は `IP` または `IP:6464`、**PC IP** はMacのLAN IPv4（`:8001`付きでも可）です。
ChirunoModではPC IPのホスト部分をTCPの送信元に使い、8001へのUDP bindは行いません。
**Input UDP port** の既定は4950です。映像の6464とは別のポートです。
初期の127.0.0.1は実機接続には使えません。

`video_stream.py` が受信インターフェース、`chiruno_transport.py` と `ntr_transport.py` が
各プロトコルの実装です。操作は `tppflush.py`、認識と安全停止は `gift_hunt.py` に分離しています。

ChirunoModではJPEG・両画面・非インターレースを要求します。
TGA、インターレース、未知のフラグ／寸法は認識せず停止します。
旧3DSは画面を8片に分けて撮るため、完全なパスでも同一瞬間の画面ではありません。
順番どおりの0〜7が揃うまでは認識に渡さず、途中参加した最初の欠けたパスも捨てます。
同期後の欠落・重複・順序異常や2秒を超える組み立ては停止します。
JPEGの赤青順と回転を補正し、表示や認識は原寸のRGB画像に統一します。

## 準備と、段階を分けた実機試験

3DS側の配布元は [ChirunoMod公式](https://github.com/ChainSwordCS/ChirunoMod) と
[v0.2.2リリース](https://github.com/ChainSwordCS/ChirunoMod/releases/tag/v0.2.2) です。
Old 3DSの高メモリを使うゲームにはChLoad_HIMEMが用意されています。
ローダーをインストールしただけで、HIMEM上のUSUMで動いているとは判定しません。
Yを押しながら起動すると別のHzModになるため、本アダプターの試験では使用しません。

1. 通常ChLoad＋HOME画面で、**受信のみ**を確認する。
2. ChLoad_HIMEM＋日本語USUMへ切り替え、**受信のみ**を確認する。
3. USUM起動後のRosalinaでInputRedirectionが有効なことを確認し、Bで閉じられるメニューを
   手動で開いて、**Bを1回だけ**送信する。映像が継続することと実際の反応を目視する。
4. 操作者が物理ボタンでソフトリセットし、HIMEM・映像・InputRedirectionが継続するかを確認する。
   ツールの診断からリセットは送らない。切断したら停止し、自動再接続しない。
5. 3ルートの日本語画像・色・会話を別々に校正する。上記とは別の認識検証が必要。

操作用UDPには応答確認がありません。送信APIが成功しただけでは操作がゲームに届いたと認めません。
ゲーム起動に伴う再起動後はIP、ローダー、InputRedirectionの有効状態を再確認します。
別ビューアが接続中なら終了します。本ツールのGUIとCLIも同時に接続しません。

## 受信のみ：最初に使うコマンド

以下のIPは自分のLANの実値に置き換えます。
日本語テンプレートや校正記録がなくても、この受信試験は実行できます。

```sh
.venv/bin/python hardware_probe.py probe \
  --backend ChirunoMod --local 192.168.0.29 --console 192.168.0.31 \
  --seconds 10 --output captures/home-passive
```

**入力パケットを送らない**のが既定です。PNG、`frames.jsonl`、`report.json` を保存します。
`status: observed` は完全画面を受信できたという観測で、HIMEM／操作対応済みの意味ではありません。
JPEGやプロトコルの異常時は理由と直前のペイロード `last-packet.bin` を残します。

GUIで見る場合は `./run_macos.command` → GeneralでbackendとIPを設定 → 上下のScreenをチェック →
RecordタブのTVアイコンで受信します。最初の確認にギフト開始用の接続ボタンは使いません。
Recordの受信では日本語の認識素材は不要で、操作パケットも送りません。

素材の連続収集も自前受信です。

```sh
.venv/bin/python gift_tools.py capture --backend ChirunoMod \
  --local 192.168.0.29 --console 192.168.0.31 \
  --seconds 30 --output captures/poipole
```

## HIMEM上の受信とBだけの同時動作試験

USUMを起動し、InputRedirectionを有効にして、物理ボタンでBで閉じられるメニューを開きます。
ボタン送信の段階になってから次を明示して実行します。

```sh
.venv/bin/python hardware_probe.py probe \
  --local 192.168.0.29 --console 192.168.0.31 \
  --himem-usum --send-b --seconds 10 --output captures/himem-input
```

`--send-b` を付けたときだけ、両画面の新しい完全パスを確認してからBを1回押し、解放します。
START／SELECT／L+R／HOME／POWER／タッチ操作やリセットは送信しません。
`--himem-usum` は操作者による現在状態の申告で、機種やゲームを自動検出した結果ではありません。
送信後も両画面で最低3枚の完全パスが必要です。
`controller_effect_verified` は自動ではtrueになりません。画像と実画面で反応を確認します。

既定の `max_age`（原画像の古さ）と `max_span`（組み立て時間）は2秒、
同じ画素が続く `freeze_timeout` は15秒です。遅いときに診断用に調整できる範囲は有限です。
静止画面と映像フリーズは画素だけでは区別できず、安全側に停止する場合があります。
古い分割片を新鮮なフルフレームと扱ったり、監視を無効にしたりはしません。

## live解禁は受信成功とは別

次を実際に確認した操作者だけが検証記録を作ります。

- ChLoad_HIMEM上の日本語USUMで、Bが実際に反応し、その間も完全画面を受信できる。
- 物理ボタンによるリセット後も同じ構成で受信・操作が継続する。

```sh
.venv/bin/python hardware_probe.py attest --report captures/himem-input/report.json \
  --coexistence-observed --manual-reset-continuity-observed
```

これは明示的な操作者の確認記録であり、自動で実機互換性を証明するものではありません。
記録はアプリの設定フォルダーへ保存し、IP・映像ポート・操作ポート・画質・組み立て上限に紐づけます。
HOMEだけの観測、受信のみの記録、模擬データ、入力後の完全画面が足りない記録ではlive解禁しません。
手動リセット後に映像または入力が失われる場合は解禁せず、原因を調べます。

さらに [日本語版の校正手順](CALIBRATION_JA.md) を各ルートで行い、
`gift_tools.py attest` には **`--backend ChirunoMod`** を指定します。
NTRでの画像校正記録はChirunoModの校正の代わりにはなりません。
通信の同時動作記録と日本語の校正記録の両方が揃って初めてlive開始を許可します。
リセット直前にもこの条件と認識結果の鮮度を再確認し、どちらかが不明なら停止します。
