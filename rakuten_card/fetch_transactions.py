"""
楽天カード利用明細取得スクリプト

使い方:
  # 引数で直接渡す
  python fetch_transactions.py --user-id your_id --password your_pass

  # 環境変数で渡す
  export RAKUTEN_USER_ID="your_id"
  export RAKUTEN_PASSWORD="your_password"
  python fetch_transactions.py

  # 対話入力（引数も環境変数もない場合は自動で聞かれる）
  python fetch_transactions.py
"""

import os
import sys
import getpass
import argparse
import csv
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


LOGIN_URL = "https://www.rakuten-card.co.jp/e-navi/"
ENAVI_BASE = "https://www.rakuten-card.co.jp/e-navi"


def parse_args():
    parser = argparse.ArgumentParser(description="楽天カード利用明細を取得する")
    parser.add_argument("--user-id", dest="user_id", default="", help="楽天会員ID（省略時は環境変数 or 対話入力）")
    parser.add_argument("--password", default="", help="パスワード（省略時は環境変数 or 対話入力）")
    parser.add_argument("--months", type=int, default=3, help="取得する月数 (デフォルト: 3)")
    parser.add_argument("--output", default="transactions.csv", help="出力CSVファイル名")
    parser.add_argument("--show-browser", action="store_true", help="ブラウザを表示する")
    return parser.parse_args()


def login(page, user_id: str, password: str):
    """楽天e-NAVIにログインする"""
    print("[*] 楽天e-NAVIにアクセスしています...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # ユーザーIDとパスワードを入力
    try:
        # 楽天IDのフィールドを探す
        user_field = page.locator("input[name='u']").first
        if not user_field.is_visible():
            user_field = page.locator("input[type='text']").first
        user_field.fill(user_id)

        pwd_field = page.locator("input[name='p']").first
        if not pwd_field.is_visible():
            pwd_field = page.locator("input[type='password']").first
        pwd_field.fill(password)

        # ログインボタンをクリック
        login_btn = page.locator("input[type='submit'], button[type='submit']").first
        login_btn.click()
        page.wait_for_load_state("networkidle", timeout=15000)
        print("[*] ログイン完了")
    except Exception as e:
        # 別のフォーム構造を試す
        print(f"[!] 標準ログインフォームが見つかりません: {e}")
        print("[*] ページのスクリーンショットを保存します...")
        page.screenshot(path="login_debug.png")
        raise


def get_monthly_statements(page, months: int):
    """月別利用明細ページのURLリストを取得する"""
    # 利用明細ページへ移動
    print("[*] 利用明細ページに移動しています...")
    try:
        page.goto(f"{ENAVI_BASE}/members/statement/", wait_until="domcontentloaded", timeout=15000)
    except PlaywrightTimeoutError:
        page.goto(f"{ENAVI_BASE}/members/statement/index.xhtml", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(2000)

    # 月選択ドロップダウンを探す
    urls = []
    try:
        month_select = page.locator("select[name*='month'], select[id*='month'], select[name*='sMonth']").first
        options = month_select.locator("option").all()
        month_values = [opt.get_attribute("value") for opt in options[:months]]
        print(f"[*] {len(month_values)} ヶ月分の明細を取得します")
        for val in month_values:
            urls.append((val, page.url))
    except Exception:
        urls.append(("current", page.url))

    return urls


def scrape_statement_page(page) -> list[dict]:
    """現在のページから利用明細データを取得する"""
    transactions = []
    page.wait_for_timeout(1500)

    # テーブルを探す（複数のセレクタを試す）
    table_selectors = [
        "table.stmt-table",
        "table[class*='statement']",
        "table[class*='charge']",
        ".stmt-dtl-table",
        "table",
    ]

    table = None
    for sel in table_selectors:
        tables = page.locator(sel).all()
        for t in tables:
            # ヘッダーに「利用日」「金額」などが含まれるか確認
            text = t.inner_text()
            if any(kw in text for kw in ["利用日", "利用店名", "金額", "ご利用金額"]):
                table = t
                break
        if table:
            break

    if not table:
        print("[!] 利用明細テーブルが見つかりませんでした")
        page.screenshot(path="statement_debug.png")
        return transactions

    # ヘッダー行を取得
    headers = []
    header_row = table.locator("thead tr, tr:first-child").first
    for cell in header_row.locator("th, td").all():
        headers.append(cell.inner_text().strip())

    if not headers:
        headers = ["利用日", "利用店名", "利用者", "利用金額", "支払い方法", "今回支払額"]

    # データ行を取得
    rows = table.locator("tbody tr, tr:not(:first-child)").all()
    for row in rows:
        cells = row.locator("td").all()
        if not cells:
            continue
        row_data = {}
        for i, cell in enumerate(cells):
            key = headers[i] if i < len(headers) else f"col_{i}"
            row_data[key] = cell.inner_text().strip()
        # 空行をスキップ
        if any(v for v in row_data.values()):
            transactions.append(row_data)

    return transactions


def download_csv(page, output_path: str):
    """CSVダウンロードボタンがある場合に使用する"""
    try:
        with page.expect_download(timeout=10000) as dl_info:
            # CSVダウンロードボタンをクリック
            dl_btn = page.locator(
                "a[href*='csv'], a[href*='CSV'], button:has-text('CSV'), a:has-text('CSV'), a:has-text('ダウンロード')"
            ).first
            dl_btn.click()
        download = dl_info.value
        download.save_as(output_path)
        print(f"[*] CSVダウンロード完了: {output_path}")
        return True
    except Exception:
        return False


def fetch_all_transactions(user_id: str, password: str, months: int, output: str, headless: bool):
    """メイン処理: ログインして利用明細を取得する"""
    all_transactions = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ja-JP",
        )
        page = context.new_page()

        try:
            # ログイン
            login(page, user_id, password)

            # まずCSVダウンロードを試みる
            print("[*] 利用明細ページへ移動中...")
            try:
                page.goto(f"{ENAVI_BASE}/members/statement/", wait_until="domcontentloaded", timeout=15000)
            except PlaywrightTimeoutError:
                page.goto(f"{ENAVI_BASE}/members/statement/index.xhtml", wait_until="domcontentloaded", timeout=15000)

            page.wait_for_timeout(2000)

            # 月別にデータを取得
            for month_offset in range(months):
                print(f"\n[*] {month_offset + 1}/{months} ヶ月目を処理中...")

                # CSVダウンロードを試みる
                csv_downloaded = False
                if month_offset == 0:
                    csv_path = output.replace(".csv", f"_month{month_offset}.csv")
                    csv_downloaded = download_csv(page, csv_path)

                if not csv_downloaded:
                    # スクレイピングでデータ取得
                    txns = scrape_statement_page(page)
                    print(f"    {len(txns)} 件の明細を取得しました")
                    all_transactions.extend(txns)

                # 次の月へ（前月ボタンまたはドロップダウンで移動）
                if month_offset < months - 1:
                    try:
                        prev_btn = page.locator(
                            "a:has-text('前月'), a:has-text('前の月'), button:has-text('前月'), a[rel='prev']"
                        ).first
                        prev_btn.click()
                        page.wait_for_load_state("networkidle", timeout=10000)
                        page.wait_for_timeout(1500)
                    except Exception:
                        print(f"    [!] 前月への移動ができませんでした")
                        break

        except Exception as e:
            print(f"[!] エラーが発生しました: {e}")
            page.screenshot(path="error_debug.png")
            raise
        finally:
            browser.close()

    # CSVに保存
    if all_transactions:
        save_to_csv(all_transactions, output)
        print(f"\n[*] 合計 {len(all_transactions)} 件の明細を {output} に保存しました")
    else:
        print("[!] 明細データを取得できませんでした")
        print("    - CSVファイルが個別に保存されている場合は analyze_transactions.py で分析できます")

    return all_transactions


def save_to_csv(transactions: list[dict], filepath: str):
    """トランザクションをCSVファイルに保存する"""
    if not transactions:
        return
    fieldnames = list(transactions[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)


def main():
    args = parse_args()

    # 優先順位: コマンド引数 > 環境変数 > 対話入力
    user_id = args.user_id or os.environ.get("RAKUTEN_USER_ID", "")
    password = args.password or os.environ.get("RAKUTEN_PASSWORD", "")

    if not user_id:
        user_id = input("楽天会員ID: ").strip()
    if not password:
        password = getpass.getpass("パスワード: ")

    if not user_id or not password:
        print("エラー: IDとパスワードが必要です")
        sys.exit(1)

    headless = not args.show_browser

    print(f"楽天カード利用明細取得ツール")
    print(f"  取得月数: {args.months} ヶ月")
    print(f"  出力ファイル: {args.output}")
    print(f"  ヘッドレスモード: {headless}")
    print()

    fetch_all_transactions(
        user_id=user_id,
        password=password,
        months=args.months,
        output=args.output,
        headless=headless,
    )


if __name__ == "__main__":
    main()
