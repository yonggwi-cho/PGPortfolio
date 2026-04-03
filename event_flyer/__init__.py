"""
Event Flyer Generator - Multi-Model Pipeline

Combines Claude (claude-opus-4-6), DALL-E 3, and PIL to generate
event flyers from natural language descriptions with accurate text rendering.
"""
from .models import EventInfo, FlyerLayout, ColorScheme, LayoutSection
from .pipeline import generate_flyer, generate_flyer_from_dict
from .platforms import PLATFORMS, get_platform

__all__ = [
    "EventInfo",
    "FlyerLayout",
    "ColorScheme",
    "LayoutSection",
    "generate_flyer",
    "generate_flyer_from_dict",
    "PLATFORMS",
    "get_platform",
]
