"""
Step 4: Accurately render event text onto the background image using PIL.
This ensures all text information is rendered correctly,
solving the accuracy problem of AI image generation models.
"""
import os
from PIL import Image, ImageDraw, ImageFont
from .models import EventInfo, FlyerLayout, LayoutSection

FLYER_WIDTH = 800
FLYER_HEIGHT = 1200

FONT_SIZES = {
    "title": 72,
    "heading": 48,
    "body": 32,
    "caption": 24,
}

# Font search paths for Japanese support
JAPANESE_FONT_PATHS = [
    # Linux system fonts
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansJP-Regular.otf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    # macOS
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    # Windows
    "C:/Windows/Fonts/msgothic.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
]

JAPANESE_FONT_BOLD_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansJP-Bold.otf",
]


def _find_font(bold: bool = False, size: int = 32) -> ImageFont.FreeTypeFont:
    """Find the best available font that supports Japanese characters."""
    paths = JAPANESE_FONT_BOLD_PATHS + JAPANESE_FONT_PATHS if bold else JAPANESE_FONT_PATHS

    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # Final fallback: default font (may not support Japanese)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _apply_overlay(img: Image.Image, layout: FlyerLayout) -> Image.Image:
    """Apply semi-transparent overlay for better text readability."""
    overlay_rgb = _hex_to_rgb(layout.color_scheme.overlay_color)
    opacity = int(layout.color_scheme.overlay_opacity * 255)
    overlay = Image.new("RGBA", img.size, (*overlay_rgb, opacity))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    return img_rgba.convert("RGB")


def _get_section_content(section: LayoutSection, event_info: EventInfo) -> str:
    """Get the text content for a section."""
    if section.custom_content:
        return section.custom_content

    key = section.content_key

    # Special combined fields
    if key == "datetime_combined":
        return f"{event_info.date}  {event_info.time}"
    if key == "venue_address_combined":
        parts = [event_info.venue]
        if event_info.address:
            parts.append(event_info.address)
        return "\n".join(parts)

    # Direct field access
    value = getattr(event_info, key, None)
    if value is None:
        return ""

    # Handle list fields (highlights)
    if isinstance(value, list):
        return "\n".join(f"◆ {item}" for item in value)

    return str(value)


def _draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    xy: tuple,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill_color: tuple,
    anchor: str = "mm",
    shadow_offset: int = 2,
    shadow_opacity: int = 128,
) -> None:
    """Draw text with a subtle drop shadow for readability."""
    # Shadow
    shadow_color = (0, 0, 0, shadow_opacity)
    sx, sy = xy[0] + shadow_offset, xy[1] + shadow_offset
    draw.text((sx, sy), text, font=font, fill=shadow_color, anchor=anchor)
    # Main text
    draw.text(xy, text, font=font, fill=fill_color, anchor=anchor)


def _draw_decorative_line(draw: ImageDraw.ImageDraw, y: int, color: tuple, width: int = 2) -> None:
    """Draw a decorative horizontal line."""
    margin = 60
    draw.line([(margin, y), (FLYER_WIDTH - margin, y)], fill=color, width=width)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width."""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue

        words = paragraph
        current_line = ""
        for char in words:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
    return lines


def render_flyer(
    background: Image.Image,
    event_info: EventInfo,
    layout: FlyerLayout,
) -> Image.Image:
    """
    Render the complete flyer by compositing event text onto the background.

    This is the key step that ensures text accuracy:
    - All text is rendered by PIL, not by AI
    - Every character is precisely positioned
    """
    print("✏️  テキストを正確にレンダリング中...")

    # Apply overlay for readability
    img = _apply_overlay(background, layout)
    draw = ImageDraw.Draw(img.convert("RGBA"))
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)

    accent_rgb = _hex_to_rgb(layout.color_scheme.accent)
    primary_rgb = _hex_to_rgb(layout.color_scheme.primary)

    # Add top decorative bar
    top_bar = Image.new("RGBA", (FLYER_WIDTH, 6), (*accent_rgb, 230))
    img.paste(top_bar, (0, 0), top_bar)

    # Render each section
    current_y = 0

    for section in layout.sections:
        content = _get_section_content(section, event_info)
        if not content:
            continue

        font_size = FONT_SIZES.get(section.font_size_category, 32)
        font = _find_font(bold=section.bold, size=font_size)

        # Get color
        color_role = section.color_role
        if color_role == "accent":
            text_color = (*accent_rgb, 255)
        elif color_role == "primary":
            text_color = (*primary_rgb, 255)
        elif color_role == "text_on_light":
            text_color = (*_hex_to_rgb(layout.color_scheme.text_on_light), 255)
        else:
            text_color = (*_hex_to_rgb(layout.color_scheme.text_on_dark), 255)

        # Apply top margin
        current_y += int(section.margin_top_ratio * FLYER_HEIGHT)

        # Handle text alignment and positioning
        padding = 60
        max_text_width = FLYER_WIDTH - padding * 2

        lines = _wrap_text(content, font, max_text_width)

        for line in lines:
            if not line:
                current_y += font_size // 2
                continue

            if section.alignment == "center":
                x = FLYER_WIDTH // 2
                anchor = "mm"
            elif section.alignment == "right":
                x = FLYER_WIDTH - padding
                anchor = "rm"
            else:
                x = padding
                anchor = "lm"

            # Add decorative line before headings (not the main title)
            if section.font_size_category == "heading" and line == lines[0]:
                _draw_decorative_line(draw, current_y - font_size // 2 - 5, (*accent_rgb, 180), 1)

            _draw_text_with_shadow(
                draw,
                (x, current_y),
                line,
                font,
                text_color,
                anchor=anchor,
            )
            current_y += int(font_size * 1.4)

        # Add line after heading
        if section.font_size_category == "heading":
            _draw_decorative_line(draw, current_y + 5, (*accent_rgb, 180), 1)

    # Bottom decorative bar
    bottom_bar = Image.new("RGBA", (FLYER_WIDTH, 6), (*accent_rgb, 230))
    img.paste(bottom_bar, (0, FLYER_HEIGHT - 6), bottom_bar)

    print(f"✅ テキストレンダリング完了")
    return img.convert("RGB")
