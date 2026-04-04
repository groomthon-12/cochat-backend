from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["streams"])


async def _event_generator():
    """SSE 이벤트 스트림 (추후 구현)"""
    yield "data: {}\n\n"


@router.get("/notifications/stream")
def notification_stream():
    """SSE 실시간 알림 스트림"""
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
