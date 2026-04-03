from fastapi import APIRouter

router = APIRouter(tags=["integrations"])


@router.get("/integrations")
def list_integrations():
    """연동된 플랫폼 목록 조회"""
    return {"integrations": []}


@router.get("/integrations/slack/oauth-url")
def get_slack_oauth_url():
    """Slack OAuth 인증 URL 반환"""
    return {"url": ""}


@router.get("/integrations/slack/callback")
def slack_oauth_callback(code: str = "", state: str = ""):
    """Slack OAuth 콜백 처리"""
    return {"status": "ok"}
