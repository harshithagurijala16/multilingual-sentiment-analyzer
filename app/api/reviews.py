import io
import json
from datetime import datetime, timezone
from typing import Optional, List
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import User, Product, Review
from app.auth import get_current_user
from app.schemas import (
    ReviewAnalyzeRequest,
    ReviewAnalyzeResponse,
    ReviewOut,
    ReviewListResponse,
    ReviewCorrectRequest,
    BulkUploadResponse
)
from src.nlp.pipeline import analyze_review, analyze_batch

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])

@router.post("/analyze", response_model=ReviewAnalyzeResponse)
def analyze_single_review(
    payload: ReviewAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analysis = analyze_review(payload.review)
    product_id = payload.product_id
    product_name = None

    if payload.product_name and not product_id:
        p = db.query(Product).filter(
            Product.user_id == current_user.id,
            Product.name == payload.product_name.strip()
        ).first()
        if not p:
            p = Product(user_id=current_user.id, name=payload.product_name.strip())
            db.add(p)
            db.commit()
            db.refresh(p)
        product_id = p.id
        product_name = p.name
    elif product_id:
        p = db.query(Product).filter(Product.id == product_id, Product.user_id == current_user.id).first()
        if p:
            product_name = p.name

    saved_id = None
    review_date = datetime.now(timezone.utc)
    if payload.save:
        rev = Review(
            user_id=current_user.id,
            product_id=product_id,
            original_text=analysis["original_text"],
            language=analysis["language"],
            script=analysis["script"],
            is_romanized=analysis["is_romanized"],
            transliterated_text=analysis["transliterated_text"],
            sentiment=analysis["sentiment"],
            confidence=analysis["confidence"],
            prob_pos=analysis["prob_pos"],
            prob_neg=analysis["prob_neg"],
            prob_neu=analysis["prob_neu"],
            aspects=json.dumps(analysis["aspects"]),
            source=payload.source,
            review_date=review_date,
            created_at=review_date
        )
        db.add(rev)
        db.commit()
        db.refresh(rev)
        saved_id = rev.id

    return ReviewAnalyzeResponse(
        id=saved_id,
        saved_id=saved_id,
        original_text=analysis["original_text"],
        language=analysis["language"],
        script=analysis["script"],
        is_romanized=analysis["is_romanized"],
        is_code_mixed=analysis["is_code_mixed"],
        transliterated_text=analysis["transliterated_text"],
        sentiment=analysis["sentiment"],
        confidence=analysis["confidence"],
        prob_pos=analysis["prob_pos"],
        prob_neg=analysis["prob_neg"],
        prob_neu=analysis["prob_neu"],
        low_confidence=analysis["low_confidence"],
        aspects=analysis["aspects"],
        product_name=product_name,
        review_date=review_date
    )

@router.post("/bulk", response_model=BulkUploadResponse)
def bulk_upload_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        content = file.file.read()
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    # Check for review column (case-insensitive)
    review_col = next((c for c in df.columns if c.strip().lower() in ["review", "text", "review_text", "comment"]), None)
    if not review_col:
        raise HTTPException(status_code=400, detail=f"Missing 'review' column. Found: {list(df.columns)}")

    product_col = next((c for c in df.columns if c.strip().lower() in ["product", "product_name"]), None)
    date_col = next((c for c in df.columns if c.strip().lower() in ["date", "review_date", "created_at"]), None)
    source_col = next((c for c in df.columns if c.strip().lower() == "source"), None)

    valid_rows = []
    skipped_rows = []

    for idx, row in df.iterrows():
        raw_text = str(row[review_col]).strip() if pd.notna(row[review_col]) else ""
        if not raw_text or len(raw_text) < 2:
            skipped_rows.append({"row_number": idx + 2, "reason": "Empty or too short review text"})
            continue

        prod_name = str(row[product_col]).strip() if product_col and pd.notna(row[product_col]) else None
        
        parsed_date = datetime.now(timezone.utc)
        if date_col and pd.notna(row[date_col]):
            try:
                parsed_date = pd.to_datetime(row[date_col]).to_pydatetime()
            except Exception:
                pass

        src_val = str(row[source_col]).strip() if source_col and pd.notna(row[source_col]) else "bulk_upload"

        valid_rows.append({
            "text": raw_text,
            "product_name": prod_name,
            "date": parsed_date,
            "source": src_val
        })

    if not valid_rows:
        return BulkUploadResponse(
            total_processed=len(df),
            saved_count=0,
            skipped_count=len(skipped_rows),
            skipped_rows=skipped_rows,
            sentiment_counts={"Positive": 0, "Negative": 0, "Neutral": 0},
            language_counts={},
            average_confidence=0.0
        )

    # Batch NLP analysis
    texts = [r["text"] for r in valid_rows]
    analyses = analyze_batch(texts)

    # Cache products
    product_cache = {}
    db_reviews = []
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    language_counts = {}
    conf_sum = 0.0

    for i, a in enumerate(analyses):
        r_meta = valid_rows[i]
        p_name = r_meta["product_name"]
        p_id = None
        if p_name:
            if p_name not in product_cache:
                p = db.query(Product).filter(Product.user_id == current_user.id, Product.name == p_name).first()
                if not p:
                    p = Product(user_id=current_user.id, name=p_name)
                    db.add(p)
                    db.commit()
                    db.refresh(p)
                product_cache[p_name] = p.id
            p_id = product_cache[p_name]

        sent = a["sentiment"]
        lang = a["language"]
        sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1
        language_counts[lang] = language_counts.get(lang, 0) + 1
        conf_sum += a["confidence"]

        db_rev = Review(
            user_id=current_user.id,
            product_id=p_id,
            original_text=a["original_text"],
            language=a["language"],
            script=a["script"],
            is_romanized=a["is_romanized"],
            transliterated_text=a["transliterated_text"],
            sentiment=sent,
            confidence=a["confidence"],
            prob_pos=a["prob_pos"],
            prob_neg=a["prob_neg"],
            prob_neu=a["prob_neu"],
            aspects=json.dumps(a["aspects"]),
            source=r_meta["source"],
            review_date=r_meta["date"],
            created_at=datetime.now(timezone.utc)
        )
        db_reviews.append(db_rev)

    db.add_all(db_reviews)
    db.commit()

    avg_conf = round(conf_sum / len(analyses), 4) if analyses else 0.0

    return BulkUploadResponse(
        total_processed=len(df),
        total_rows=len(df),
        saved_count=len(db_reviews),
        skipped_count=len(skipped_rows),
        skipped_rows=skipped_rows,
        sentiment_counts=sentiment_counts,
        language_counts=language_counts,
        average_confidence=avg_conf
    )

@router.get("", response_model=ReviewListResponse)
def list_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    language: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sort_by: str = Query("review_date"),
    order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Review).filter(Review.user_id == current_user.id)

    if language and language.lower() != "all":
        query = query.filter(Review.language.ilike(language))
    if sentiment and sentiment.lower() != "all":
        query = query.filter(Review.sentiment.ilike(sentiment))
    if product_id:
        query = query.filter(Review.product_id == product_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(Review.original_text.ilike(s) | Review.transliterated_text.ilike(s))
    if start_date:
        try:
            dt = datetime.fromisoformat(start_date)
            query = query.filter(Review.review_date >= dt)
        except Exception:
            pass
    if end_date:
        try:
            dt = datetime.fromisoformat(end_date)
            query = query.filter(Review.review_date <= dt)
        except Exception:
            pass

    total = query.count()

    order_col = getattr(Review, sort_by, Review.review_date)
    if order.lower() == "desc":
        query = query.order_by(desc(order_col))
    else:
        query = query.order_by(order_col)

    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    formatted = []
    for item in items:
        p_name = item.product.name if item.product else None
        formatted.append(ReviewOut(
            id=item.id,
            product_id=item.product_id,
            product_name=p_name,
            original_text=item.original_text,
            language=item.language,
            script=item.script,
            is_romanized=item.is_romanized,
            transliterated_text=item.transliterated_text,
            sentiment=item.sentiment,
            confidence=item.confidence,
            prob_pos=item.prob_pos,
            prob_neg=item.prob_neg,
            prob_neu=item.prob_neu,
            aspects=item.get_aspects_list(),
            source=item.source,
            review_date=item.review_date,
            created_at=item.created_at,
            corrected_label=item.corrected_label
        ))

    return ReviewListResponse(total=total, page=page, limit=limit, reviews=formatted)

@router.get("/products")
def list_user_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(Product.user_id == current_user.id).all()
    return [{"id": p.id, "name": p.name, "category": p.category} for p in products]

@router.get("/template")
def download_csv_template():
    csv_content = (
        "review,product,date,source\n"
        "\"Camera quality chala bagundi, battery backup superb\",Echo Dot 5th Gen,2026-03-15,Website\n"
        "\"Romba mosamana delivery experience, product damaged\",OnePlus 12 5G,2026-03-18,Amazon\n"
        "\"Bahut achhi service hai, packing bhi zabardast\",Boat Rockerz 450,2026-03-20,Flipkart\n"
        "\"Chennagide aadre delivery late aayithu\",Echo Dot 5th Gen,2026-03-22,Store\n"
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="reviews_template.csv"'}
    )

@router.get("/export")
def export_reviews_csv(
    language: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Review).filter(Review.user_id == current_user.id)
    if language and language.lower() != "all":
        query = query.filter(Review.language.ilike(language))
    if sentiment and sentiment.lower() != "all":
        query = query.filter(Review.sentiment.ilike(sentiment))
    if product_id:
        query = query.filter(Review.product_id == product_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(Review.original_text.ilike(s) | Review.transliterated_text.ilike(s))
    if start_date:
        try:
            dt = datetime.fromisoformat(start_date)
            query = query.filter(Review.review_date >= dt)
        except Exception:
            pass
    if end_date:
        try:
            dt = datetime.fromisoformat(end_date)
            query = query.filter(Review.review_date <= dt)
        except Exception:
            pass

    reviews = query.order_by(desc(Review.review_date)).all()
    rows = []
    for r in reviews:
        p_name = r.product.name if r.product else ""
        rows.append({
            "id": r.id,
            "product": p_name,
            "original_text": r.original_text,
            "language": r.language,
            "script": r.script,
            "is_romanized": r.is_romanized,
            "transliterated_text": r.transliterated_text,
            "sentiment": r.sentiment,
            "confidence": round(r.confidence, 4),
            "prob_positive": round(r.prob_pos, 4),
            "prob_negative": round(r.prob_neg, 4),
            "prob_neutral": round(r.prob_neu, 4),
            "aspects": ", ".join(r.get_aspects_list()),
            "corrected_label": r.corrected_label or "",
            "review_date": r.review_date.strftime("%Y-%m-%d %H:%M:%S") if r.review_date else "",
            "source": r.source or ""
        })

    df = pd.DataFrame(rows)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    csv_data = stream.getvalue()

    filename = f"reviews_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.put("/{review_id}/correct", response_model=ReviewOut)
def correct_review_label(
    review_id: int,
    payload: ReviewCorrectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rev = db.query(Review).filter(Review.id == review_id, Review.user_id == current_user.id).first()
    if not rev:
        raise HTTPException(status_code=404, detail="Review not found.")

    rev.corrected_label = payload.corrected_label
    db.commit()
    db.refresh(rev)

    p_name = rev.product.name if rev.product else None
    return ReviewOut(
        id=rev.id,
        product_id=rev.product_id,
        product_name=p_name,
        original_text=rev.original_text,
        language=rev.language,
        script=rev.script,
        is_romanized=rev.is_romanized,
        transliterated_text=rev.transliterated_text,
        sentiment=rev.sentiment,
        confidence=rev.confidence,
        prob_pos=rev.prob_pos,
        prob_neg=rev.prob_neg,
        prob_neu=rev.prob_neu,
        aspects=rev.get_aspects_list(),
        source=rev.source,
        review_date=rev.review_date,
        created_at=rev.created_at,
        corrected_label=rev.corrected_label
    )

@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rev = db.query(Review).filter(Review.id == review_id, Review.user_id == current_user.id).first()
    if not rev:
        raise HTTPException(status_code=404, detail="Review not found.")

    db.delete(rev)
    db.commit()
    return None
