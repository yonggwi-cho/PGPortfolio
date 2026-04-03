"""
Step 3: Generate background image using an AI image model.

Priority order:
  1. Google Imagen 3  (GOOGLE_API_KEY が設定されている場合)
  2. DALL-E 3         (OPENAI_API_KEY が設定されている場合)
  3. PIL gradient     (フォールバック)
"""
import io
import os
import requests
from PIL import Image, ImageDraw
from .models import FlyerLayout

FLYER_WIDTH = 800
FLYER_HEIGHT = 1200

# No-text instruction appended to every background prompt
_NO_TEXT_SUFFIX = (
    "No text, no letters, no words, no numbers, no typography, no signs. "
    "Clean background suitable for event flyer overlay. "
    "High quality, professional style."
)


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

    Tries image generation models in priority order:
      1. Google Imagen 3  (requires GOOGLE_API_KEY)
      2. DALL-E 3         (requires OPENAI_API_KEY)
      3. PIL gradient     (always available as fallback)
    """
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if google_api_key:
        try:
            return _generate_imagen_background(layout, google_api_key)
        except Exception as e:
            print(f"   ⚠️  Google Imagen 3 生成失敗 ({e})")

    if openai_api_key:
        try:
            return _generate_dalle_background(layout, openai_api_key)
        except Exception as e:
            print(f"   ⚠️  DALL-E 3 生成失敗 ({e})")

    print("   📐 グラデーション背景を生成中")
    print("      (AI背景: GOOGLE_API_KEY または OPENAI_API_KEY を設定してください)")
    return _generate_gradient_background(layout)


def _generate_imagen_background(layout: FlyerLayout, api_key: str) -> Image.Image:
    """Generate background image using Google Imagen 3."""
    from google import genai
    from google.genai import types

    print("   🖼️  Google Imagen 3 で背景画像を生成中...")

    prompt = f"{layout.background_prompt}. {_NO_TEXT_SUFFIX}"

    client = genai.Client(api_key=api_key)
    response = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="3:4",          # portrait orientation for flyer
            safety_filter_level="BLOCK_SOME",
            person_generation="DONT_ALLOW",
        ),
    )

    image_bytes = response.generated_images[0].image.image_bytes
    img = Image.open(io.BytesIO(image_bytes))
    img = img.resize((FLYER_WIDTH, FLYER_HEIGHT), Image.LANCZOS)

    print("   ✅ Google Imagen 3 背景画像生成完了")
    return img


def _generate_dalle_background(layout: FlyerLayout, api_key: str) -> Image.Image:
    """Generate background image using DALL-E 3."""
    import openai

    print("   🖼️  DALL-E 3 で背景画像を生成中...")

    prompt = f"{layout.background_prompt}. {_NO_TEXT_SUFFIX}"

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

    print("   ✅ DALL-E 3 背景画像生成完了")
    return img
