"""
Data models for the event flyer generation system.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class EventInfo(BaseModel):
    """Structured event information extracted from natural language."""
    title: str = Field(description="イベントのタイトル")
    subtitle: Optional[str] = Field(None, description="サブタイトルまたはキャッチコピー")
    date: str = Field(description="開催日 (例: 2024年3月15日)")
    time: str = Field(description="開催時間 (例: 18:00〜21:00)")
    venue: str = Field(description="会場名")
    address: Optional[str] = Field(None, description="会場の住所")
    description: str = Field(description="イベントの説明・概要")
    highlights: List[str] = Field(default_factory=list, description="見どころ・ハイライト")
    ticket_price: Optional[str] = Field(None, description="チケット価格")
    contact: Optional[str] = Field(None, description="問い合わせ先")
    website: Optional[str] = Field(None, description="公式サイトURL")
    organizer: Optional[str] = Field(None, description="主催者・団体名")
    category: str = Field(default="general", description="イベントカテゴリ (music/art/food/business/sports/general)")


class ColorScheme(BaseModel):
    """Color palette for the flyer."""
    primary: str = Field(description="メインカラー (hex)")
    secondary: str = Field(description="サブカラー (hex)")
    accent: str = Field(description="アクセントカラー (hex)")
    text_on_dark: str = Field(default="#FFFFFF", description="暗い背景上のテキスト色")
    text_on_light: str = Field(default="#1A1A1A", description="明るい背景上のテキスト色")
    overlay_color: str = Field(description="背景オーバーレイ色 (hex with alpha intent)")
    overlay_opacity: float = Field(default=0.6, description="オーバーレイ不透明度 (0.0-1.0)")


class LayoutSection(BaseModel):
    """A section in the flyer layout."""
    name: str = Field(description="セクション名")
    content_key: str = Field(description="EventInfoのフィールド名またはカスタムコンテンツ")
    custom_content: Optional[str] = Field(None, description="カスタムテキスト")
    font_size_category: str = Field(description="フォントサイズ: title/heading/body/caption")
    alignment: str = Field(default="center", description="テキスト揃え: left/center/right")
    bold: bool = Field(default=False)
    color_role: str = Field(default="text_on_dark", description="色の役割")
    margin_top_ratio: float = Field(default=0.0, description="上マージン (画像高さ比)")


class FlyerLayout(BaseModel):
    """Complete flyer layout specification."""
    background_prompt: str = Field(description="背景画像生成用のDALL-Eプロンプト (英語)")
    style: str = Field(description="デザインスタイル (modern/elegant/festival/minimal/corporate)")
    color_scheme: ColorScheme
    sections: List[LayoutSection] = Field(description="チラシのコンテンツセクション (上から順)")
    designer_notes: str = Field(description="デザイナーからのノート・意図")
