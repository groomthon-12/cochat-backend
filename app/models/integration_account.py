import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    account_identifier = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
