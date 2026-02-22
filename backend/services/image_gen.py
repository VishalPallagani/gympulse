import io
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageFont

BACKGROUND = "#0A0A0A"
SURFACE = "#1A1A1A"
ACCENT = "#F97316"
TEXT = "#FFFFFF"
MUTED = "#9CA3AF"

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_URLS = {
    "regular": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf",
    "bold": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf",
}


def _ensure_fonts() -> dict[str, Path]:
    FONT_DIR.mkdir(parents=True, exist_ok=True)

    paths = {
        "regular": FONT_DIR / "Roboto-Regular.ttf",
        "bold": FONT_DIR / "Roboto-Bold.ttf",
    }

    for key, file_path in paths.items():
        if file_path.exists():
            continue
        try:
            response = httpx.get(FONT_URLS[key], timeout=20)
            if response.status_code == 200:
                file_path.write_bytes(response.content)
        except Exception:
            # Font download is best-effort; fallback fonts are used if unavailable.
            pass

    return paths


def _font(weight: str, size: int) -> ImageFont.ImageFont:
    paths = _ensure_fonts()
    path = paths.get(weight)
    try:
        if path and path.exists():
            return ImageFont.truetype(str(path), size=size)
    except Exception:
        pass
    return ImageFont.load_default()


def _format_int(value: Any) -> str:
    try:
        return f"{int(float(value)):,}"
    except Exception:
        return "0"


def generate_story_card_png(stats: dict[str, Any]) -> bytes:
    image = Image.new("RGB", (1080, 1920), BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = _font("bold", 92)
    headline_font = _font("bold", 128)
    label_font = _font("bold", 54)
    body_font = _font("regular", 42)
    tiny_font = _font("regular", 30)

    week_number = datetime.now().isocalendar().week
    summary = stats.get("summary", {})
    quick = stats.get("quick_stats", {})
    weekly_rows = stats.get("weekly_volume", [])
    prs = stats.get("personal_records", [])

    week_volume = quick.get("total_volume", 0)
    week_sessions = quick.get("sessions", 0)
    streak = summary.get("current_streak", 0)

    top_lift = "NO PR YET"
    if prs:
        top_pr = max(prs, key=lambda item: float(item.get("weight_kg") or 0))
        top_lift = (
            f"{str(top_pr.get('exercise_name', 'Lift')).upper()}: "
            f"{_format_int(top_pr.get('weight_kg'))} KG PR \U0001F3C6"
        )

    draw.text((540, 90), "GYMPL\u25CFSE", fill=ACCENT, font=title_font, anchor="mm")
    draw.line((120, 180, 960, 180), fill=ACCENT, width=4)
    draw.text((540, 305), f"WEEK {week_number}", fill=TEXT, font=headline_font, anchor="mm")

    stats_y = 430
    line_gap = 95
    draw.text((120, stats_y), f"{_format_int(week_volume)} KG MOVED", fill=TEXT, font=label_font)
    draw.text((120, stats_y + line_gap), f"{_format_int(week_sessions)} SESSIONS", fill=TEXT, font=label_font)
    draw.text((120, stats_y + (line_gap * 2)), top_lift, fill=ACCENT, font=body_font)
    draw.text(
        (120, stats_y + (line_gap * 3)),
        f"\U0001F525 {_format_int(streak)} DAY STREAK",
        fill=TEXT,
        font=label_font,
    )

    chart_top = 980
    chart_left = 120
    chart_right = 960
    chart_height = 560
    draw.rounded_rectangle((chart_left, chart_top, chart_right, chart_top + chart_height), radius=24, fill=SURFACE)
    draw.text((chart_left + 30, chart_top + 22), "VOLUME BY MUSCLE GROUP", fill=MUTED, font=body_font)

    latest_week = weekly_rows[-1] if weekly_rows else {}
    bars = []
    for key, value in latest_week.items():
        if key in {"week_start", "total"}:
            continue
        try:
            numeric = float(value or 0)
        except (TypeError, ValueError):
            numeric = 0
        if numeric > 0:
            bars.append((str(key), numeric))

    if not bars:
        group = str(summary.get("top_muscle_group", "Full Body"))
        bars = [(group, 1.0)]

    bars = sorted(bars, key=lambda item: item[1], reverse=True)[:6]
    max_value = max(value for _, value in bars) or 1.0

    bar_start_y = chart_top + 115
    bar_gap = 70
    bar_max_width = 560

    for index, (label, value) in enumerate(bars):
        y = bar_start_y + (index * bar_gap)
        draw.text((chart_left + 32, y), label.upper(), fill=TEXT, font=tiny_font)
        bg_left = chart_left + 300
        bg_top = y + 6
        bg_right = bg_left + bar_max_width
        bg_bottom = y + 44

        draw.rounded_rectangle((bg_left, bg_top, bg_right, bg_bottom), radius=12, fill="#2C2C2C")
        fill_width = int((value / max_value) * bar_max_width)
        draw.rounded_rectangle((bg_left, bg_top, bg_left + fill_width, bg_bottom), radius=12, fill=ACCENT)
        draw.text((bg_right + 18, y + 2), _format_int(value), fill=MUTED, font=tiny_font)

    draw.text((540, 1770), "Share your gains", fill=ACCENT, font=body_font, anchor="mm")
    draw.text((540, 1835), "gympu.lse | Track yours on WhatsApp", fill=MUTED, font=tiny_font, anchor="mm")

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
