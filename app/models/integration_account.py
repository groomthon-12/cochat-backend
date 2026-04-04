from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(String, nullable=False)
    account_identifier = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="integration_accounts")
