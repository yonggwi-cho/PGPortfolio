"""
楽天カード利用明細分析スクリプト

使い方:
  python analyze_transactions.py transactions.csv
  python analyze_transactions.py transactions.csv --plot
  python analyze_transactions.py transactions.csv --top 10
"""

import argparse
import sys
import re
from pathlib import Path
from collections import defaultdict


def parse_args():
    parser = argparse.ArgumentParser(description="楽天カード利用明細を分析する")
    parser.add_argument("csv_file", help="利用明細CSVファイル")
    parser.add_argument("--plot", action="store_true", help="グラフを表示する")
    parser.add_argument("--top", type=int, default=10, help="上位N件を表示 (デフォルト: 10)")
    parser.add_argument("--output-dir", default=".", help="グラフ保存ディレクトリ")
    return parser.parse_args()


# ---- カテゴリ分類ルール ----
CATEGORY_RULES = {
    "食費": [
        r"スーパー", r"マート", r"食品", r"フード", r"ファミリーマート", r"セブン.?イレブン",
        r"ローソン", r"コンビニ", r"吉野家", r"すき家", r"マクドナルド", r"モスバーガー",
        r"ケンタッキー", r"松屋", r"サイゼリヤ", r"ガスト", r"ラーメン", r"寿司", r"焼肉",
        r"居酒屋", r"カフェ", r"スタバ", r"ドトール", r"コメダ", r"ウェルシア", r"食堂",
        r"弁当", r"惣菜", r"肉", r"魚", r"野菜",
    ],
    "交通": [
        r"JR", r"東京メトロ", r"都営", r"Suica", r"PASMO", r"鉄道", r"バス", r"タクシー",
        r"ウーバー", r"Uber", r"電車", r"新幹線", r"飛行機", r"ANA", r"JAL", r"航空",
        r"駐車", r"ETC", r"高速",
    ],
    "ショッピング": [
        r"楽天市場", r"Amazon", r"アマゾン", r"ヨドバシ", r"ビックカメラ", r"ユニクロ",
        r"ZARA", r"無印良品", r"MUJI", r"ニトリ", r"イケア", r"IKEA", r"百貨店",
        r"デパート", r"ショッピング", r"モール",
    ],
    "サブスクリプション": [
        r"Netflix", r"ネットフリックス", r"Spotify", r"Apple", r"Google", r"YouTube",
        r"Prime", r"プライム", r"Disney", r"ディズニー", r"Hulu", r"U-NEXT",
        r"Adobe", r"Microsoft", r"Office365", r"iCloud",
    ],
    "医療・健康": [
        r"病院", r"クリニック", r"薬局", r"ドラッグストア", r"マツキヨ", r"ツルハ",
        r"歯科", r"眼科", r"整形", r"内科", r"外科", r"調剤",
    ],
    "光熱費・通信": [
        r"電力", r"電気", r"ガス", r"水道", r"NTT", r"docomo", r"ドコモ", r"au",
        r"SoftBank", r"ソフトバンク", r"楽天モバイル", r"格安SIM", r"インターネット",
        r"Wi-Fi",
    ],
    "娯楽・レジャー": [
        r"映画", r"シネマ", r"ゲーム", r"カラオケ", r"ボウリング", r"スポーツ",
        r"ジム", r"フィットネス", r"温泉", r"旅行", r"ホテル", r"宿泊",
    ],
    "教育": [
        r"書籍", r"本屋", r"教材", r"塾", r"スクール", r"セミナー", r"Udemy",
        r"学習", r"受験",
    ],
}


def categorize(shop_name: str) -> str:
    for category, patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            if re.search(pattern, shop_name, re.IGNORECASE):
                return category
    return "その他"


def parse_amount(amount_str: str) -> int:
    """金額文字列を整数に変換する"""
    if not amount_str:
        return 0
    # 「¥1,234」「1,234円」「1234」などに対応
    cleaned = re.sub(r"[¥￥,円\s]", "", str(amount_str))
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return 0


def detect_columns(headers: list[str]) -> dict:
    """CSVヘッダーからカラム名を推定する"""
    col_map = {}

    date_patterns = ["利用日", "日付", "date", "使用日", "Date"]
    shop_patterns = ["利用店名", "店名", "加盟店", "shop", "利用先", "支払先", "利用店名・商品名"]
    amount_patterns = ["利用金額", "金額", "支払額", "今回支払金額", "お支払い金額", "amount", "Amount"]
    member_patterns = ["利用者", "会員番号", "使用者"]
    method_patterns = ["支払い方法", "支払方法", "分割回数"]

    def find_col(patterns):
        for p in patterns:
            for h in headers:
                if p.lower() in h.lower():
                    return h
        return None

    col_map["date"] = find_col(date_patterns)
    col_map["shop"] = find_col(shop_patterns)
    col_map["amount"] = find_col(amount_patterns)
    col_map["member"] = find_col(member_patterns)
    col_map["method"] = find_col(method_patterns)

    return col_map


def load_csv(filepath: str):
    """CSVファイルを読み込む（エンコーディングを自動検出）"""
    import csv

    encodings = ["utf-8-sig", "utf-8", "shift_jis", "cp932", "euc_jp"]
    for enc in encodings:
        try:
            with open(filepath, encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                headers = reader.fieldnames or []
                print(f"[*] エンコーディング: {enc}, カラム: {headers}")
                return rows, list(headers)
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"CSVファイルを読み込めませんでした: {filepath}")


def analyze(transactions: list[dict], col_map: dict, top_n: int):
    """利用明細を分析してサマリーを出力する"""
    shop_col = col_map.get("shop")
    amount_col = col_map.get("amount")
    date_col = col_map.get("date")
    member_col = col_map.get("member")

    # 金額と店名を正規化
    records = []
    for row in transactions:
        shop = row.get(shop_col, "不明") if shop_col else "不明"
        amount = parse_amount(row.get(amount_col, "0")) if amount_col else 0
        date = row.get(date_col, "") if date_col else ""
        member = row.get(member_col, "") if member_col else ""
        if amount > 0:
            records.append({
                "date": date,
                "shop": shop,
                "amount": amount,
                "member": member,
                "category": categorize(shop),
                "raw": row,
            })

    if not records:
        print("[!] 有効な明細データが見つかりませんでした")
        print("    金額カラムが正しく検出されていない可能性があります")
        print(f"    検出カラム: {col_map}")
        return records

    total = sum(r["amount"] for r in records)

    print("\n" + "=" * 60)
    print("  楽天カード利用明細 分析レポート")
    print("=" * 60)
    print(f"  明細件数: {len(records):,} 件")
    print(f"  合計金額: ¥{total:,}")
    print(f"  平均利用額: ¥{total // len(records):,}")

    # ---- 月別集計 ----
    monthly = defaultdict(int)
    for r in records:
        date_str = r["date"]
        # YYYY/MM/DD, YYYY-MM-DD, YY/MM/DD などに対応
        m = re.match(r"(\d{2,4})[/\-年](\d{1,2})", date_str)
        if m:
            year = m.group(1)
            month = m.group(2).zfill(2)
            key = f"{year}/{month}"
        else:
            key = date_str[:7] if len(date_str) >= 7 else "不明"
        monthly[key] += r["amount"]

    if len(monthly) > 1:
        print("\n【月別利用金額】")
        for month in sorted(monthly.keys()):
            bar = "█" * (monthly[month] // 10000)
            print(f"  {month}: ¥{monthly[month]:>10,}  {bar}")

    # ---- カテゴリ別集計 ----
    by_category = defaultdict(int)
    by_category_count = defaultdict(int)
    for r in records:
        by_category[r["category"]] += r["amount"]
        by_category_count[r["category"]] += 1

    print("\n【カテゴリ別利用金額】")
    sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    for cat, amt in sorted_cats:
        pct = amt / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat:<16}: ¥{amt:>10,} ({pct:5.1f}%)  [{by_category_count[cat]:3d}件]  {bar}")

    # ---- 利用店舗ランキング ----
    shop_totals = defaultdict(int)
    shop_counts = defaultdict(int)
    for r in records:
        shop_totals[r["shop"]] += r["amount"]
        shop_counts[r["shop"]] += 1

    print(f"\n【利用金額 上位{top_n}店舗】")
    top_shops = sorted(shop_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    for i, (shop, amt) in enumerate(top_shops, 1):
        print(f"  {i:2}. {shop[:30]:<30} ¥{amt:>10,} ({shop_counts[shop]}回)")

    # ---- 利用回数ランキング ----
    print(f"\n【利用回数 上位{top_n}店舗】")
    top_freq = sorted(shop_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    for i, (shop, count) in enumerate(top_freq, 1):
        avg = shop_totals[shop] // count
        print(f"  {i:2}. {shop[:30]:<30} {count:3d}回  平均¥{avg:,}")

    # ---- 会員別集計 ----
    if member_col:
        by_member = defaultdict(int)
        for r in records:
            if r["member"]:
                by_member[r["member"]] += r["amount"]
        if len(by_member) > 1:
            print("\n【会員別利用金額】")
            for member, amt in sorted(by_member.items(), key=lambda x: x[1], reverse=True):
                pct = amt / total * 100
                print(f"  {member}: ¥{amt:,} ({pct:.1f}%)")

    print("\n" + "=" * 60)
    return records


def plot_charts(records: list[dict], output_dir: str):
    """グラフを生成して保存する"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        # 日本語フォント設定
        for font in fm.findSystemFonts():
            if any(name in font for name in ["NotoSansCJK", "IPAGothic", "Hiragino", "Yu Gothic", "Meiryo"]):
                fm.fontManager.addfont(font)
                plt.rcParams["font.family"] = fm.FontProperties(fname=font).get_name()
                break
        else:
            plt.rcParams["font.family"] = "sans-serif"
    except ImportError:
        print("[!] matplotlib がインストールされていません。グラフ生成をスキップします")
        print("    pip install matplotlib でインストールしてください")
        return

    from collections import defaultdict
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # カテゴリ別円グラフ
    by_category = defaultdict(int)
    for r in records:
        by_category[r["category"]] += r["amount"]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # 円グラフ
    cats = list(by_category.keys())
    amts = [by_category[c] for c in cats]
    axes[0].pie(amts, labels=cats, autopct="%1.1f%%", startangle=140)
    axes[0].set_title("カテゴリ別利用金額")

    # 月別棒グラフ
    monthly = defaultdict(int)
    for r in records:
        date_str = r["date"]
        m = re.match(r"(\d{2,4})[/\-年](\d{1,2})", date_str)
        if m:
            key = f"{m.group(1)}/{m.group(2).zfill(2)}"
        else:
            key = "不明"
        monthly[key] += r["amount"]

    months = sorted(monthly.keys())
    vals = [monthly[m] / 10000 for m in months]
    axes[1].bar(months, vals, color="steelblue")
    axes[1].set_title("月別利用金額")
    axes[1].set_xlabel("月")
    axes[1].set_ylabel("金額 (万円)")
    axes[1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    chart_path = output_dir / "rakuten_analysis.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n[*] グラフを保存しました: {chart_path}")


def main():
    args = parse_args()

    if not Path(args.csv_file).exists():
        print(f"エラー: ファイルが見つかりません: {args.csv_file}")
        sys.exit(1)

    print(f"[*] CSVファイルを読み込んでいます: {args.csv_file}")
    transactions, headers = load_csv(args.csv_file)
    print(f"[*] {len(transactions)} 件のデータを読み込みました")

    col_map = detect_columns(headers)
    print(f"[*] カラム検出結果: {col_map}")

    records = analyze(transactions, col_map, top_n=args.top)

    if args.plot and records:
        plot_charts(records, args.output_dir)


if __name__ == "__main__":
    main()
