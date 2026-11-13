# Old 3DS＋ChirunoMod：無線状態とNFC Patch調査

## 今回の実測で分かった範囲

対象は操作者申告の初代3DS LL、Luma3DS v13.4、ChirunoMod v0.2.2、
ChLoad_HIMEM、日本語版ウルトラサンです。本体システムバージョンとゲーム更新版は未確認です。

| 状態 | 実測・操作者報告 |
| --- | --- |
| USUMゲーム中、HIMEM起動後のInputRedirection状態が未確認 | 黄色LED、TCP 6464タイムアウト、上0／下0。到達性診断も失敗 |
| USUMを中断したHOME | 水色LED、TCP接続・両画面受信成功。再試験では上45／下45まで受信 |
| 手動でUSUM再開 | 操作者は黄色LEDへ戻ると報告。再開後の別接続は約5秒でタイムアウト、上0／下0 |
| HIMEM起動後のRosalina状態を手動確認 | Start InputRedirection＝未起動だった |
| 操作者がInputRedirectionを有効化してUSUM再開 | ゲーム中も水色LED。10.055秒で上22／下21、別接続30.139秒で上61／下62。ゲーム内画像確認 |

全試験は受信のみです。操作用UDP 4950への送信、ボタン入力、リセットは行っていません。
InputRedirection有効化は操作者の本体上の手動操作です。NFCパッチは適用していません。
確認できたのはInputRedirectionが有効と申告された状態での映像受信であり、遠隔キーの反映ではありません。

HOMEの45枚試験は33.658秒で画面組み立ての2秒上限に達し、受信側が接続を閉じています。
そのため、その一本のTCP接続がUSUM再開時に自然に切れたという証拠としては扱いません。
ゲーム再開後の接続失敗は別セッションの測定です。
また起動直後に上画面の最初のJPEGが2×50で届く異常を観測し、安全停止しました。
初期化不具合の疑いがありますが、受信側で無条件に受け入れる変更はしていません。

## InputRedirectionを先に確認する根拠

[Luma3DS v13.4のInputRedirection](https://github.com/LumaTeam/Luma3DS/blob/v13.4/sysmodules/rosalina/source/input_redirection.c)
は開始時に `miniSocInit()` を呼びます。
[同版のminiSoc](https://github.com/LumaTeam/Luma3DS/blob/v13.4/sysmodules/rosalina/source/minisoc.c#L59)
にはネットワーク管理のインフラストラクチャ排他状態へ入り、状態をロックする処理があります。
HIMEM起動後のInputRedirection有効化が今回の受信復帰に寄与した可能性は、この実装と観測に整合します。
ただしMacから本体内部の状態を読んだわけではなく、全バージョンでの因果や安定性を証明していません。

したがって、この環境では起動時に次を確認します。

1. ChLoad_HIMEMでUSUMを起動する。
2. 必要に応じてゲームを中断したHOMEで、RosalinaのInputRedirectionが有効かを操作者が確認する。
   Start表示なら未起動、Stop表示なら起動中。
3. 未起動なら操作者が有効化し、ゲーム再開後も通常LAN接続・映像受信が続くか確認する。
4. この段階では受信だけを使い、キー反映・リセット継続・日本語認識は別々に検証する。

## NFC Patchの適用可否

[Chokistream開発者の無線モード資料](https://github.com/Eiim/Chokistream/wiki/Technical-info-on-bugs-and-quirks)
は、ゲームがWi-Fiからローカル無線へ切り替える問題と、USUMがNFC Patchの対象に含まれることを説明しています。
これはパッチ方式や全機種との互換性を保証する記述ではありません。

| 方法 | Old 3DS＋ChirunoModでの判断 |
| --- | --- |
| Chokistream内蔵NFC Patch | `NTRClient` のNTRメモリ書き込みコマンドとして実装されている。ChirunoMod TCP 6464へ送る方式ではなく、本受信機へそのまま流用できない |
| Lumaのゲーム向けIPSパッチ | Luma側でゲームコードを修正するため方式上は映像バックエンドと独立。ただし正確なゲーム・更新版・変更前バイト・他のパッチとの整合確認が必要。今回の日本語版・Old 3DSで適用検証していない |
| HIMEM起動後にInputRedirection有効化 | 今回は追加パッチなしでゲーム内の受信復帰を観測。遠隔操作・長時間・リセット継続は別途未検証 |

[ChokistreamのNTRClient実装](https://github.com/Eiim/Chokistream/blob/main/src/main/java/chokistream/NTRClient.java#L452)
にある `OLD` / `NEW` は本体システムバージョン11.3以前／11.4以降の区別であり、
Old 3DS／New 3DSという機種区分ではありません。
ChirunoMod v0.2.2の設定・映像プロトコルには、このNTRのメモリ書き込みコマンドはありません。

[Luma公式のゲームパッチ仕様](https://github.com/LumaTeam/Luma3DS/wiki/Optional-features#config-menu-options)
ではタイトルごとの `code.ips` が提供されています。
[USUM用パッチ作者の配布説明](https://gbatemp.net/threads/usum-ips-patches.488802/)にはNFC無効化の単機能パッチがあり、
対応ゲーム版の指定があります。ただし本調査では配布バイナリの内容や日本語版との一致を検証していません。
このパッチ集には他のゲーム挙動を変える項目もあるため、全体を受信対策として導入する判断はしません。
ゲーム更新版不明の状態で、固定アドレス書き込みや未検証のパッチを生成・適用していません。

## 現在の結論

今回の環境では、まずHIMEM起動後のInputRedirection有効状態の確認が有効な切り分けでした。
追加NFCパッチを適用せずに、USUMゲーム中での自前映像受信を確認しています。
本体・ゲームの更新版が未確認のため、NFC Patchの具体的な適用ファイルまでは確定していません。
liveの解禁記録は作らず、受信成功・入力反映・リセット継続・日本語認識の確認を分離したままです。
