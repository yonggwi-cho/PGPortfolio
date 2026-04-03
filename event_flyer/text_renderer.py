"""
Step 4: Accurately render event text onto the background image using PIL.
All text information is rendered by PIL (not by AI), ensuring perfect accuracy
for dates, venues, prices, and other critical event details.
"""
import os
from PIL import Image, ImageDraw, ImageFont
from .models import EventInfo, FlyerLayout, LayoutSection
from .platforms import PlatformConfig

# Base font sizes designed for 1080px width
_BASE_WIDTH = 1080
_BASE_FONT_SIZES = {
    "title":   96,
    "heading": 60,
    "body":    40,
    "caption": 30,
}

# Font search paths for Japanese support
_JAPANESE_FONT_PATHS = [
    # Linux
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
_JAPANESE_FONT_BOLD_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansJP-Bold.otf",
]


def _scale(base_size: int, platform_width: int) -> int:
    """Scale a size proportionally to the platform width."""
    return max(1, int(base_size * platform_width / _BASE_WIDTH))


def _find_font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    paths = (_JAPANESE_FONT_BOLD_PATHS + _JAPANESE_FONT_PATHS) if bold else _JAPANESE_FONT_PATHS
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _apply_overlay(img: Image.Image, layout: FlyerLayout) -> Image.Image:
    overlay_rgb = _hex_to_rgb(layout.color_scheme.overlay_color)
    opacity = int(layout.color_scheme.overlay_opacity * 255)
    overlay = Image.new("RGBA", img.size, (*overlay_rgb, opacity))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _get_section_content(section: LayoutSection, event_info: EventInfo) -> str:
    if section.custom_content:
        return section.custom_content
    key = section.content_key
    if key == "datetime_combined":
        return f"{event_info.date}  {event_info.time}"
    if key == "venue_address_combined":
        parts = [event_info.venue]
        if event_info.address:
            parts.append(event_info.address)
        return "\n".join(parts)
    value = getattr(event_info, key, None)
    if value is None:
        return ""
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
    shadow_offset: int = 3,
) -> None:
    sx, sy = xy[0] + shadow_offset, xy[1] + shadow_offset
    draw.text((sx, sy), text, font=font, fill=(0, 0, 0, 140), anchor=anchor)
    draw.text(xy, text, font=font, fill=fill_color, anchor=anchor)


def _draw_decorative_line(
    draw: ImageDraw.ImageDraw, y: int, color: tuple, img_width: int, line_width: int = 2
) -> None:
    margin = _scale(60, img_width)
    draw.line([(margin, y), (img_width - margin, y)], fill=color, width=line_width)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current_line = ""
        for char in paragraph:
            test = current_line + char
            bbox = font.getbbox(test)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test
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
    platform: PlatformConfig,
) -> Image.Image:
    """
    Render the complete flyer by compositing event text onto the background.

    All text is drawn by PIL — never by an AI model — guaranteeing
    perfect accuracy for dates, venues, prices, and contact information.
    """
    print(f"✏️  テキストをレンダリング中 ({platform.width}×{platform.height})...")

    w, h = platform.width, platform.height
    padding = _scale(70, w)
    bar_h = _scale(8, w)

    img = _apply_overlay(background, layout).convert("RGBA")
    draw = ImageDraw.Draw(img)

    accent_rgb = _hex_to_rgb(layout.color_scheme.accent)
    primary_rgb = _hex_to_rgb(layout.color_scheme.primary)

    # Top decorative bar
    top_bar = Image.new("RGBA", (w, bar_h), (*accent_rgb, 230))
    img.paste(top_bar, (0, 0), top_bar)

    current_y = bar_h

    for section in layout.sections:
        content = _get_section_content(section, event_info)
        if not content:
            continue

        base_size = _BASE_FONT_SIZES.get(section.font_size_category, 40)
        font_size = _scale(base_size, w)
        font = _find_font(bold=section.bold, size=font_size)

        # Resolve text color
        color_role = section.color_role
        if color_role == "accent":
            text_color = (*accent_rgb, 255)
        elif color_role == "primary":
            text_color = (*primary_rgb, 255)
        elif color_role == "text_on_light":
            text_color = (*_hex_to_rgb(layout.color_scheme.text_on_light), 255)
        else:
            text_color = (*_hex_to_rgb(layout.color_scheme.text_on_dark), 255)

        current_y += int(section.margin_top_ratio * h)
        max_text_width = w - padding * 2
        lines = _wrap_text(content, font, max_text_width)
        line_height = int(font_size * 1.4)

        for i, line in enumerate(lines):
            if not line:
                current_y += font_size // 2
                continue

            if section.alignment == "center":
                x, anchor = w // 2, "mm"
            elif section.alignment == "right":
                x, anchor = w - padding, "rm"
            else:
                x, anchor = padding, "lm"

            if section.font_size_category == "heading" and i == 0:
                _draw_decorative_line(draw, current_y - font_size // 2 - _scale(6, w), (*accent_rgb, 180), w, 1)

            _draw_text_with_shadow(draw, (x, current_y), line, font, text_color, anchor=anchor)
            current_y += line_height

        if section.font_size_category == "heading":
            _draw_decorative_line(draw, current_y + _scale(6, w), (*accent_rgb, 180), w, 1)

    # Bottom decorative bar
    bottom_bar = Image.new("RGBA", (w, bar_h), (*accent_rgb, 230))
    img.paste(bottom_bar, (0, h - bar_h), bottom_bar)

    print("✅ テキストレンダリング完了")
    return img.convert("RGB")
