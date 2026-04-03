#!/usr/bin/env python3
"""
CLI entry point for the event flyer generator.

Usage:
    # Interactive mode (natural language input):
    python generate_flyer.py

    # With input text:
    python generate_flyer.py "来月15日に渋谷でジャズコンサート開催..."

    # Specify platform:
    python generate_flyer.py "..." --platform instagram   # 1080×1350 (default)
    python generate_flyer.py "..." --platform story       # 1080×1920
    python generate_flyer.py "..." --platform square      # 1080×1080

    # With output path:
    python generate_flyer.py "..." --output my_event.jpg

    # Demo mode:
    python generate_flyer.py --demo
    python generate_flyer.py --demo --platform story
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
        description="イベントチラシ生成システム (Multi-Model: Claude + Google Imagen 3 + PIL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
プラットフォーム一覧:
  instagram  Instagram フィード 4:5 (1080×1350)  ← デフォルト
  story      Instagram Stories / LINE VOOM 9:16 (1080×1920)
  square     正方形 1:1 (1080×1080) — LINE / Instagram

出力フォーマット: JPEG (SNSシェア向け最適化済み)

環境変数:
  ANTHROPIC_API_KEY  (必須)
  GOOGLE_API_KEY     (推奨: Google Imagen 3 背景生成)
  OPENAI_API_KEY     (代替: DALL-E 3 背景生成)
""",
    )
    parser.add_argument(
        "event_description",
        nargs="?",
        help="イベントの説明（自然言語）",
    )
    parser.add_argument(
        "--platform", "-p",
        default="instagram",
        choices=["instagram", "story", "square"],
        help="出力プラットフォーム (デフォルト: instagram)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="出力ファイルパス (デフォルト: flyer_<platform>.jpg)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="デモモード: サンプルイベントでチラシを生成",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY 環境変数を設定してください")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)

    # Default output filename includes platform name
    output_path = args.output or f"flyer_{args.platform}.jpg"

    if args.demo:
        event_description = DEMO_EVENT
        print(f"📌 デモモード: {args.platform} 向けチラシを生成します")
        print()
    elif args.event_description:
        event_description = args.event_description
    else:
        print("📝 イベントの詳細を入力してください（Ctrl+D または Ctrl+Z+Enter で確定）:")
        print()
        lines = []
        try:
            while True:
                lines.append(input())
        except EOFError:
            pass
        event_description = "\n".join(lines)
        print()

    if not event_description.strip():
        print("エラー: イベントの説明が空です")
        sys.exit(1)

    from event_flyer import generate_flyer

    output_path, event_info, layout = generate_flyer(
        user_input=event_description,
        output_path=output_path,
        platform_name=args.platform,
    )

    file_size_kb = os.path.getsize(output_path) // 1024
    print()
    print("📲 SNSシェア情報:")
    print(f"   ファイル  : {output_path}")
    print(f"   サイズ    : {file_size_kb} KB")
    print(f"   フォーマット: JPEG (Instagram・LINE 対応)")


if __name__ == "__main__":
    main()
