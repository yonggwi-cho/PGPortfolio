#!/usr/bin/env python3
"""
CLI entry point for the event flyer generator.

Usage:
    # Interactive mode (natural language input):
    python generate_flyer.py

    # With input text:
    python generate_flyer.py "来月15日に渋谷でジャズコンサート開催..."

    # With output path:
    python generate_flyer.py "..." --output my_event.png

    # Demo mode (runs with sample event):
    python generate_flyer.py --demo
"""
import sys
import argparse
import os


DEMO_EVENT = """
来る2024年6月15日（土）、東京・渋谷の「Blue Moon Jazz Club」にて、
特別ジャズナイト「Midnight Blue Jazz Session」を開催します！

時間：19:00開場 / 20:00開演（〜23:00）
会場：Blue Moon Jazz Club（東京都渋谷区道玄坂2-10-7）

世界的ジャズピアニスト・山田太郎トリオによる特別ライブ！
ニューヨーク仕込みのアーバンジャズから、ボサノバ、スタンダードまで、
最高の音楽と夜をお楽しみください。

◆ 見どころ
- 山田太郎（ピアノ）、佐藤次郎（ベース）、田中三郎（ドラム）によるトリオ演奏
- スペシャルゲスト：ボーカリスト 鈴木花子（第1セット予定）
- ワンドリンク付き、フードメニューも充実

チケット：前売り ¥3,500 / 当日 ¥4,000
予約・問い合わせ：info@bluemoon-jazz.jp / 03-1234-5678
公式サイト：https://bluemoon-jazz.jp
主催：Blue Moon Jazz Club
"""


def main():
    parser = argparse.ArgumentParser(
        description="イベントチラシ生成システム (Multi-Model: Claude + DALL-E 3 + PIL)"
    )
    parser.add_argument(
        "event_description",
        nargs="?",
        help="イベントの説明（自然言語）"
    )
    parser.add_argument(
        "--output", "-o",
        default="flyer.png",
        help="出力ファイルパス (デフォルト: flyer.png)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="デモモード: サンプルイベントでチラシを生成"
    )
    args = parser.parse_args()

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY 環境変数を設定してください")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)

    # Get event description
    if args.demo:
        event_description = DEMO_EVENT
        print("📌 デモモードで実行します")
        print()
    elif args.event_description:
        event_description = args.event_description
    else:
        print("📝 イベントの詳細を入力してください（Ctrl+D または Ctrl+Z+Enter で確定）:")
        print()
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        event_description = "\n".join(lines)
        print()

    if not event_description.strip():
        print("エラー: イベントの説明が空です")
        sys.exit(1)

    # Run the pipeline
    from event_flyer import generate_flyer

    output_path, event_info, layout = generate_flyer(
        user_input=event_description,
        output_path=args.output,
    )

    print()
    print("📊 生成されたチラシの情報:")
    print(f"   タイトル: {event_info.title}")
    print(f"   日時: {event_info.date} {event_info.time}")
    print(f"   会場: {event_info.venue}")
    if event_info.ticket_price:
        print(f"   料金: {event_info.ticket_price}")
    print(f"   スタイル: {layout.style}")
    print(f"   ファイル: {output_path}")


if __name__ == "__main__":
    main()
