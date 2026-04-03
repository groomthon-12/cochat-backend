from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, String

from app.models.base import Base


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False)
    account_identifier = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
