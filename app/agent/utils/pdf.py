from __future__ import annotations
from pathlib import Path
from typing import List
import re

import arabic_reshaper
from bidi.algorithm import get_display
from markdown_it import MarkdownIt
from markdown_it.token import Token
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


HEADER_HEIGHT = 1.6 * inch
FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
MONTSERRAT_REGULAR_PATH = FONTS_DIR / "Montserrat-Regular.ttf"
MONTSERRAT_BOLD_PATH = FONTS_DIR / "Montserrat-Bold.ttf"
ARABIC_REGULAR_PATH = FONTS_DIR / "Amiri-Regular.ttf"
ARABIC_BOLD_PATH = FONTS_DIR / "Amiri-Bold.ttf"

MONTSERRAT_REGULAR_FONT_NAME = "Montserrat-Regular"
MONTSERRAT_BOLD_FONT_NAME = "Montserrat-Bold"
ARABIC_REGULAR_FONT_NAME = "Amiri-Regular"
ARABIC_BOLD_FONT_NAME = "Amiri-Bold"

_FONTS_REGISTERED = False


def _ensure_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    if not MONTSERRAT_REGULAR_PATH.exists():
        raise FileNotFoundError(
            f"Montserrat regular font not found at {MONTSERRAT_REGULAR_PATH}"
        )
    if not MONTSERRAT_BOLD_PATH.exists():
        raise FileNotFoundError(
            f"Montserrat bold font not found at {MONTSERRAT_BOLD_PATH}"
        )

    if not ARABIC_REGULAR_PATH.exists():
        raise FileNotFoundError(
            f"Arabic regular font not found at {ARABIC_REGULAR_PATH}"
        )
    if not ARABIC_BOLD_PATH.exists():
        raise FileNotFoundError(f"Arabic bold font not found at {ARABIC_BOLD_PATH}")

    pdfmetrics.registerFont(
        TTFont(MONTSERRAT_REGULAR_FONT_NAME, str(MONTSERRAT_REGULAR_PATH))
    )
    pdfmetrics.registerFont(
        TTFont(MONTSERRAT_BOLD_FONT_NAME, str(MONTSERRAT_BOLD_PATH))
    )
    pdfmetrics.registerFont(TTFont(ARABIC_REGULAR_FONT_NAME, str(ARABIC_REGULAR_PATH)))
    pdfmetrics.registerFont(TTFont(ARABIC_BOLD_FONT_NAME, str(ARABIC_BOLD_PATH)))
    _FONTS_REGISTERED = True


ARABIC_CHAR_PATTERN = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


def _contains_arabic(text: str) -> bool:
    return bool(ARABIC_CHAR_PATTERN.search(text))


def _shape_arabic_text(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


_md = MarkdownIt()


def _escape_text(value: str) -> str:
    """Escape HTML special chars for ReportLab paragraphs."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_inline(inline_token: Token) -> tuple[str, bool]:
    """Render inline markdown token stream into minimal HTML supported by ReportLab."""
    if inline_token.children is None:
        raw_text = inline_token.content or ""
        contains_arabic = _contains_arabic(raw_text)
        if contains_arabic:
            raw_text = _shape_arabic_text(raw_text)
        return _escape_text(raw_text), contains_arabic

    chunks: List[str] = []
    contains_arabic = False
    for child in inline_token.children:
        if child.type == "text":
            segment = child.content or ""
            if _contains_arabic(segment):
                segment = _shape_arabic_text(segment)
                contains_arabic = True
            chunks.append(_escape_text(segment))
        elif child.type == "softbreak":
            chunks.append("<br/>")
        elif child.type == "hardbreak":
            chunks.append("<br/><br/>")
        elif child.type == "strong_open":
            chunks.append("<b>")
        elif child.type == "strong_close":
            chunks.append("</b>")
        elif child.type == "em_open":
            chunks.append("<i>")
        elif child.type == "em_close":
            chunks.append("</i>")
        elif child.type == "code_inline":
            chunks.append(
                "<font face='Courier'>{}</font>".format(_escape_text(child.content))
            )
        elif child.type == "link_open":
            href = ""
            if child.attrs:
                href = child.attrs.get("href", "") or ""
            chunks.append(f"<u>{_escape_text(href)}:</u> ")
        elif child.type == "link_close":
            continue
        else:
            # Fallback to raw content
            fallback = child.content or ""
            if _contains_arabic(fallback):
                fallback = _shape_arabic_text(fallback)
                contains_arabic = True
            chunks.append(_escape_text(fallback))
    text = "".join(chunks).strip()
    if not text:
        raw = inline_token.content or ""
        if _contains_arabic(raw):
            raw = _shape_arabic_text(raw)
            contains_arabic = True
        text = _escape_text(raw)
    return text, contains_arabic


def _list_flowable(
    items: List[dict[str, str | bool]],
    *,
    bullet_type: str,
    start: int = 1,
    body_style: ParagraphStyle,
    body_style_ar: ParagraphStyle,
) -> ListFlowable:
    list_contains_arabic = any(item.get("contains_arabic") for item in items)
    list_items: List[ListItem] = []
    for item in items:
        text = item.get("text", "")
        style = body_style_ar if item.get("contains_arabic") else body_style
        list_items.append(ListItem(Paragraph(text, style), leftIndent=0))

    bullet_font_name = (
        body_style_ar.fontName if list_contains_arabic else body_style.fontName
    )
    bullet_font_size = (
        body_style_ar.fontSize if list_contains_arabic else body_style.fontSize
    )
    return ListFlowable(
        list_items,
        bulletType=bullet_type,
        start=start if bullet_type == "1" else None,
        bulletFontName=bullet_font_name,
        bulletFontSize=bullet_font_size,
        bulletColor=colors.HexColor("#444444"),
        leftIndent=18,
    )


def _interpolate_color(start, end, factor: float):
    """Return a Color linearly interpolated between start and end."""
    return colors.Color(
        red=start.red + (end.red - start.red) * factor,
        green=start.green + (end.green - start.green) * factor,
        blue=start.blue + (end.blue - start.blue) * factor,
    )


def _draw_first_page_header(canvas, doc, title: str, subtitle: str) -> None:
    """Render a gradient header band with centered title/subtitle."""
    canvas.saveState()
    width, height = doc.pagesize
    header_height = HEADER_HEIGHT

    top = height
    start_color = colors.HexColor("#1d4ed8")
    end_color = colors.HexColor("#14b8a6")
    steps = 160
    step_height = header_height / steps
    for step in range(steps):
        factor = step / max(steps - 1, 1)
        fill = _interpolate_color(start_color, end_color, factor)
        y = top - header_height + step * step_height
        rect_height = (
            step_height if step < steps - 1 else header_height - step * step_height
        )
        canvas.setFillColor(fill)
        canvas.rect(
            0,
            y,
            width,
            rect_height,
            stroke=0,
            fill=1,
        )

    canvas.setFillColor(colors.white)
    title_text = title
    title_has_arabic = _contains_arabic(title_text)
    title_font = (
        ARABIC_BOLD_FONT_NAME if title_has_arabic else MONTSERRAT_BOLD_FONT_NAME
    )
    if title_has_arabic:
        title_text = _shape_arabic_text(title_text)
    title_size = 26
    usable_width = width - (doc.leftMargin + doc.rightMargin)
    while (
        canvas.stringWidth(title_text, title_font, title_size) > usable_width
        and title_size > 16
    ):
        title_size -= 1
    title_y = top - (header_height / 2) + 12
    title_x = (width - canvas.stringWidth(title_text, title_font, title_size)) / 2
    canvas.setFont(title_font, title_size)
    canvas.drawString(title_x, title_y, title_text)

    subtitle_text = subtitle
    subtitle_has_arabic = _contains_arabic(subtitle_text)
    subtitle_font = (
        ARABIC_REGULAR_FONT_NAME
        if subtitle_has_arabic
        else MONTSERRAT_REGULAR_FONT_NAME
    )
    if subtitle_has_arabic:
        subtitle_text = _shape_arabic_text(subtitle_text)
    subtitle_size = 12
    subtitle_width = canvas.stringWidth(subtitle_text, subtitle_font, subtitle_size)
    subtitle_x = (width - subtitle_width) / 2
    subtitle_y = title_y - 24
    canvas.setFont(subtitle_font, subtitle_size)
    canvas.drawString(subtitle_x, subtitle_y, subtitle_text)

    canvas.restoreState()


def markdown_to_pdf(
    markdown_text: str, output_path: Path, *, header_title: str | None = None
) -> None:
    """
    Convert Markdown content into a styled PDF document.

    Supports headings, paragraphs, bullet lists, numbered lists, emphasis, and inline code.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_fonts()

    story = []
    styles = getSampleStyleSheet()

    heading_styles = {
        1: ParagraphStyle(
            "Heading1",
            parent=styles["Heading1"],
            fontName=MONTSERRAT_BOLD_FONT_NAME,
            fontSize=20,
            leading=26,
            spaceAfter=12,
            textColor=colors.HexColor("#111111"),
        ),
        2: ParagraphStyle(
            "Heading2",
            parent=styles["Heading2"],
            fontName=MONTSERRAT_BOLD_FONT_NAME,
            fontSize=16,
            leading=22,
            spaceBefore=6,
            spaceAfter=10,
            textColor=colors.HexColor("#222222"),
        ),
        3: ParagraphStyle(
            "Heading3",
            parent=styles["Heading3"],
            fontName=MONTSERRAT_BOLD_FONT_NAME,
            fontSize=14,
            leading=20,
            spaceBefore=4,
            spaceAfter=8,
            textColor=colors.HexColor("#333333"),
        ),
    }

    heading_styles_ar = {
        1: ParagraphStyle(
            "Heading1Arabic",
            parent=styles["Heading1"],
            fontName=ARABIC_BOLD_FONT_NAME,
            fontSize=20,
            leading=26,
            spaceAfter=12,
            textColor=colors.HexColor("#111111"),
            alignment=TA_RIGHT,
            wordWrap="RTL",
        ),
        2: ParagraphStyle(
            "Heading2Arabic",
            parent=styles["Heading2"],
            fontName=ARABIC_BOLD_FONT_NAME,
            fontSize=16,
            leading=22,
            spaceBefore=6,
            spaceAfter=10,
            textColor=colors.HexColor("#222222"),
            alignment=TA_RIGHT,
            wordWrap="RTL",
        ),
        3: ParagraphStyle(
            "Heading3Arabic",
            parent=styles["Heading3"],
            fontName=ARABIC_BOLD_FONT_NAME,
            fontSize=14,
            leading=20,
            spaceBefore=4,
            spaceAfter=8,
            textColor=colors.HexColor("#333333"),
            alignment=TA_RIGHT,
            wordWrap="RTL",
        ),
    }

    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["BodyText"],
        fontName=MONTSERRAT_REGULAR_FONT_NAME,
        fontSize=11,
        leading=15,
        spaceAfter=6,
        textColor=colors.HexColor("#2f2f2f"),
    )

    body_style_ar = ParagraphStyle(
        "BodyTextArabic",
        parent=styles["BodyText"],
        fontName=ARABIC_REGULAR_FONT_NAME,
        fontSize=11,
        leading=15,
        spaceAfter=6,
        textColor=colors.HexColor("#2f2f2f"),
        alignment=TA_RIGHT,
        wordWrap="RTL",
    )

    tokens = _md.parse(markdown_text)
    list_stack: List[dict[str, object]] = []

    def flush_list():
        if not list_stack:
            return
        current = list_stack.pop()
        items = current.get("items") or []
        if not items:
            return
        bullet_type = current["type"]
        start = current.get("start", 1) or 1
        story.append(
            _list_flowable(
                items,
                bullet_type="1" if bullet_type == "ordered" else "bullet",
                start=start,
                body_style=body_style,
                body_style_ar=body_style_ar,
            )
        )
        story.append(Spacer(1, 10))

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            flush_list()
            level = int(token.tag[1])
            inline_token = tokens[i + 1]
            text, has_arabic = _render_inline(inline_token)
            style_source = heading_styles_ar if has_arabic else heading_styles
            style = style_source.get(level)
            if style is None:
                style = style_source[3]
            story.append(Paragraph(text, style))
            story.append(Spacer(1, 6 if level >= 3 else 12))
            i += 3  # skip inline + close
            continue

        if token.type == "paragraph_open":
            inline_token = tokens[i + 1]
            text, has_arabic = _render_inline(inline_token)
            if text:
                style = body_style_ar if has_arabic else body_style
                story.append(Paragraph(text, style))
                story.append(Spacer(1, 6))
            i += 3
            continue

        if token.type in {"bullet_list_open", "ordered_list_open"}:
            flush_list()
            start = 1
            if token.type == "ordered_list_open" and token.attrs:
                start_attr = token.attrs.get("start")
                if start_attr:
                    try:
                        start = int(start_attr)
                    except ValueError:
                        start = 1
            list_stack.append(
                {
                    "type": "bullet" if token.type == "bullet_list_open" else "ordered",
                    "items": [],
                    "start": start,
                }
            )
            i += 1
            continue

        if token.type == "list_item_open":
            # collect text until list_item_close
            inline_fragments: List[str] = []
            item_contains_arabic = False
            j = i + 1
            while j < len(tokens) and tokens[j].type != "list_item_close":
                if tokens[j].type == "inline":
                    fragment_text, fragment_has_arabic = _render_inline(tokens[j])
                    if fragment_text:
                        inline_fragments.append(fragment_text.strip())
                    if fragment_has_arabic:
                        item_contains_arabic = True
                j += 1
            sentence = " ".join(
                fragment.strip() for fragment in inline_fragments if fragment.strip()
            )
            if list_stack and sentence:
                list_stack[-1]["items"].append(
                    {"text": sentence, "contains_arabic": item_contains_arabic}
                )
            i = j + 1
            continue

        if token.type in {"bullet_list_close", "ordered_list_close"}:
            flush_list()
            i += 1
            continue

        if token.type == "hr":
            flush_list()
            story.append(Spacer(1, 12))
            i += 1
            continue

        i += 1

    flush_list()

    if not story:
        story.append(Paragraph("No documentation generated.", body_style))

    # Reserve space beneath the header band on the first page
    story.insert(0, Spacer(1, HEADER_HEIGHT))

    header_text = (
        header_title.strip()
        if header_title and header_title.strip()
        else "Design Blueprint"
    )
    header_subtitle = "Designed by Ayor"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=54,
        title="Design Blueprint Documentation",
        author="LangGraph App Builder",
    )
    doc.build(
        story,
        onFirstPage=lambda canvas, document: _draw_first_page_header(
            canvas, document, header_text, header_subtitle
        ),
    )
