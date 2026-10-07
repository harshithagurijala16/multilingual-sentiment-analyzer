from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Product, Review
from app.auth import get_current_user
from src.nlp.keywords import extract_top_keywords

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/summary")
def get_summary(
    product_id: Optional[int] = Query(None),
    language: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Review).filter(Review.user_id == current_user.id)
    if product_id:
        query = query.filter(Review.product_id == product_id)
    if language and language.lower() != "all":
        query = query.filter(Review.language.ilike(language))

    reviews = query.all()
    total = len(reviews)
    if total == 0:
        return {
            "total_reviews": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 0.0,
            "average_confidence": 0.0,
            "nps_score": 0.0,
            "total_languages": 0,
            "total_products": 0
        }

    pos = sum(1 for r in reviews if r.sentiment == "Positive")
    neg = sum(1 for r in reviews if r.sentiment == "Negative")
    neu = sum(1 for r in reviews if r.sentiment == "Neutral")
    
    pos_pct = round((pos / total) * 100, 1)
    neg_pct = round((neg / total) * 100, 1)
    neu_pct = round((neu / total) * 100, 1)
    
    avg_conf = round(sum(r.confidence for r in reviews) / total, 4)
    nps = round(pos_pct - neg_pct, 1)
    
    langs = len(set(r.language for r in reviews))
    prods = len(set(r.product_id for r in reviews if r.product_id))

    return {
        "total_reviews": total,
        "positive_count": pos,
        "negative_count": neg,
        "neutral_count": neu,
        "positive_pct": pos_pct,
        "negative_pct": neg_pct,
        "neutral_pct": neu_pct,
        "average_confidence": avg_conf,
        "nps_score": nps,
        "total_languages": langs,
        "total_products": prods
    }

@router.get("/distribution")
def get_distribution(
    product_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Review.sentiment, func.count(Review.id)).filter(Review.user_id == current_user.id)
    if product_id:
        query = query.filter(Review.product_id == product_id)
    counts = dict(query.group_by(Review.sentiment).all())
    total = sum(counts.values()) or 1

    return [
        {"sentiment": "Positive", "count": counts.get("Positive", 0), "percentage": round(counts.get("Positive", 0)/total * 100, 1), "color": "#10B981"},
        {"sentiment": "Negative", "count": counts.get("Negative", 0), "percentage": round(counts.get("Negative", 0)/total * 100, 1), "color": "#EF4444"},
        {"sentiment": "Neutral", "count": counts.get("Neutral", 0), "percentage": round(counts.get("Neutral", 0)/total * 100, 1), "color": "#64748B"}
    ]

@router.get("/by-language")
def get_by_language(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reviews = db.query(Review.language, Review.sentiment).filter(Review.user_id == current_user.id).all()
    lang_map = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})
    for lang, sent in reviews:
        lang_map[lang][sent.lower()] += 1
        lang_map[lang]["total"] += 1

    result = []
    for lang, data in sorted(lang_map.items(), key=lambda x: x[1]["total"], reverse=True):
        result.append({
            "language": lang,
            "positive": data["positive"],
            "negative": data["negative"],
            "neutral": data["neutral"],
            "total": data["total"]
        })
    return result

@router.get("/by-product")
def get_by_product(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(Product.user_id == current_user.id).all()
    result = []
    for p in products:
        p_revs = [r for r in p.reviews]
        total = len(p_revs)
        if total == 0:
            continue
        pos = sum(1 for r in p_revs if r.sentiment == "Positive")
        neg = sum(1 for r in p_revs if r.sentiment == "Negative")
        neu = sum(1 for r in p_revs if r.sentiment == "Neutral")
        pos_pct = round((pos / total) * 100, 1)
        result.append({
            "product_id": p.id,
            "product_name": p.name,
            "category": p.category,
            "total_reviews": total,
            "positive": pos,
            "negative": neg,
            "neutral": neu,
            "positive_pct": pos_pct,
            "nps_score": round(pos_pct - (neg/total * 100), 1)
        })
    result.sort(key=lambda x: x["total_reviews"], reverse=True)
    return result

@router.get("/trend")
def get_trend(
    interval: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reviews = db.query(Review).filter(Review.user_id == current_user.id).order_by(Review.review_date.asc()).all()
    trend_map = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})

    for r in reviews:
        dt = r.review_date
        if not dt:
            continue
        if interval == "monthly":
            key = dt.strftime("%Y-%m")
        elif interval == "weekly":
            key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
        else:
            key = dt.strftime("%Y-%m-%d")

        trend_map[key][r.sentiment.lower()] += 1
        trend_map[key]["total"] += 1

    result = []
    for date_key, counts in sorted(trend_map.items()):
        result.append({
            "date": date_key,
            "positive": counts["positive"],
            "negative": counts["negative"],
            "neutral": counts["neutral"],
            "total": counts["total"]
        })
    return result

@router.get("/keywords")
def get_keywords(
    language: Optional[str] = Query("English"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Review).filter(Review.user_id == current_user.id)
    if language and language.lower() != "all":
        query = query.filter(Review.language.ilike(language))
    reviews = query.all()

    rev_dicts = [
        {"original_text": r.original_text, "language": r.language, "sentiment": r.sentiment}
        for r in reviews
    ]
    return extract_top_keywords(rev_dicts, language=language or "English", top_k=10)

@router.get("/aspects")
def get_aspects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reviews = db.query(Review).filter(Review.user_id == current_user.id).all()
    aspect_stats = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})

    for r in reviews:
        aspects_list = r.get_aspects_list()
        for asp in aspects_list:
            aspect_stats[asp][r.sentiment.lower()] += 1
            aspect_stats[asp]["total"] += 1

    result = []
    for asp, counts in sorted(aspect_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        total = counts["total"]
        pos_pct = round((counts["positive"] / total) * 100, 1) if total > 0 else 0.0
        neg_pct = round((counts["negative"] / total) * 100, 1) if total > 0 else 0.0
        result.append({
            "aspect": asp,
            "positive": counts["positive"],
            "negative": counts["negative"],
            "neutral": counts["neutral"],
            "total": total,
            "positive_pct": pos_pct,
            "negative_pct": neg_pct
        })
    return result

@router.get("/low-confidence")
def get_low_confidence(
    threshold: float = Query(0.60, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reviews = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.confidence < threshold
    ).order_by(Review.confidence.asc()).limit(20).all()

    return [
        {
            "id": r.id,
            "original_text": r.original_text,
            "language": r.language,
            "is_romanized": r.is_romanized,
            "transliterated_text": r.transliterated_text,
            "sentiment": r.sentiment,
            "confidence": r.confidence,
            "corrected_label": r.corrected_label,
            "review_date": r.review_date
        }
        for r in reviews
    ]

@router.get("/insights")
def get_insights(
    product_id: Optional[int] = Query(None),
    language: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.api.reports import generate_insights_list
    query = db.query(Review).filter(Review.user_id == current_user.id)
    if product_id:
        query = query.filter(Review.product_id == product_id)
    if language and language.lower() != "all":
        query = query.filter(Review.language.ilike(language))
    reviews = query.all()
    return {"insights": generate_insights_list(reviews), "total_reviews": len(reviews)}
