"""
Event Flyer Generator - Multi-Model Pipeline

Combines Claude (claude-opus-4-6), DALL-E 3, and PIL to generate
event flyers from natural language descriptions with accurate text rendering.
"""
from .models import EventInfo, FlyerLayout, ColorScheme, LayoutSection
from .pipeline import generate_flyer, generate_flyer_from_dict

__all__ = [
    "EventInfo",
    "FlyerLayout",
    "ColorScheme",
    "LayoutSection",
    "generate_flyer",
    "generate_flyer_from_dict",
]
