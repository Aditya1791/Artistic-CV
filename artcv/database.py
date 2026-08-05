"""
ArtCV Database Layer - SQLAlchemy ORM & SQLite/PostgreSQL Database Manager
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

# Environment variable configuration for database connection string
# Default to local SQLite database: sqlite:///./artcv.db
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./artcv.db")

# Handle Heroku / PostgreSQL postgres:// to postgresql:// fix if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Append sslmode=require for remote PostgreSQL connections if omitted
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True) # Null for pure OAuth users
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    provider = Column(String(50), default="email") # email, google, facebook
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    gallery_items = relationship("GalleryItem", back_populates="owner", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "provider": self.provider,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class GalleryItem(Base):
    __tablename__ = "gallery_items"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    effect_name = Column(String(100), nullable=False)
    params = Column(Text, default="{}")
    media_type = Column(String(50), default="image") # image, video
    file_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="gallery_items")

    def to_dict(self) -> Dict[str, Any]:
        if self.file_path.startswith("http://") or self.file_path.startswith("https://"):
            file_url = self.file_path
        else:
            file_url = f"/api/gallery/file/{os.path.basename(self.file_path)}"

        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "effect_name": self.effect_name,
            "params": self.params,
            "media_type": self.media_type,
            "file_url": file_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def init_db():
    """Initializes tables in database with automatic fallback if remote DB is unreachable."""
    global engine, SessionLocal
    try:
        print(f"[DB] Initializing database engine: {engine.url.render_as_string(hide_password=True)}")
        Base.metadata.create_all(bind=engine)
        print("[DB] Database tables created successfully.")
    except Exception as e:
        print(f"[DB ERROR] Remote database connection failed: {e}")
        if "sqlite" not in str(engine.url):
            print("[DB WARN] Falling back to local SQLite database (sqlite:///./artcv.db) so server can start.")
            fallback_url = "sqlite:///./artcv.db"
            engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            Base.metadata.create_all(bind=engine)
            print("[DB] Local SQLite fallback ready.")



def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database helper functions

def get_or_create_guest_user(db: Session) -> User:
    guest = db.query(User).filter(User.email == "guest@artisticcv.app").first()
    if not guest:
        guest = User(
            email="guest@artisticcv.app",
            name="Guest Creator ⚡",
            provider="guest",
            avatar_url="https://ui-avatars.com/api/?name=Guest+Creator&background=ff7e67&color=fff"
        )
        db.add(guest)
        db.commit()
        db.refresh(guest)
    return guest


def create_user(
    db: Session,
    email: str,
    name: str,
    password_hash: Optional[str] = None,
    avatar_url: Optional[str] = None,
    provider: str = "email"
) -> User:
    user = User(
        email=email.lower().strip(),
        name=name,
        password_hash=password_hash,
        avatar_url=avatar_url,
        provider=provider
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user




def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def save_gallery_item(
    db: Session,
    user_id: int,
    title: str,
    effect_name: str,
    file_path: str,
    params: str = "{}",
    media_type: str = "image"
) -> GalleryItem:
    item = GalleryItem(
        user_id=user_id,
        title=title,
        effect_name=effect_name,
        params=params,
        media_type=media_type,
        file_path=file_path
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_user_gallery(db: Session, user_id: int, limit: int = 100) -> List[GalleryItem]:
    return (
        db.query(GalleryItem)
        .filter(GalleryItem.user_id == user_id)
        .order_by(GalleryItem.created_at.desc())
        .limit(limit)
        .all()
    )


def get_gallery_item_by_id(db: Session, item_id: str) -> Optional[GalleryItem]:
    return db.query(GalleryItem).filter(GalleryItem.id == item_id).first()


def delete_gallery_item(db: Session, item_id: str, user_id: int) -> bool:
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id, GalleryItem.user_id == user_id).first()
    if not item:
        return False
    
    # Try deleting file on disk if exists
    if os.path.exists(item.file_path):
        try:
            os.remove(item.file_path)
        except Exception:
            pass

    db.delete(item)
    db.commit()
    return True
