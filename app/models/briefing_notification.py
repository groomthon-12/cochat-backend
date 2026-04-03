from sqlalchemy import BigInteger, Column, ForeignKey, Index, UniqueConstraint

from app.models.base import Base


class BriefingNotification(Base):
    __tablename__ = "briefing_notifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    briefing_id = Column(
        BigInteger,
        ForeignKey("briefings.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_id = Column(
        BigInteger,
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("briefing_id", "notification_id", name="uq_briefing_notification"),
        Index("ix_briefing_notifications_briefing_id", "briefing_id"),
    )
