import io
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.database import get_db
from app.models import User, Product, Review
from app.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Reports"])

def generate_insights_list(reviews: list[Review]) -> list[str]:
    """Generates plain-language executive insights from the review dataset."""
    if not reviews:
        return ["No review data available to generate insights."]

    total = len(reviews)
    pos = sum(1 for r in reviews if r.sentiment == "Positive")
    neg = sum(1 for r in reviews if r.sentiment == "Negative")
    neu = sum(1 for r in reviews if r.sentiment == "Neutral")
    pos_pct = round((pos / total) * 100, 1)
    neg_pct = round((neg / total) * 100, 1)
    nps = round(pos_pct - neg_pct, 1)

    insights = []

    # Overall sentiment health
    if nps >= 40:
        insights.append(f"Strong Customer Satisfaction: Net Sentiment Score is +{nps} with {pos_pct}% positive feedback.")
    elif nps >= 10:
        insights.append(f"Moderate Customer Satisfaction: Net Sentiment Score is +{nps}; {neg_pct}% of customers reported issues.")
    else:
        insights.append(f"Customer Attention Required: Net Sentiment Score is low ({nps}) with {neg_pct}% negative feedback.")

    # Multilingual & Romanization coverage
    lang_counts = {}
    romanized_count = 0
    for r in reviews:
        lang_counts[r.language] = lang_counts.get(r.language, 0) + 1
        if r.is_romanized:
            romanized_count += 1

    top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
    top_langs_str = ", ".join([f"{k} ({round(v/total*100)}%)" for k, v in top_langs[:3]])
    insights.append(f"Language Diversity: Top feedback languages are {top_langs_str}.")

    rom_pct = round((romanized_count / total) * 100, 1)
    if rom_pct > 0:
        insights.append(f"Romanized / Code-Mixed Text: {rom_pct}% ({romanized_count}/{total}) of reviews were written in Roman script or code-mixed.")

    # Aspect analytics
    aspect_counts = {}
    for r in reviews:
        for asp in r.get_aspects_list():
            if asp not in aspect_counts:
                aspect_counts[asp] = {"pos": 0, "neg": 0, "total": 0}
            aspect_counts[asp]["total"] += 1
            if r.sentiment == "Positive":
                aspect_counts[asp]["pos"] += 1
            elif r.sentiment == "Negative":
                aspect_counts[asp]["neg"] += 1

    if aspect_counts:
        # Best aspect
        best_aspect = max(
            aspect_counts.items(),
            key=lambda x: (x[1]["pos"] / x[1]["total"] if x[1]["total"] > 0 else 0)
        )
        best_rate = round(best_aspect[1]["pos"] / best_aspect[1]["total"] * 100, 1)
        insights.append(f"Primary Strength: Customer praise centers heavily on '{best_aspect[0]}' with {best_rate}% positive sentiment.")

        # Most problematic aspect
        worst_aspect = max(
            aspect_counts.items(),
            key=lambda x: (x[1]["neg"] / x[1]["total"] if x[1]["total"] > 0 else 0)
        )
        worst_rate = round(worst_aspect[1]["neg"] / worst_aspect[1]["total"] * 100, 1)
        if worst_rate > 20:
            insights.append(f"Key Friction Point: '{worst_aspect[0]}' is the leading driver of negative sentiment ({worst_rate}% negative rate).")

    # Low confidence alerts
    low_conf_count = sum(1 for r in reviews if r.confidence < 0.60)
    if low_conf_count > 0:
        insights.append(f"Human-in-the-Loop Queue: {low_conf_count} reviews have model confidence under 60% and are recommended for verification.")

    return insights


@router.get("/pdf")
def export_pdf_report(
    product_id: Optional[int] = Query(None),
    language: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Review).filter(Review.user_id == current_user.id)
    if product_id:
        query = query.filter(Review.product_id == product_id)
    if language and language.lower() != "all":
        query = query.filter(Review.language.ilike(language))

    reviews = query.all()
    if not reviews:
        raise HTTPException(status_code=400, detail="No reviews found matching the selected filters.")

    total = len(reviews)
    pos = sum(1 for r in reviews if r.sentiment == "Positive")
    neg = sum(1 for r in reviews if r.sentiment == "Negative")
    neu = sum(1 for r in reviews if r.sentiment == "Neutral")
    pos_pct = round((pos / total) * 100, 1)
    neg_pct = round((neg / total) * 100, 1)
    neu_pct = round((neu / total) * 100, 1)
    avg_conf = round(sum(r.confidence for r in reviews) / total, 4)
    nps = round(pos_pct - neg_pct, 1)

    product_name = "All Products"
    if product_id:
        prod = db.query(Product).filter(Product.id == product_id).first()
        if prod:
            product_name = prod.name

    # Build PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#4F46E5")  # Indigo
    dark_color = colors.HexColor("#1E293B")     # Slate 800
    gray_color = colors.HexColor("#64748B")     # Slate 500
    light_bg = colors.HexColor("#F8FAFC")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=gray_color,
    )
    h2_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=dark_color,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "NormalBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=dark_color,
    )
    insight_style = ParagraphStyle(
        "InsightItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=dark_color,
        bulletFontName="Helvetica",
        bulletFontSize=9,
        leftIndent=15,
        spaceAfter=4,
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Multilingual Sentiment & Feedback Analytics", title_style))
    meta_line = f"Generated for: <b>{current_user.org_name or current_user.email}</b> | Scope: <b>{product_name}</b> | Filter: <b>{language or 'All Languages'}</b> | Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}"
    story.append(Paragraph(meta_line, subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=14))

    # KPI Summary Cards Table
    story.append(Paragraph("Executive Performance Metrics", h2_style))
    kpi_data = [
        ["Total Reviews", "Positive", "Negative", "Neutral", "Avg Confidence", "Net Sentiment (NPS)"],
        [
            str(total),
            f"{pos} ({pos_pct}%)",
            f"{neg} ({neg_pct}%)",
            f"{neu} ({neu_pct}%)",
            f"{round(avg_conf * 100, 1)}%",
            f"{'+' if nps >= 0 else ''}{nps}",
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[85, 85, 85, 85, 95, 95])
    kpi_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 1), (-1, 1), light_bg),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 10),
            ("TEXTCOLOR", (0, 1), (-1, 1), dark_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Automated Key Insights
    story.append(Paragraph("Strategic Actionable Insights", h2_style))
    insights = generate_insights_list(reviews)
    for insight in insights:
        story.append(Paragraph(f"• {insight}", insight_style))
    story.append(Spacer(1, 14))

    # Language Breakdown Table
    story.append(Paragraph("Sentiment Breakdown by Language", h2_style))
    lang_map = {}
    for r in reviews:
        if r.language not in lang_map:
            lang_map[r.language] = {"pos": 0, "neg": 0, "neu": 0, "total": 0}
        lang_map[r.language]["total"] += 1
        if r.sentiment == "Positive":
            lang_map[r.language]["pos"] += 1
        elif r.sentiment == "Negative":
            lang_map[r.language]["neg"] += 1
        else:
            lang_map[r.language]["neu"] += 1

    lang_rows = [["Language", "Reviews", "Positive", "Negative", "Neutral", "Satisfaction Rate"]]
    for lang, counts in sorted(lang_map.items(), key=lambda x: x[1]["total"], reverse=True):
        ltotal = counts["total"]
        pos_rate = round(counts["pos"] / ltotal * 100, 1) if ltotal > 0 else 0
        lang_rows.append([
            lang,
            str(ltotal),
            str(counts["pos"]),
            str(counts["neg"]),
            str(counts["neu"]),
            f"{pos_rate}%",
        ])

    lang_table = Table(lang_rows, colWidths=[120, 80, 80, 80, 80, 105])
    lang_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#94A3B8")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(lang_table)
    story.append(Spacer(1, 14))

    # Aspect Sentiment Breakdown Table
    story.append(Paragraph("Customer Aspect Sentiment Matrix", h2_style))
    aspect_map = {}
    for r in reviews:
        for asp in r.get_aspects_list():
            if asp not in aspect_map:
                aspect_map[asp] = {"pos": 0, "neg": 0, "neu": 0, "total": 0}
            aspect_map[asp]["total"] += 1
            if r.sentiment == "Positive":
                aspect_map[asp]["pos"] += 1
            elif r.sentiment == "Negative":
                aspect_map[asp]["neg"] += 1
            else:
                aspect_map[asp]["neu"] += 1

    aspect_rows = [["Aspect", "Mentions", "Positive %", "Negative %", "Neutral %", "Verdict"]]
    for asp, counts in sorted(aspect_map.items(), key=lambda x: x[1]["total"], reverse=True):
        atotal = counts["total"]
        ap_pct = round(counts["pos"] / atotal * 100, 1) if atotal > 0 else 0
        an_pct = round(counts["neg"] / atotal * 100, 1) if atotal > 0 else 0
        aneu_pct = round(counts["neu"] / atotal * 100, 1) if atotal > 0 else 0
        verdict = "Positive Driver" if ap_pct >= 60 else ("Friction Area" if an_pct >= 30 else "Balanced")
        aspect_rows.append([
            asp.capitalize(),
            str(atotal),
            f"{ap_pct}%",
            f"{an_pct}%",
            f"{aneu_pct}%",
            verdict,
        ])

    if len(aspect_rows) > 1:
        aspect_table = Table(aspect_rows, colWidths=[120, 80, 80, 80, 80, 105])
        aspect_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#94A3B8")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(aspect_table)

    story.append(Spacer(1, 16))
    footer_text = f"Report generated autonomously by Multilingual Sentiment Analytics Engine (XLM-RoBERTa + Indic-Transliteration)."
    story.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=8, textColor=gray_color, alignment=1)))

    # Build the document
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"sentiment_analytics_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
