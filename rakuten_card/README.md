# 楽天カード利用明細 取得・分析ツール

## ファイル構成

| ファイル | 説明 |
|---|---|
| `fetch_transactions.py` | 楽天e-NAVIにログインして利用明細を取得 |
| `analyze_transactions.py` | 取得したCSVを分析してレポート出力 |

## セットアップ

```bash
pip install playwright pandas openpyxl matplotlib
playwright install chromium
```

## 使い方

### 1. 利用明細の取得

```bash
export RAKUTEN_USER_ID="楽天会員ID"
export RAKUTEN_PASSWORD="パスワード"

# 直近3ヶ月分を取得（デフォルト）
python fetch_transactions.py

# 直近6ヶ月分を取得、ブラウザ表示あり
python fetch_transactions.py --months 6 --show-browser

# 出力ファイル名を指定
python fetch_transactions.py --months 3 --output my_transactions.csv
```

### 2. 手動CSVダウンロード（推奨）

楽天e-NAVIでは手動でCSVをダウンロードすることもできます：

1. https://www.rakuten-card.co.jp/e-navi/ にログイン
2. 「ご利用明細」→ 月を選択
3. 「CSVダウンロード」ボタンをクリック

### 3. 利用明細の分析

```bash
# 基本分析
python analyze_transactions.py transactions.csv

# グラフも生成（matplotlib が必要）
python analyze_transactions.py transactions.csv --plot

# 上位20店舗を表示
python analyze_transactions.py transactions.csv --top 20
```

## 分析レポートの内容

- **月別利用金額** - 月ごとの支出推移
- **カテゴリ別集計** - 食費・交通・ショッピング等に自動分類
- **利用金額ランキング** - 高額利用店舗トップN
- **利用回数ランキング** - 頻繁に利用している店舗トップN
- **会員別集計** - 家族カードがある場合の内訳

## 注意事項

- 認証情報は環境変数で管理し、コードに直接書かないでください
- 楽天カードのウェブサイト構造が変わった場合、`fetch_transactions.py` の調整が必要です
- 自動ログインは楽天カードの利用規約を確認の上ご利用ください
