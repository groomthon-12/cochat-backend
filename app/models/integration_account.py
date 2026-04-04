from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "user_id",
            "slack_team_id",
            "slack_user_id",
            name="uq_integration_accounts_provider_user_slack_identity",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(String, nullable=False)
    account_identifier = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    slack_team_id = Column(String, nullable=True)
    slack_user_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="integration_accounts")
