"""
Main pipeline: orchestrates the multi-model event flyer generation.

Pipeline:
  1. Claude (claude-opus-4-6)   → Extract structured event info from natural language
  2. Claude (claude-opus-4-6)   → Design flyer layout (colors, style, sections)
  3. DALL-E 3 / PIL fallback  → Generate background image (no text)
  4. PIL                       → Render text accurately onto background
"""
import os
import anthropic
from PIL import Image

from .models import EventInfo, FlyerLayout
from .content_extractor import extract_event_info
from .layout_designer import design_flyer_layout
from .image_generator import generate_background
from .text_renderer import render_flyer


def generate_flyer(
    user_input: str,
    output_path: str = "flyer.png",
    anthropic_api_key: str | None = None,
) -> tuple[str, EventInfo, FlyerLayout]:
    """
    Generate an event flyer from natural language description.

    Args:
        user_input: Natural language description of the event (Japanese or English)
        output_path: Path to save the output PNG
        anthropic_api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)

    Returns:
        Tuple of (output_path, event_info, flyer_layout)
    """
    print("=" * 60)
    print("🎪 イベントチラシ生成システム (Multi-Model Pipeline)")
    print("=" * 60)
    print()

    # Initialize Claude client
    api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    client = anthropic.Anthropic(api_key=api_key)

    # Step 1: Extract event information using Claude
    print("[Step 1/4] Claude: イベント情報を自然言語から抽出")
    event_info = extract_event_info(user_input, client)
    print()

    # Step 2: Design flyer layout using Claude
    print("[Step 2/4] Claude: チラシレイアウトを設計")
    layout = design_flyer_layout(event_info, client)
    print()

    # Step 3: Generate background image
    print("[Step 3/4] 背景画像を生成")
    background = generate_background(layout)
    print()

    # Step 4: Render text accurately onto background
    print("[Step 4/4] PIL: テキスト情報を正確に合成")
    flyer = render_flyer(background, event_info, layout)
    print()

    # Save output
    flyer.save(output_path, "PNG", quality=95)
    print("=" * 60)
    print(f"✅ チラシ生成完了!")
    print(f"   出力ファイル: {output_path}")
    print(f"   イベント: {event_info.title}")
    print(f"   日時: {event_info.date} {event_info.time}")
    print(f"   会場: {event_info.venue}")
    print("=" * 60)

    return output_path, event_info, layout


def generate_flyer_from_dict(
    event_dict: dict,
    output_path: str = "flyer.png",
    anthropic_api_key: str | None = None,
) -> tuple[str, EventInfo, FlyerLayout]:
    """
    Generate a flyer from a pre-structured event info dictionary.
    Skips the extraction step (Step 1) and goes directly to layout design.
    """
    print("=" * 60)
    print("🎪 イベントチラシ生成システム (構造化データから)")
    print("=" * 60)
    print()

    api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    client = anthropic.Anthropic(api_key=api_key)

    event_info = EventInfo(**event_dict)
    print(f"📋 イベント情報: 「{event_info.title}」")
    print()

    print("[Step 1/3] Claude: チラシレイアウトを設計")
    layout = design_flyer_layout(event_info, client)
    print()

    print("[Step 2/3] 背景画像を生成")
    background = generate_background(layout)
    print()

    print("[Step 3/3] PIL: テキスト情報を正確に合成")
    flyer = render_flyer(background, event_info, layout)
    print()

    flyer.save(output_path, "PNG", quality=95)
    print("=" * 60)
    print(f"✅ チラシ生成完了! → {output_path}")
    print("=" * 60)

    return output_path, event_info, layout
