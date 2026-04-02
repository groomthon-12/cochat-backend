import uuid

from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class BriefingNotification(Base):
    __tablename__ = "briefing_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    briefing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("briefings.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("briefing_id", "notification_id", name="uq_briefing_notification"),
        Index("ix_briefing_notifications_briefing_id", "briefing_id"),
    )
