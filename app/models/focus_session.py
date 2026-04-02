from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    planned_duration_minutes = Column(Integer, nullable=False)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="active")

    briefings = relationship("Briefing", back_populates="session")
