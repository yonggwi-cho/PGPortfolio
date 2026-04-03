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
from .platforms import PlatformConfig

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


def _generate_gradient_background(layout: FlyerLayout, platform: PlatformConfig) -> Image.Image:
    """Generate a gradient background using PIL as fallback."""
    w, h = platform.width, platform.height
    primary_rgb = _hex_to_rgb(layout.color_scheme.primary)
    secondary_rgb = _hex_to_rgb(layout.color_scheme.secondary)
    accent_rgb = _hex_to_rgb(layout.color_scheme.accent)

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        ratio = y / h
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
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    accent_with_alpha = (*accent_rgb, 30)
    overlay_draw.ellipse([-w // 2, -h // 4, w, h // 2], outline=(*accent_rgb, 60), width=3)
    overlay_draw.ellipse([w // 4, h * 3 // 4, w * 3 // 2, h * 3 // 2], fill=accent_with_alpha)

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    return img.convert("RGB")


def generate_background(layout: FlyerLayout, platform: PlatformConfig) -> Image.Image:
    """
    Generate background image for the given platform.

    Tries image generation models in priority order:
      1. Google Imagen 3  (requires GOOGLE_API_KEY)
      2. DALL-E 3         (requires OPENAI_API_KEY)
      3. PIL gradient     (always available as fallback)
    """
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if google_api_key:
        try:
            return _generate_imagen_background(layout, platform, google_api_key)
        except Exception as e:
            print(f"   ⚠️  Google Imagen 3 生成失敗 ({e})")

    if openai_api_key:
        try:
            return _generate_dalle_background(layout, platform, openai_api_key)
        except Exception as e:
            print(f"   ⚠️  DALL-E 3 生成失敗 ({e})")

    print("   📐 グラデーション背景を生成中")
    print("      (AI背景: GOOGLE_API_KEY または OPENAI_API_KEY を設定してください)")
    return _generate_gradient_background(layout, platform)


def _generate_imagen_background(
    layout: FlyerLayout, platform: PlatformConfig, api_key: str
) -> Image.Image:
    """Generate background image using Google Imagen 3."""
    from google import genai
    from google.genai import types

    print(f"   🖼️  Google Imagen 3 で背景画像を生成中 ({platform.imagen_aspect})...")

    prompt = f"{layout.background_prompt}. {_NO_TEXT_SUFFIX}"

    client = genai.Client(api_key=api_key)
    response = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=platform.imagen_aspect,
            safety_filter_level="BLOCK_SOME",
            person_generation="DONT_ALLOW",
        ),
    )

    image_bytes = response.generated_images[0].image.image_bytes
    img = Image.open(io.BytesIO(image_bytes))
    img = img.resize((platform.width, platform.height), Image.LANCZOS)

    print("   ✅ Google Imagen 3 背景画像生成完了")
    return img


def _generate_dalle_background(
    layout: FlyerLayout, platform: PlatformConfig, api_key: str
) -> Image.Image:
    """Generate background image using DALL-E 3."""
    import openai

    print(f"   🖼️  DALL-E 3 で背景画像を生成中 ({platform.dalle_size})...")

    prompt = f"{layout.background_prompt}. {_NO_TEXT_SUFFIX}"

    client = openai.OpenAI(api_key=api_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=platform.dalle_size,
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    img_response = requests.get(image_url, timeout=30)
    img_response.raise_for_status()

    img = Image.open(io.BytesIO(img_response.content))
    img = img.resize((platform.width, platform.height), Image.LANCZOS)

    print("   ✅ DALL-E 3 背景画像生成完了")
    return img
