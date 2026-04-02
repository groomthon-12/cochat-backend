import asyncio
import os
from pprint import pprint

# 만약 .env 파일을 파이썬 환경에서 읽어오고 싶다면 dotenv-python 라이브러리가 필요합니다.
# 터미널에서 export GOOGLE_API_KEY="..." 를 먼저 입력했다면 이 부분은 없어도 됩니다.
try:
    from dotenv import load_dotenv
    # 도커 컴포즈 구조상 infra/local/.env를 참조하는지, 혹은 backend/.env를 참조하는지 확인 후 로드
    load_dotenv("../cochat-infra/local/.env") 
except ImportError:
    pass

from app.pipelines.state import MessageState
from app.pipelines.realtime_graph import analyze_message, run_realtime_pipeline

async def main():
    if not os.getenv("GOOGLE_API_KEY"):
        print("💡 에러: GOOGLE_API_KEY 환경변수가 설정되지 않았습니다!")
        return

    # 1. 가상의 입력 데이터(State) 생성
    dummy_state = MessageState(
        message_id="test_msg_001",
        content="수고하셨습니다",
        metadata={
            "provider": "slack",
            "channel_name": "dev-team",
            "is_direct_target": True,
            "has_attachments": False
        },
        conversation_history=[],
        initial_urgency="",
        retrieved_context=[],
        judgment_rationale="",
        final_urgency="",
        should_store=False,
        storable_summary=""
    )
    
    print("🤖 Gemini 모델에게 메시지 분석을 요청합니다...")
    
    # 2. 노드 함수 단독으로 찔러보기 테스트
    result = analyze_message(dummy_state)
    
    print("\n[LLM 판단 결과]")
    pprint(result, width=100)

if __name__ == "__main__":
    asyncio.run(main())
