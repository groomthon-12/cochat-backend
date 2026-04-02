from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    notification_id = Column(
        BigInteger,
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_type = Column(String, nullable=False)
    expected_priority = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    notification = relationship("Notification", back_populates="feedback_reports")
