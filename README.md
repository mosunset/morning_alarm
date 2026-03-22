# morning_alarm

朝の時報サイト操作を自動化するPythonスクリプトです。
`Selenium`で時報サイトを開き、指定要素をクリックし、一定待機後に音量設定を行い、さらに`NICT`タブを開いて定期更新します。

## 概要

このアプリは次の処理を自動で実行します。

1. 対象サイトを選択（3種類）
2. ネットワーク診断（DNS解決・HTTP疎通）
3. 対象サイトを開いて1秒待機後、指定XPathをクリック
4. Windowsマスター音量を指定値へ設定（既定40%）
5. `NICT`ページを新しいタブで開き、指定XPathをクリック
6. 以後、指定分ごとに2タブをリロードして再クリック（タブごとに1秒待機）

## 対応環境

- OS: Windows（音量設定はWindowsのみ対応）
- Python: `>=3.13`
- パッケージ管理: `uv`

## インストール

```bash
uv sync
```

## 実行方法

```bash
uv run main.py [-s SITE] [-v VOLUME_PERCENT] [-r RELOAD_MINUTES]
```

すべてオプション引数です。指定順は自由です。  
省略時は `site=web117`、`volume_percent=40`、`reload_minutes=5` を使います。

指定可能な値:

- `1` または `web117`
- `2` または `azo234`
- `3` または `piliapp`

例:

```bash
uv run main.py --site 1
uv run main.py -s azo234
uv run main.py -r 10 -s 3 -v 30
uv run main.py --volume 25 --reload-minutes 15
```

## サイト定義

### メイン対象サイト

- `web117`: `https://web117.jp/`
- `azo234`: `https://azo234.github.io/timesignal/`
- `piliapp`: `https://jp.piliapp.com/time-now/jp/117/`

### メインサイトのクリックXPath

- `web117`: `/html/body/section/div[1]/p[2]/button`
- `azo234`: `/html/body`
- `piliapp`: `/html/body/div[2]/div/div[1]/div/div[3]/div[1]/div/div[1]/div[1]/i`

### 追加タブ（常に開く）

- URL: `https://www.nict.go.jp/JST/JST6/index.html`
- クリックXPath: `/html/body/footer/nav/div[2]/div/input`

## 詳細仕様

### 0. 既定値の管理

- 既定パラメータ（時間系と音量）は `morning_alarm/defaults.py` に集約
- 処理ロジックとCLI表示文言の既定値は同じ定数を参照

### 1. サイト選択仕様

- `--site` / `-s` で指定した値を解釈
- `1/2/3`指定は内部でサイトキーへ変換
- サイトキーが不正な場合は案内を表示して終了

### 2. ネットワーク診断仕様

対象URLのホストに対し、以下を実施します。

- DNS解決確認
- HTTP疎通を3回試行
- 平均応答時間を算出

判定条件（快適判定）:

- 成功率: `100%`
- 平均応答時間: `1.2秒以下`

条件を満たさない場合、ブラウザ操作へ進まず終了します。

### 3. Selenium操作仕様（初回）

1. Chromeを起動（最大化）
2. メイン対象URLへアクセス
3. ページ読込完了後、1秒待機してメイン対象XPathをクリック
   - 通常クリック失敗時はJavaScriptクリックへフォールバック
4. 音量を`volume_percent`へ設定（既定40、`--volume` / `-v`）
5. `NICT`を新規タブで開いてアクティブ化
6. `NICT`側もページ読込完了後、1秒待機してXPathをクリック

### 4. 定期更新仕様（初期値と可変値）

- 間隔: `reload_minutes`分（既定`5分`、`--reload-minutes` / `-r`）
- 対象: メインタブ + `NICT`タブ
- 各サイクルで実施:
  - タブ切替
  - リロード
  - 読み込み完了待機
  - 対応XPathを再クリック
  - タブ処理ごとに1秒待機

### 5. ブラウザ終了仕様

- 既定ではブラウザを閉じずに残します（`detach`）
- スクリプトは定期更新ループで継続動作します

## 音量設定仕様

- 使用ライブラリ: `pycaw`
- 設定値: `volume_percent`（既定`40%`）
- Windows以外ではスキップして失敗扱いログを出力
- 例外時は処理を継続し、ログのみ出力

## ログ出力仕様

主に次のイベントを標準出力へ表示します。

- サイト選択結果
- ネットワーク診断結果（成功率・平均応答）
- クリック成功/失敗
- 音量設定成功/失敗
- 追加タブのオープン状態
- 定期更新サイクル開始・各タブ更新結果

## 停止方法

実行中のターミナルで`Ctrl + C`を押して停止します。

## ファイル構成

- `main.py`
  - サイト選択と全体フロー制御
- `morning_alarm/network.py`
  - ネットワーク診断
- `morning_alarm/web.py`
  - Selenium操作、クリック、定期リロード、音量設定
- `morning_alarm/defaults.py`
  - 既定パラメータ（時間系・音量）を集約

## 既知事項

- エディタの`basedpyright`で外部パッケージimport警告が出ることがありますが、`uv run`での実行は可能です。
