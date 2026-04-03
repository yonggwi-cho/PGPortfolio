"""
Step 3: Generate background image using DALL-E 3.
Falls back to a gradient background using PIL if OpenAI is not available.
"""
import io
import os
import requests
from PIL import Image, ImageDraw
from .models import FlyerLayout

FLYER_WIDTH = 800
FLYER_HEIGHT = 1200


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _generate_gradient_background(layout: FlyerLayout) -> Image.Image:
    """
    Generate a gradient background using PIL as fallback.
    Creates a visually appealing gradient from primary to secondary color.
    """
    primary_rgb = _hex_to_rgb(layout.color_scheme.primary)
    secondary_rgb = _hex_to_rgb(layout.color_scheme.secondary)
    accent_rgb = _hex_to_rgb(layout.color_scheme.accent)

    img = Image.new("RGB", (FLYER_WIDTH, FLYER_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Draw vertical gradient
    for y in range(FLYER_HEIGHT):
        ratio = y / FLYER_HEIGHT
        # Three-stop gradient: primary -> secondary -> accent blend
        if ratio < 0.5:
            t = ratio * 2
            r = int(primary_rgb[0] * (1 - t) + secondary_rgb[0] * t)
            g = int(primary_rgb[1] * (1 - t) + secondary_rgb[1] * t)
            b = int(primary_rgb[2] * (1 - t) + secondary_rgb[2] * t)
        else:
            t = (ratio - 0.5) * 2
            r = int(secondary_rgb[0] * (1 - t) + accent_rgb[0] * t * 0.3 + secondary_rgb[0] * t * 0.7)
            g = int(secondary_rgb[1] * (1 - t) + accent_rgb[1] * t * 0.3 + secondary_rgb[1] * t * 0.7)
            b = int(secondary_rgb[2] * (1 - t) + accent_rgb[2] * t * 0.3 + secondary_rgb[2] * t * 0.7)
        draw.line([(0, y), (FLYER_WIDTH, y)], fill=(r, g, b))

    # Add subtle geometric decoration
    overlay = Image.new("RGBA", (FLYER_WIDTH, FLYER_HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    accent_with_alpha = (*accent_rgb, 30)
    overlay_draw.ellipse(
        [-FLYER_WIDTH // 2, -FLYER_HEIGHT // 4, FLYER_WIDTH, FLYER_HEIGHT // 2],
        outline=(*accent_rgb, 60), width=3
    )
    overlay_draw.ellipse(
        [FLYER_WIDTH // 4, FLYER_HEIGHT * 3 // 4, FLYER_WIDTH * 3 // 2, FLYER_HEIGHT * 3 // 2],
        fill=accent_with_alpha
    )

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def generate_background(layout: FlyerLayout) -> Image.Image:
    """
    Generate background image.
    Uses DALL-E 3 if OPENAI_API_KEY is available, otherwise uses PIL gradient.
    """
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if openai_api_key:
        try:
            return _generate_dalle_background(layout, openai_api_key)
        except Exception as e:
            print(f"   ⚠️  DALL-E 3生成失敗 ({e})、グラデーション背景を使用します")

    print("   📐 グラデーション背景を生成中 (DALL-E 3を使用するにはOPENAI_API_KEYを設定してください)")
    return _generate_gradient_background(layout)


def _generate_dalle_background(layout: FlyerLayout, api_key: str) -> Image.Image:
    """Generate background image using DALL-E 3."""
    import openai

    print("   🖼️  DALL-E 3で背景画像を生成中...")

    # Ensure prompt emphasizes no text
    prompt = (
        f"{layout.background_prompt}. "
        "No text, no letters, no words, no typography. "
        "Clean background suitable for event flyer. "
        "High quality, professional photography or illustration style."
    )

    client = openai.OpenAI(api_key=api_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    img_response = requests.get(image_url, timeout=30)
    img_response.raise_for_status()

    img = Image.open(io.BytesIO(img_response.content))
    img = img.resize((FLYER_WIDTH, FLYER_HEIGHT), Image.LANCZOS)

    print("   ✅ DALL-E 3背景画像生成完了")
    return img
