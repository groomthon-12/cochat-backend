import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(
        UUID(as_uuid=True),
        ForeignKey("integration_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("raw_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type = Column(String, nullable=False)
    provider_object_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    original_text = Column(Text, nullable=True)
    content_preview = Column(Text, nullable=True)
    source_url = Column(String, nullable=True)
    actor_name = Column(String, nullable=True)
    context_name = Column(String, nullable=True)
    is_direct_target = Column(Boolean, nullable=False, default=False)
    occurred_at = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String, nullable=True)
    priority_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    requires_decision = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="unread")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    integration = relationship("IntegrationAccount", backref="notifications")
    raw_event = relationship("RawEvent", back_populates="notifications")
    feedback_reports = relationship("FeedbackReport", back_populates="notification")
