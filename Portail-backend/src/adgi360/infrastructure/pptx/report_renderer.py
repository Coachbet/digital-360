"""Génération du rapport PowerPoint aux couleurs adgi360.

Le contenu (titres, chiffres, commentaires) est rédigé par l'IA locale via n8n ;
ce module ne s'occupe que de la mise en forme. Cette séparation permet de
retravailler le design sans toucher au prompt, et inversement.

python-pptx plutôt qu'une bibliothèque Node : le backend est déjà en Python et
n'a ainsi aucune dépendance supplémentaire à installer.
"""

import io
from dataclasses import dataclass, field
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# Charte adgi360
MAGENTA = RGBColor(0xFF, 0x3D, 0x95)
INK = RGBColor(0x1A, 0x1A, 0x3C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x6B, 0x72, 0x80)
SOFT = RGBColor(0xFD, 0xF0, 0xF6)
LIGHT = RGBColor(0xF7, 0xF7, 0xF9)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.7)
CONTENT_W = SLIDE_W - 2 * MARGIN

TITLE_FONT = "Arial"
BODY_FONT = "Arial"


@dataclass
class Kpi:
    label: str
    value: str
    delta: str | None = None


@dataclass
class SlideSpec:
    """Une diapositive telle que décrite par l'IA.

    `layout` choisit la mise en page ; une valeur inconnue retombe sur « bullets »
    pour qu'un écart du modèle ne fasse jamais échouer la génération.
    """

    title: str
    layout: str = "bullets"
    subtitle: str | None = None
    bullets: list[str] = field(default_factory=list)
    kpis: list[Kpi] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    series: list[dict] = field(default_factory=list)
    notes: str | None = None


@dataclass
class DeckSpec:
    title: str
    subtitle: str | None = None
    client_name: str = ""
    period: str = ""
    slides: list[SlideSpec] = field(default_factory=list)


# --------------------------------------------------------------------- helpers


def _blank(prs: Presentation):
    """Layout 6 = vierge : on place tout nous-mêmes, aucun placeholder hérité."""
    return prs.slides.add_slide(prs.slide_layouts[min(6, len(prs.slide_layouts) - 1)])


def _fill(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _text(
    slide,
    text: str,
    left,
    top,
    width,
    height,
    size: int,
    color: RGBColor = INK,
    bold: bool = False,
    font: str = BODY_FONT,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    line_spacing: float = 1.1,
):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    # Sans cette remise à zéro, le texte ne s'aligne pas avec les formes voisines.
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0

    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.line_spacing = line_spacing
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    return box


def _wordmark(slide, left, top, size: int = 20) -> None:
    """Logo typographique. Les deux mots vivent dans le même cadre : leur
    espacement suit la police au lieu d'un décalage codé en dur."""
    box = slide.shapes.add_textbox(left, top, Inches(3), Inches(0.5))
    frame = box.text_frame
    # word_wrap explicite : sans lui python-pptx écrit wrap="none" + spAutoFit,
    # et le rendu recentre la forme autour de son point d'ancrage — le logo
    # se retrouve décalé par rapport au titre en dessous.
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.LEFT
    for text, color in (("ADIGI", WHITE), ("360", MAGENTA)):
        run = paragraph.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = True
        run.font.color.rgb = color
        run.font.name = TITLE_FONT


def _brand_logo(prs: Presentation, slide, left, top, width=Inches(2.0)) -> None:
    logo_bytes = getattr(prs, "_adgi360_logo_bytes", None)
    if not logo_bytes:
        default_logo = Path(__file__).with_name("assets") / "adigi360-logo-white.png"
        if default_logo.exists():
            logo_bytes = default_logo.read_bytes()
    if logo_bytes:
        try:
            slide.shapes.add_picture(io.BytesIO(logo_bytes), left, top, width=width)
            return
        except Exception:
            pass
    _wordmark(slide, left, top)


def _bullet_list(
    slide,
    bullets: list[str],
    left,
    top,
    width,
    size: int = 16,
    text_color: RGBColor = INK,
    dot_color: RGBColor = MAGENTA,
):
    """Puces dessinées à la main : un petit disque magenta + le texte.

    Les puces natives de PowerPoint héritent du thème et rendent mal quand on
    part d'un layout vierge ; ce rendu manuel garantit un résultat identique
    partout.
    """
    y = top
    row_h = Inches(0.52)
    for bullet in bullets:
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, left, y + Inches(0.09), Inches(0.11), Inches(0.11)
        )
        _fill(dot, dot_color)
        box = _text(
            slide,
            bullet,
            left + Inches(0.3),
            y,
            width - Inches(0.3),
            row_h,
            size,
            text_color,
        )
        # Une puce longue passe sur deux lignes : on décale la suivante d'autant.
        lines = max(1, len(bullet) // 72 + 1)
        y += Emu(int(row_h * (0.62 + 0.38 * lines)))
    return y


# ---------------------------------------------------------------------- slides


def _title_slide(prs: Presentation, deck: DeckSpec) -> None:
    """Ouverture sombre : contraste fort avec les pages de contenu claires."""
    slide = _blank(prs)
    background = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    _fill(background, INK)

    # Cercle magenta débordant du bord droit, motif repris sur la page de fin.
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, SLIDE_W - Inches(2.6), -Inches(1.6), Inches(5.2), Inches(5.2)
    )
    _fill(circle, MAGENTA)

    _brand_logo(prs, slide, MARGIN, Inches(0.58), Inches(2.15))

    _text(
        slide, deck.title, MARGIN, Inches(3.0), Inches(8.6), Inches(2.0),
        40, WHITE, True, TITLE_FONT, line_spacing=1.05,
    )
    if deck.subtitle:
        _text(
            slide, deck.subtitle, MARGIN, Inches(5.1), Inches(8.6), Inches(0.9),
            17, RGBColor(0xC9, 0xCD, 0xD6),
        )

    footer = " · ".join(part for part in [deck.client_name, deck.period] if part)
    if footer:
        _text(slide, footer, MARGIN, Inches(6.5), Inches(8), Inches(0.4), 13, MAGENTA, True)


def _kpi_slide(prs: Presentation, spec: SlideSpec) -> None:
    """Chiffres clés en grandes cartes — le format le plus lisible pour des stats."""
    slide = _blank(prs)
    _text(slide, spec.title, MARGIN, Inches(0.7), CONTENT_W, Inches(0.9), 32, INK, True, TITLE_FONT)
    if spec.subtitle:
        _text(slide, spec.subtitle, MARGIN, Inches(1.5), CONTENT_W, Inches(0.5), 15, MUTED)

    kpis = spec.kpis[:4]
    if not kpis:
        return
    gap = Inches(0.3)
    card_w = Emu(int((CONTENT_W - gap * (len(kpis) - 1)) / len(kpis)))
    top = Inches(2.35)
    card_h = Inches(2.4)

    for index, kpi in enumerate(kpis):
        left = MARGIN + Emu(int((card_w + gap) * index))
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, card_w, card_h)
        _fill(card, SOFT if index % 2 == 0 else LIGHT)
        card.adjustments[0] = 0.08

        _text(
            slide, kpi.value, left + Inches(0.35), top + Inches(0.5),
            card_w - Inches(0.7), Inches(1.0), 40, MAGENTA, True, TITLE_FONT,
        )
        _text(
            slide, kpi.label, left + Inches(0.35), top + Inches(1.5),
            card_w - Inches(0.7), Inches(0.6), 13, INK,
        )
        if kpi.delta:
            _text(
                slide, kpi.delta, left + Inches(0.35), top + Inches(1.95),
                card_w - Inches(0.7), Inches(0.35), 12, MUTED,
            )

    if spec.bullets:
        _bullet_list(slide, spec.bullets[:3], MARGIN, Inches(5.1), CONTENT_W, 15)


def _bullets_slide(prs: Presentation, spec: SlideSpec) -> None:
    """Deux colonnes : le texte respire, et la colonne droite porte un visuel."""
    slide = _blank(prs)
    _text(slide, spec.title, MARGIN, Inches(0.7), Inches(8.5), Inches(0.9), 32, INK, True, TITLE_FONT)
    if spec.subtitle:
        _text(slide, spec.subtitle, MARGIN, Inches(1.55), Inches(7.6), Inches(0.5), 15, MUTED)

    _bullet_list(slide, spec.bullets[:6], MARGIN, Inches(2.3), Inches(7.4), 16)

    # Bloc visuel : cercles concentriques, motif de la marque, sans texte.
    panel = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.9), Inches(2.1), Inches(3.75), Inches(3.9)
    )
    _fill(panel, SOFT)
    panel.adjustments[0] = 0.06
    outer = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(9.6), Inches(2.8), Inches(2.4), Inches(2.4))
    _fill(outer, RGBColor(0xF7, 0xC7, 0xDD))
    inner = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(10.15), Inches(3.35), Inches(1.3), Inches(1.3))
    _fill(inner, MAGENTA)


def _recommendations_slide(prs: Presentation, spec: SlideSpec) -> None:
    """Recommandations numérotées : pastille magenta + titre + détail."""
    slide = _blank(prs)
    _text(slide, spec.title, MARGIN, Inches(0.7), CONTENT_W, Inches(0.9), 32, INK, True, TITLE_FONT)
    if spec.subtitle:
        _text(slide, spec.subtitle, MARGIN, Inches(1.55), CONTENT_W, Inches(0.5), 15, MUTED)

    items = spec.items[:4]
    # Sans sous-titre, on remonte la liste pour ne pas laisser un blanc sous le titre.
    top = Inches(2.3) if spec.subtitle else Inches(1.95)
    row_h = Inches(1.25)

    for index, item in enumerate(items):
        y = top + Emu(int(row_h * index))
        badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, MARGIN, y, Inches(0.62), Inches(0.62))
        _fill(badge, MAGENTA)
        _text(
            slide, str(index + 1), MARGIN, y + Inches(0.13), Inches(0.62), Inches(0.4),
            18, WHITE, True, TITLE_FONT, PP_ALIGN.CENTER,
        )
        _text(
            slide, str(item.get("title", "")), MARGIN + Inches(0.95), y + Inches(0.02),
            CONTENT_W - Inches(0.95), Inches(0.4), 18, INK, True,
        )
        detail = str(item.get("detail", ""))
        if detail:
            _text(
                slide, detail, MARGIN + Inches(0.95), y + Inches(0.42),
                CONTENT_W - Inches(0.95), Inches(0.6), 14, MUTED,
            )


def _trend_slide(prs: Presentation, spec: SlideSpec) -> None:
    """Graphique natif, construit à partir des séries validées par n8n."""
    slide = _blank(prs)
    _text(slide, "03 • ANALYSE", MARGIN, Inches(0.38), CONTENT_W, Inches(0.3), 11, MAGENTA, True)
    _text(slide, spec.title, MARGIN, Inches(0.72), CONTENT_W, Inches(0.65), 30, INK, True, TITLE_FONT)
    chart_data = ChartData()
    chart_data.categories = spec.categories or ["Période"]
    added_series = False
    for item in spec.series[:3]:
        values = [float(v) for v in item.get("values", [])]
        if len(values) == len(chart_data.categories):
            chart_data.add_series(str(item.get("name") or "Valeur"), values)
            added_series = True
    if not added_series:
        chart_data.add_series("Valeur", [0] * len(chart_data.categories))
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.LINE_MARKERS,
        MARGIN, Inches(1.65), Inches(8.1), Inches(4.65), chart_data,
    ).chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xE4, 0xE4, 0xEB)
    for index, series in enumerate(chart.series):
        series.format.line.color.rgb = MAGENTA if index == 0 else INK
        series.format.line.width = Pt(2.5 if index == 0 else 1.5)
        series.marker.size = 7
    panel = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.25), Inches(1.65), Inches(3.35), Inches(4.65)
    )
    _fill(panel, INK)
    panel.adjustments[0] = 0.06
    _text(slide, "INTERPRÉTATION", Inches(9.65), Inches(2.05), Inches(2.55), Inches(0.3), 11, MAGENTA, True)
    _bullet_list(
        slide, spec.bullets[:4], Inches(9.58), Inches(2.65), Inches(2.55),
        13, WHITE, MAGENTA,
    )


def _table_slide(prs: Presentation, spec: SlideSpec) -> None:
    slide = _blank(prs)
    _text(slide, "04 • DÉTAIL", MARGIN, Inches(0.38), CONTENT_W, Inches(0.3), 11, MAGENTA, True)
    _text(slide, spec.title, MARGIN, Inches(0.72), CONTENT_W, Inches(0.65), 30, INK, True, TITLE_FONT)
    items = spec.items[:7]
    headers = list(items[0].keys())[:6] if items else ["Élément", "Valeur"]
    table_height = Inches(min(4.7, 0.62 * (len(items) + 1)))
    table = slide.shapes.add_table(
        len(items) + 1, len(headers), MARGIN, Inches(1.7), CONTENT_W, table_height
    ).table
    for column in range(len(headers)):
        table.columns[column].width = Emu(int(CONTENT_W / len(headers)))
    for col, header in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = str(header).replace("_", " ").upper()
        cell.fill.solid(); cell.fill.fore_color.rgb = INK
        cell.text_frame.paragraphs[0].font.color.rgb = WHITE
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.name = BODY_FONT
        cell.text_frame.paragraphs[0].font.size = Pt(10)
    for row_index, item in enumerate(items, start=1):
        for col, header in enumerate(headers):
            cell = table.cell(row_index, col)
            cell.text = str(item.get(header, ""))
            cell.fill.solid(); cell.fill.fore_color.rgb = WHITE if row_index % 2 else LIGHT
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.font.name = BODY_FONT
            paragraph.font.size = Pt(10)
            paragraph.font.color.rgb = INK
            paragraph.alignment = PP_ALIGN.LEFT if col == 0 else PP_ALIGN.CENTER
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.05)


def _closing_slide(prs: Presentation, deck: DeckSpec) -> None:
    slide = _blank(prs)
    background = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    _fill(background, INK)
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, -Inches(1.8), SLIDE_H - Inches(3.0), Inches(5.0), Inches(5.0)
    )
    _fill(circle, MAGENTA)

    _brand_logo(prs, slide, Inches(4.4), Inches(1.3), Inches(2.2))
    _text(
        slide, "Grandissons ensemble !", Inches(4.4), Inches(2.6), Inches(8.2), Inches(1.0),
        34, WHITE, True, TITLE_FONT,
    )
    _text(
        slide, "info@adigi360.com  ·  +1 514-812-2857  ·  www.adigi360.com",
        Inches(4.4), Inches(3.8), Inches(8.2), Inches(0.5), 14, RGBColor(0xC9, 0xCD, 0xD6),
    )


LAYOUTS = {
    "kpis": _kpi_slide,
    "bullets": _bullets_slide,
    "recommendations": _recommendations_slide,
    "trend": _trend_slide,
    "table": _table_slide,
}


def render_report_pptx(
    deck: DeckSpec,
    template_bytes: bytes | None = None,
    logo_bytes: bytes | None = None,
) -> bytes:
    prs = Presentation(io.BytesIO(template_bytes)) if template_bytes else Presentation()
    if template_bytes:
        # On conserve thèmes, polices et masques du gabarit, mais pas ses pages
        # d'exemple : le rapport repart d'un deck propre.
        for slide_id in list(prs.slides._sldIdLst):
            rel_id = slide_id.rId
            prs.part.drop_rel(rel_id)
            prs.slides._sldIdLst.remove(slide_id)
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    prs._adgi360_logo_bytes = logo_bytes

    _title_slide(prs, deck)

    for spec in deck.slides:
        renderer = LAYOUTS.get(spec.layout, _bullets_slide)
        # Une diapo « kpis » sans chiffre serait vide : on bascule sur les puces.
        if spec.layout == "kpis" and not spec.kpis:
            renderer = _bullets_slide
        if spec.layout == "recommendations" and not spec.items:
            renderer = _bullets_slide
        renderer(prs, spec)
        if spec.notes:
            prs.slides[-1].notes_slide.notes_text_frame.text = spec.notes

    _closing_slide(prs, deck)

    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()


def deck_from_dict(payload: dict, client_name: str = "", period: str = "") -> DeckSpec:
    """Construit un DeckSpec à partir du JSON produit par l'IA.

    Tolérant par construction : chaque champ manquant a une valeur de repli, pour
    qu'une réponse imparfaite du modèle produise quand même un rapport lisible
    plutôt qu'une erreur.
    """
    slides: list[SlideSpec] = []
    for raw in payload.get("slides", []) or []:
        if not isinstance(raw, dict):
            continue
        kpis = [
            Kpi(
                label=str(k.get("label", "")),
                value=str(k.get("value", "")),
                delta=str(k["delta"]) if k.get("delta") else None,
            )
            for k in (raw.get("kpis") or [])
            if isinstance(k, dict)
        ]
        bullets = [str(b) for b in (raw.get("bullets") or []) if str(b).strip()]
        items = [i for i in (raw.get("items") or []) if isinstance(i, dict)]
        categories = [str(v) for v in (raw.get("categories") or [])]
        series = [s for s in (raw.get("series") or []) if isinstance(s, dict)]

        slides.append(
            SlideSpec(
                title=str(raw.get("title") or "Sans titre"),
                layout=str(raw.get("layout") or "bullets"),
                subtitle=str(raw["subtitle"]) if raw.get("subtitle") else None,
                bullets=bullets,
                kpis=kpis,
                items=items,
                categories=categories,
                series=series,
                notes=str(raw["notes"]) if raw.get("notes") else None,
            )
        )

    if not slides:
        slides = [
            SlideSpec(
                title="Synthèse",
                bullets=["Aucun contenu n'a été produit pour ce rapport."],
            )
        ]

    return DeckSpec(
        title=str(payload.get("title") or f"Rapport de performance — {client_name}"),
        subtitle=str(payload["subtitle"]) if payload.get("subtitle") else None,
        client_name=client_name,
        period=period,
        slides=slides,
    )
