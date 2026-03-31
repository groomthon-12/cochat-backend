from fastapi import APIRouter

router = APIRouter(tags=["notifications"])


@router.post("/webhooks/slack", status_code=200)
def slack_webhook(payload: dict = {}):
    """Slack 웹훅 수신"""
    return {"status": "received"}


@router.get("/notifications")
def list_notifications():
    """알림 목록 조회"""
    return {"notifications": []}


@router.patch("/notifications/{notificationId}")
def update_notification(notificationId: str):
    """알림 상태 업데이트 (읽음 처리 등)"""
    return {"notificationId": notificationId, "status": "updated"}
