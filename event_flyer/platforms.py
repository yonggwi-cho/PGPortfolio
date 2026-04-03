"""
Platform presets for social media sharing.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformConfig:
    name: str
    width: int
    height: int
    output_format: str       # "JPEG" or "PNG"
    jpeg_quality: int        # 0-95, JPEG only
    imagen_aspect: str       # Google Imagen 3 aspect ratio string
    dalle_size: str          # DALL-E 3 size string
    description: str


PLATFORMS: dict[str, PlatformConfig] = {
    # Instagram フィード (4:5) — 最もリーチが高い縦型投稿
    "instagram": PlatformConfig(
        name="instagram",
        width=1080,
        height=1350,
        output_format="JPEG",
        jpeg_quality=90,
        imagen_aspect="3:4",
        dalle_size="1024x1024",
        description="Instagram フィード 4:5 (1080×1350)",
    ),
    # Instagram / LINE Stories (9:16)
    "story": PlatformConfig(
        name="story",
        width=1080,
        height=1920,
        output_format="JPEG",
        jpeg_quality=90,
        imagen_aspect="9:16",
        dalle_size="1024x1792",
        description="Instagram Stories / LINE VOOM 9:16 (1080×1920)",
    ),
    # 正方形 — LINE シェア・Instagram 正方形
    "square": PlatformConfig(
        name="square",
        width=1080,
        height=1080,
        output_format="JPEG",
        jpeg_quality=88,
        imagen_aspect="1:1",
        dalle_size="1024x1024",
        description="正方形 1:1 (1080×1080) — LINE / Instagram",
    ),
}

DEFAULT_PLATFORM = "instagram"


def get_platform(name: str) -> PlatformConfig:
    if name not in PLATFORMS:
        raise ValueError(
            f"プラットフォーム '{name}' は不明です。"
            f"使用可能: {', '.join(PLATFORMS)}"
        )
    return PLATFORMS[name]
