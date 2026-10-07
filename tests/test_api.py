import io
import pytest
from app.models import Review, Product

def test_auth_endpoints(client):
    # Register new user
    reg_res = client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword123",
        "org_name": "New Corp"
    })
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    token = data["access_token"]

    # Login with new user
    login_res = client.post("/api/auth/login", json={
        "email": "newuser@example.com",
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # Get /me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "newuser@example.com"

def test_review_analyze_and_save(client, auth_headers):
    payload = {
        "review": "Ee phone battery backup chala bagundi, superb screen display!",
        "save": True
    }
    res = client.post("/api/reviews/analyze", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "Telugu"
    assert data["is_romanized"] is True
    assert data["sentiment"] in ["Positive", "Negative", "Neutral"]
    assert data["saved_id"] is not None

def test_reviews_list_and_filters(client, auth_headers):
    # Check listing
    res = client.get("/api/reviews?page=1&limit=10", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "reviews" in data

def test_review_label_correction(client, auth_headers):
    # First create a review
    res = client.post("/api/reviews/analyze", json={
        "review": "Avarage performance, packaging not good",
        "save": True
    }, headers=auth_headers)
    review_id = res.json()["saved_id"]

    # Now correct label
    corr_res = client.put(f"/api/reviews/{review_id}/correct", json={
        "corrected_label": "Negative"
    }, headers=auth_headers)
    assert corr_res.status_code == 200
    assert corr_res.json()["corrected_label"] == "Negative"

def test_bulk_csv_upload(client, auth_headers):
    csv_content = (
        "review,product,date,source\n"
        "\"Camera quality chala bagundi\",Test Smartphone X,2026-03-01,Website\n"
        "\"Bahut achhi delivery\",Test Smartphone X,2026-03-02,Store\n"
    )
    files = {"file": ("test_reviews.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/reviews/bulk", files=files, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_rows"] == 2
    assert data["saved_count"] == 2
    assert data["skipped_count"] == 0

def test_analytics_endpoints(client, auth_headers):
    # Summary
    summary = client.get("/api/analytics/summary", headers=auth_headers)
    assert summary.status_code == 200
    assert "total_reviews" in summary.json()

    # Distribution
    dist = client.get("/api/analytics/distribution", headers=auth_headers)
    assert dist.status_code == 200
    assert isinstance(dist.json(), list)

    # By language
    by_lang = client.get("/api/analytics/by-language", headers=auth_headers)
    assert by_lang.status_code == 200

    # Aspects
    aspects = client.get("/api/analytics/aspects", headers=auth_headers)
    assert aspects.status_code == 200

    # Insights
    insights = client.get("/api/analytics/insights", headers=auth_headers)
    assert insights.status_code == 200
    assert "insights" in insights.json()

def test_reports_pdf_and_csv_export(client, auth_headers):
    # Add at least one review first
    client.post("/api/reviews/analyze", json={
        "review": "Superb phone quality",
        "save": True
    }, headers=auth_headers)

    # PDF export
    pdf_res = client.get("/api/reports/pdf", headers=auth_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # CSV export
    csv_res = client.get("/api/reviews/export", headers=auth_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert b"review" in csv_res.content or b"original_text" in csv_res.content
