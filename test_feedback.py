import asyncio
import os
from pprint import pprint

from app.pipelines.state import FeedbackState
from app.pipelines.feedback_graph import feedback_graph

async def main():
    if not os.getenv("GOOGLE_API_KEY"):
        print("💡 에러: GOOGLE_API_KEY 환경변수가 설정되지 않았습니다!")
        print("💡 .env 파일에 키를 넣거나 터미널에서 export 해주세요.")
        return

    # 가상의 피드백 데이터 (사용자가 AI의 'Emergency' 오분류를 'Low'로 질책하며 정정한 상황)
    dummy_state = {
        "message_id": "test_feedback_101",
        "content": "배치 스크립트 실행 중 타임아웃 발생 (TimeoutError: Database Lock)",
        "metadata": {
            "provider": "slack",
            "channel_name": "alerts",
            "is_direct_target": False,
            "has_attachments": False
        },
        "original_urgency": "Emergency",
        "original_rationale": "TimeoutError 키워드가 있으며 DB Lock으로 인해 즉각적인 서비스 중단이 우려됨.",
        "user_corrected_urgency": "Low",
        "feedback_reason": "새벽 DWH 배치 스크립트 타임아웃은 종종 발생하는 로그성 알람이며 시스템이 자체 재시도하므로 당장 개발자를 깨울 필요 없음."
    }
    
    # MemorySaver용 스레드 ID
    config = {"configurable": {"thread_id": "feedback_session_01"}}
    
    print("🚀 LangGraph 피드백(Feedback) 파이프라인 전체 흐름 테스트를 시작합니다\n")
    print("-" * 50)
    
    # astream을 사용하여 파이프라인 진행률 추적
    async for event in feedback_graph.astream(dummy_state, config=config):
        for node_name, state_update in event.items():
            print(f"🟢 [통과 노드]: {node_name}")
            
            if node_name == "extract_correction_guideline":
                print(f"   👉 🧠 추출된 신규 가이드라인: {state_update.get('extracted_guideline')}")
                
            elif node_name == "validate_guideline_consistency":
                result = state_update.get('validation_result')
                ids = state_update.get('conflicting_doc_ids', [])
                print(f"   🔍 ⚔️ 충돌 검증 결과: {result}")
                if ids:
                    print(f"   ⚠️ 충돌 ID 목록: {ids}")
                    
            elif node_name == "override_conflicting_guideline":
                print(f"   🗑️ 구형 가이드라인 폐기 엣지 호출됨 (DB 삭제 완료)")
                
            elif node_name == "store_feedback_guideline":
                print(f"   💾 신규 가이드라인 Vector DB 영구 저장 완료")
                
            print("-" * 50)
            
    print("\n✅ 피드백 파이프라인 그래프 정상 종료 완료.")

if __name__ == "__main__":
    asyncio.run(main())
