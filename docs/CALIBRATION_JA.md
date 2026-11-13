# 日本語版の画像収集・校正・実機検証

このforkは未校正のまま自動厳選を開始しません。`profiles/ja.json` の座標・色は
**英語版を起点にした未検証の仮値**です。日本語の実画像・通常色／色違いの実測値は含みません。
`templates/ja/Recv/*.placeholder.json` は必要素材の説明で、認識用の画像ではありません。
英語画像へ自動フォールバックする処理もありません。

## 1. 操作を送らずに映像を集める

旧3DS LLでは先に [HIMEM上の通信検証](OLD3DS_HIMEM_JA.md) を行います。
Macと3DSを同一LANに接続し、ChirunoMod v0.2.2へ自前アダプターで接続します。公式Chokistreamは不要です。
New 3DS／NTRの場合は明示的に `--backend NTR-HR` を指定します。他のビューアは終了します。例のIPは必ず自分の環境に置き換えてください。

```sh
.venv/bin/python gift_tools.py capture --backend ChirunoMod \
  --local 192.168.1.10:8001 --console 192.168.1.50 \
  --seconds 30 --interval 0.3 --output captures/poipole-dialogue
```

このコマンドはChirunoModの設定・映像受信用TCP通信だけを行い、InputRedirectionへは何も送信しません。
物理ボタンで会話・メニューを進めてください。画面は回転補正済みのネイティブ解像度で保存されます。
下画面は320×240、上画面は400×240です。画面番号は **0=下、1=上** です。
GUIのRecordタブも映像確認に使用できますが、テンプレート作成には非可逆圧縮を追加しないCLIのPNGを推奨します。

各ルートを別々に収集します。設定対象名は `poipole`、`typenull_poni`、`typenull_aether` です。

| stage | 必要な画面・目印 | 到達操作 |
| --- | --- | --- |
| dialogue_name | 上画面のベベノム／タイプ：ヌルの名前が出る会話 | A。ポニは事前に短く右へ移動 |
| party_added | 手持ちに加わったことが分かる日本語メッセージ | B。ベベノムとエーテルのみ |
| dialogue_end | 受け取り後の最後の日本語会話 | ポニはB、エーテルはA |
| menu | 下画面のメニューが開いた目印 | X |
| party_level | 下画面の受け取り個体を探せる一覧／表示 | A |
| party_name | 下画面で対象個体が選択された名前表示 | 十字キー上 |
| restart_title | 上画面のUSUMタイトル側の目印 | START |
| save_file | 上画面のセーブデータ選択画面の固定文字 | 認識してからA |

`party_name` と色チェック領域は、既存の `Recv.check_summary` が参照していた下画面を起点にしています。
日本語版で実際に同じ画面・領域になるか、**受け取り個体を選択しているかを含めて**確認してください。
名前の一部分だけで別個体と一致しないようにし、改名した個体は別に校正します。
手持ちは空きを確保し、同種の別個体を入れないでください。ボックス送りの分岐は未対応です。
タイトルとセーブ画面は手動でリセットして収集します。最初の実行をツールの無条件リセットに頼りません。

## 2. 座標とテンプレートを作る

`profiles/ja.json` を作業用にコピーする場合、`template_root` はそのJSONファイルからの相対パスです。
画像を原寸で開き、各stageの `box: [左, 上, 右, 下]` を修正します。右端・下端は含みません。
必要なら `screen`、上下探索幅 `vertical`、待機回数 `attempts`、間隔 `interval` も調整します。
テンプレートとROIの高さは同じにし、横方向だけROI内で探索します。
上下探索はROI全体を移動します。画面外にはみ出す設定は安全停止になります。

```sh
.venv/bin/python gift_tools.py inspect --language Japanese --target poipole
.venv/bin/python gift_tools.py crop --language Japanese --target poipole \
  --stage dialogue_name --image captures/poipole-dialogue/upper-0001.png \
  --output templates/ja/Recv/poipole-dialogue_name.png
```

他のstageもmanifestのファイル名に合わせて切り出します。`*.placeholder.json` は残しても削除しても構いません。
保存するのは本物のゲーム画面のPNGで、文字を描き起こした代用品は使いません。

`threshold` はグレースケールの平均絶対差を255で割った値で、**小さいほど一致**です。
既定は0.12。0より大きく0.2以下に制限しています。成功画像だけで緩めず、別会話・別メニュー・
別個体・遷移途中・黒画面でも誤一致しないことを確認します。白一色のダミーは拒否します。

## 3. 通常色・色違い・判定不明を分ける

安全判定はBoostのカットシーン色判定ではなく、受け取り後の対象名と色領域を使います。
ギフト3ルートではBoostを無効にしています。

`colour` で次を調整できます。

- `box` / `screen`: 対象名が見える画面の色チェック領域。名前と同じ画面を要求します。
- `normal` / `shiny`: それぞれ実画像の領域の平均RGB。英語版由来の既定値は日本語版の実測値ではありません。
- `max_distance`: 色参照間の距離を1とした、参照色までの許容距離。0.5未満です。
- `min_margin`: 通常色参照と色違い参照への距離の差。差が小さい場合は判定不明です。
- `max_stddev`: パッチ内の色のばらつきの上限。輪郭や別の画面が混ざったときの拒否に使います。
- `samples` / `sample_interval`: 新しく完了したフレーム3〜20枚での一致条件。

通常色も色違いも、別タイミング／複数個体／同じ機材・NTR品質で集めます。
画質や色順も映像方式に依存します。ChirunoModで受信した画像を使い、NTRの校正を流用しません。
**本物の色違い画像がない状態では実機検証完了にしないでください。**
黒・白・別画面・遷移中・別個体をunknownの負例として集めます。

`freshness.max_age` は受信停止の上限秒数（既定2秒）、`freeze_timeout` は同一画素が続く上限秒数
（既定15秒）です。`max_span` は完全画面の組み立て時間の上限（省略時2秒）で、
原画像の古さも最初の分割片から数えます。静止メニューでも保守的に停止することがあります。実測の待機時間に合わせて
調整できますが、無限待ち／監視無効化にはできません。

## 4. 記録画像を再判定する

例として `captures/cases.json` を作ります。パスはmanifestからの相対パスです。

```json
[
  {"image":"normal/lower-0001.png", "expected":"normal"},
  {"image":"shiny/lower-0001.png", "expected":"shiny"},
  {"image":"wrong-menu/lower-0001.png", "expected":"unknown"},
  {"image":"dialogue/upper-0001.png", "stage":"dialogue_name", "expected":"match"},
  {"image":"wrong-dialogue/upper-0001.png", "stage":"dialogue_name", "expected":"no_match"}
]
```

```sh
.venv/bin/python gift_tools.py replay --language Japanese --target poipole \
  --cases captures/cases.json
```

全stageに正例 `match` と負例 `no_match` を追加し、通常色・色違い・unknownも網羅してください。
校正に使わなかった独立のフレームでも再判定し、3ルートを別々に検証します。
同じ切り出し画像を自身に当てただけの成功を、認識精度の検証に数えないでください。

GUIでdry-runを選んだまま手動で受け取り個体の表示へ進み、接続して確認します。
dry-runは物理ボタンを奪わず、自動入力・リセットを一切送信しません。
認識不能なら停止し、`~/Pictures/ShinyHunterUSUM/gift-日時/` に画像と `scores.jsonl` を保存します。
ログのscoreは確率ではありません。

## 5. 実機の検証項目とlive有効化

各ルートについて実際に確認します。

1. 保存位置、手持ちの空き、受け取り対象、メニューの「ポケモン」が最初に選択される状態。
2. 受け取り前から対象名・受け取り後・メニューまでの順序とROIが一致する。
3. 色違いは停止し、通常色だけがリセット候補になる。自動セーブは行わない。
4. 認識できない画像、しきい値付近、判定不一致では停止する。
5. 映像停止、同じ画像の繰り返し、Wi-Fi切断、操作通信失敗で停止し、再試行リセットしない。
6. 通常色の直後でも、最終再確認で別画面・色違い・unknownになればリセットしない。
7. タイトル／セーブ選択画面を認識し、次の受け取りに戻れる。

実機確認と画像のreplayが終わった操作者だけが、次のフラグでその事実を明示します。
これは**操作者の申告**であり、自動的に実機検証を証明する仕組みではありません。
単体テストの模擬画像でこの操作をしないでください。

```sh
.venv/bin/python gift_tools.py attest --language Japanese --target poipole --backend ChirunoMod \
  --cases captures/cases.json --hardware-verified
```

検証記録 `profiles/ja-poipole.validated.json` が作られます。通常色・色違い・unknownと全stageの
正負例がすべて成功し、必要な画像が揃っていないと作られません。
JSONプロファイルと全テンプレートのSHA-256に紐づくため、変更後は再確認が必要です。
ポニ／エーテルも別々に実施します。検証記録・個人の捕獲画像はGitに含めません。

GUIで言語・ルート・Profile JSONを選び、**最後に**dry-runを外します。
保存済みの受け取り直前から開始します。初回の自動リセットはありません。
通常色が新しい複数フレームで一致した場合だけ、直前の対象名・色判定を再確認して
L+R+SELECTを一度送ります。色違い候補では停止するので、目視で確認して手動保存してください。

## 未検証範囲

HIMEM＋日本語USUMゲーム中で、InputRedirectionを本体側で有効化した状態の映像受信を実機確認しました。
遠隔入力の反映、日本語の認識素材、実ゲームの色分布、会話の到達順序、リセット継続、長時間の厳選は未検証です。
純粋なRGB比較とテンプレート照合は任意の誤認識を数学的に排除するものではありません。
ガードは不明・エラー時に止めるためのものです。無人運転へ移す前に実機データで確認してください。
