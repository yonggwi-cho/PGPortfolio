"""
Step 2: Design the flyer layout using Claude.
Claude decides on colors, style, background image prompt, and section arrangement.
"""
import json
import anthropic
from .models import EventInfo, FlyerLayout


LAYOUT_SYSTEM_PROMPT = """あなたはプロのグラフィックデザイナーです。
イベント情報を元に、視覚的に魅力的なチラシのレイアウト設計を行います。

設計原則:
- イベントのカテゴリと雰囲気に合ったカラースキームを選ぶ
- 重要情報（タイトル・日時・場所）が最も目立つようにする
- 背景画像はテキストなしで依頼すること (テキストは後で別途合成する)
- 日本語イベントの場合も背景プロンプトは英語で書く
- レイアウトセクションは上から下の順で配置する
"""

LAYOUT_USER_TEMPLATE = """以下のイベント情報に基づいて、チラシのレイアウトを設計してください:

{event_info_json}

以下のJSONスキーマで出力してください:
{{
  "background_prompt": "背景画像生成プロンプト (英語, テキスト・文字なしで)",
  "style": "modern/elegant/festival/minimal/corporate",
  "color_scheme": {{
    "primary": "#XXXXXX",
    "secondary": "#XXXXXX",
    "accent": "#XXXXXX",
    "text_on_dark": "#FFFFFF",
    "text_on_light": "#1A1A1A",
    "overlay_color": "#000000",
    "overlay_opacity": 0.6
  }},
  "sections": [
    {{
      "name": "セクション名",
      "content_key": "EventInfoのフィールド名",
      "custom_content": null,
      "font_size_category": "title/heading/body/caption",
      "alignment": "center/left/right",
      "bold": true,
      "color_role": "text_on_dark",
      "margin_top_ratio": 0.05
    }}
  ],
  "designer_notes": "デザインの意図・説明"
}}

利用可能なcontent_key:
- title, subtitle, date, time, venue, address, description
- ticket_price, contact, website, organizer
- "datetime_combined" (日時を1行で表示)
- "venue_address_combined" (会場と住所を合わせて表示)
- custom (custom_contentを使用)

JSONのみを出力してください。"""


def design_flyer_layout(event_info: EventInfo, client: anthropic.Anthropic) -> FlyerLayout:
    """
    Design flyer layout using Claude with adaptive thinking.
    Claude determines colors, style, background prompt, and section arrangement.
    """
    print("🎨 レイアウトを設計中...")

    event_dict = event_info.model_dump(exclude_none=True)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=LAYOUT_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": LAYOUT_USER_TEMPLATE.format(
                event_info_json=json.dumps(event_dict, ensure_ascii=False, indent=2)
            )
        }]
    ) as stream:
        response = stream.get_final_message()

    raw_json = ""
    for block in response.content:
        if block.type == "text":
            raw_json = block.text.strip()
            break

    if raw_json.startswith("```"):
        lines = raw_json.split("\n")
        raw_json = "\n".join(lines[1:-1])

    data = json.loads(raw_json)
    layout = FlyerLayout(**data)

    print(f"✅ レイアウト設計完了: スタイル「{layout.style}」")
    print(f"   デザインメモ: {layout.designer_notes[:80]}...")
    return layout
