import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    org_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True)

    user = relationship("User", back_populates="products")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    
    original_text = Column(Text, nullable=False)
    language = Column(String(50), nullable=False, index=True)
    script = Column(String(50), nullable=False)
    is_romanized = Column(Boolean, default=False, index=True)
    transliterated_text = Column(Text, nullable=True)
    
    sentiment = Column(String(20), nullable=False, index=True) # Positive, Negative, Neutral
    confidence = Column(Float, nullable=False)
    prob_pos = Column(Float, nullable=False)
    prob_neg = Column(Float, nullable=False)
    prob_neu = Column(Float, nullable=False)
    
    aspects = Column(Text, default="[]") # JSON list of detected aspects
    source = Column(String(50), default="single") # single, bulk, seed
    review_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    corrected_label = Column(String(20), nullable=True) # for human correction feedback

    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")

    def get_aspects_list(self):
        try:
            return json.loads(self.aspects) if self.aspects else []
        except Exception:
            return []

    def set_aspects_list(self, aspect_list):
        self.aspects = json.dumps(aspect_list)
