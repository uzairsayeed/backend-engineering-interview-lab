from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from app.constants import SHORT_CODE_MAX_LENGTH

# Base is the parent of our SQLAlchemy ORM models.
# When this class is declared:
    # SQLAlchemy registers its table metadata under:
        # Base.metadata
        # Conceptually:
            # Base.metadata
            #     └── short_urls table definition
    
class Base(DeclarativeBase):
    pass


class ShortUrlRecord(Base):
    __tablename__ = "short_urls"

    __table_args__ = (
        UniqueConstraint(
            "short_code",
            name="uq_short_urls_short_code",
        ),
        CheckConstraint(
            "redirect_count >= 0",
            name="ck_short_urls_redirect_count_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    short_code: Mapped[str] = mapped_column(
        String(SHORT_CODE_MAX_LENGTH),
        nullable=False,
    )

    destination_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    redirect_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    def __repr__(self) -> str:
        return (
            "ShortUrlRecord("
            f"id={self.id!r}, "
            f"short_code={self.short_code!r}"
            ")"
        )