from fastapi import APIRouter

router = APIRouter(tags=["briefing"])


@router.post("/focus-sessions", status_code=201)
def create_focus_session():
    """집중 세션 시작"""
    return {"sessionId": "", "status": "started"}


@router.patch("/focus-sessions/{sessionId}")
def update_focus_session(sessionId: str):
    """집중 세션 종료 또는 업데이트"""
    return {"sessionId": sessionId, "status": "updated"}


@router.post("/briefings", status_code=201)
def create_briefing():
    """브리핑 생성 (AI 요약 요청)"""
    return {"briefingId": "", "status": "pending"}


@router.get("/briefings/latest")
def get_latest_briefing():
    """가장 최근 브리핑 조회"""
    return {"briefing": None}
