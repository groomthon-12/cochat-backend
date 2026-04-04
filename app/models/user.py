from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    integration_accounts = relationship("IntegrationAccount", back_populates="user")
    focus_sessions = relationship("FocusSession", back_populates="user")
