"""
Step 1: Extract structured event information from natural language using Claude.
"""
import json
import anthropic
from .models import EventInfo


EXTRACTION_SYSTEM_PROMPT = """あなたはイベント情報の専門的な抽出アシスタントです。
ユーザーが自然言語で説明したイベント情報を、正確に構造化されたJSONとして抽出してください。

重要な原則:
- 明示的に述べられた情報のみを抽出する (推測で補完しない)
- 日付・時間・場所・価格などの情報は原文を正確に保持する
- 情報がない場合はnullを使用する
- カテゴリはmusic/art/food/business/sports/generalのいずれか
"""

EXTRACTION_USER_TEMPLATE = """以下のイベント情報から構造化データを抽出してください:

{user_input}

JSONスキーマ:
{{
  "title": "イベントタイトル (必須)",
  "subtitle": "サブタイトル・キャッチコピー (任意)",
  "date": "開催日 (必須)",
  "time": "開催時間 (必須)",
  "venue": "会場名 (必須)",
  "address": "住所 (任意)",
  "description": "イベント説明・概要 (必須)",
  "highlights": ["見どころ1", "見どころ2"],
  "ticket_price": "チケット価格 (任意)",
  "contact": "問い合わせ先 (任意)",
  "website": "URL (任意)",
  "organizer": "主催者名 (任意)",
  "category": "music/art/food/business/sports/general"
}}

JSONのみを出力してください。"""


def extract_event_info(user_input: str, client: anthropic.Anthropic) -> EventInfo:
    """
    Extract structured event information from natural language using Claude.
    Uses streaming with adaptive thinking for accuracy.
    """
    print("📋 イベント情報を抽出中...")

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": EXTRACTION_USER_TEMPLATE.format(user_input=user_input)
        }]
    ) as stream:
        response = stream.get_final_message()

    # Extract JSON from response
    raw_json = ""
    for block in response.content:
        if block.type == "text":
            raw_json = block.text.strip()
            break

    # Clean up JSON if wrapped in markdown
    if raw_json.startswith("```"):
        lines = raw_json.split("\n")
        raw_json = "\n".join(lines[1:-1])

    data = json.loads(raw_json)
    event_info = EventInfo(**data)

    print(f"✅ イベント情報を抽出完了: 「{event_info.title}」")
    return event_info
