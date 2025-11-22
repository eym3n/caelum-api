from __future__ import annotations
from pathlib import Path
from typing import List

from markdown_it import MarkdownIt
from markdown_it.token import Token
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


HEADER_HEIGHT = 1.6 * inch

_md = MarkdownIt()


def _escape_text(value: str) -> str:
    """Escape HTML special chars for ReportLab paragraphs."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_inline(inline_token: Token) -> str:
    """Render inline markdown token stream into minimal HTML supported by ReportLab."""
    if inline_token.children is None:
        return _escape_text(inline_token.content)

    chunks: List[str] = []
    for child in inline_token.children:
        if child.type == "text":
            chunks.append(_escape_text(child.content))
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
            chunks.append(_escape_text(child.content))
    text = "".join(chunks).strip()
    return text if text else _escape_text(inline_token.content)


def _list_flowable(
    items: List[str],
    *,
    bullet_type: str,
    start: int = 1,
    body_style: ParagraphStyle,
) -> ListFlowable:
    list_items = [ListItem(Paragraph(item, body_style), leftIndent=0) for item in items]
    return ListFlowable(
        list_items,
        bulletType=bullet_type,
        start=start if bullet_type == "1" else None,
        bulletFontName=body_style.fontName,
        bulletFontSize=body_style.fontSize,
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
    title_font = "Times-Bold"
    title_size = 26
    usable_width = width - (doc.leftMargin + doc.rightMargin)
    while (
        canvas.stringWidth(title, title_font, title_size) > usable_width
        and title_size > 16
    ):
        title_size -= 1
    title_y = top - (header_height / 2) + 12
    title_x = (width - canvas.stringWidth(title, title_font, title_size)) / 2
    canvas.setFont(title_font, title_size)
    canvas.drawString(title_x, title_y, title)

    subtitle_font = "Times-Roman"
    subtitle_size = 12
    subtitle_width = canvas.stringWidth(subtitle, subtitle_font, subtitle_size)
    subtitle_x = (width - subtitle_width) / 2
    subtitle_y = title_y - 24
    canvas.setFont(subtitle_font, subtitle_size)
    canvas.drawString(subtitle_x, subtitle_y, subtitle)

    canvas.restoreState()


def markdown_to_pdf(
    markdown_text: str, output_path: Path, *, header_title: str | None = None
) -> None:
    """
    Convert Markdown content into a styled PDF document.

    Supports headings, paragraphs, bullet lists, numbered lists, emphasis, and inline code.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    story = []
    styles = getSampleStyleSheet()

    heading_styles = {
        1: ParagraphStyle(
            "Heading1",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=20,
            leading=26,
            spaceAfter=12,
            textColor=colors.HexColor("#111111"),
        ),
        2: ParagraphStyle(
            "Heading2",
            parent=styles["Heading2"],
            fontName="Times-Bold",
            fontSize=16,
            leading=22,
            spaceBefore=6,
            spaceAfter=10,
            textColor=colors.HexColor("#222222"),
        ),
        3: ParagraphStyle(
            "Heading3",
            parent=styles["Heading3"],
            fontName="Times-Bold",
            fontSize=14,
            leading=20,
            spaceBefore=4,
            spaceAfter=8,
            textColor=colors.HexColor("#333333"),
        ),
    }

    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=11,
        leading=15,
        spaceAfter=6,
        textColor=colors.HexColor("#2f2f2f"),
    )

    tokens = _md.parse(markdown_text)
    list_stack: List[dict[str, str | int | List[str]]] = []

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
            text = _render_inline(inline_token)
            style = heading_styles.get(level, heading_styles[3])
            story.append(Paragraph(text, style))
            story.append(Spacer(1, 6 if level >= 3 else 12))
            i += 3  # skip inline + close
            continue

        if token.type == "paragraph_open":
            inline_token = tokens[i + 1]
            text = _render_inline(inline_token)
            if text:
                story.append(Paragraph(text, body_style))
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
            j = i + 1
            while j < len(tokens) and tokens[j].type != "list_item_close":
                if tokens[j].type == "inline":
                    inline_fragments.append(_render_inline(tokens[j]))
                j += 1
            sentence = " ".join(
                fragment.strip() for fragment in inline_fragments if fragment.strip()
            )
            if list_stack and sentence:
                list_stack[-1]["items"].append(sentence)
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
