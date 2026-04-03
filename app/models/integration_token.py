from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class IntegrationToken(Base):
    __tablename__ = "integration_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    integration_id = Column(
        BigInteger,
        ForeignKey("integration_accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    integration = relationship("IntegrationAccount", backref="token")
