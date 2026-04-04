import asyncio
import os
from pprint import pprint

try:
    from dotenv import load_dotenv
    load_dotenv("../cochat-infra/local/.env")
except ImportError:
    pass

from app.pipelines.state import MessageState
from app.pipelines.realtime_graph import realtime_graph

async def main():
    if not os.getenv("GOOGLE_API_KEY"):
        print("💡 에러: GOOGLE_API_KEY 환경변수가 설정되지 않았습니다!")
        print("💡 .env 파일에 키를 넣거나 터미널에서 export 해주세요.")
        return

    # 가상의 입력 데이터 (심각한 장애 상황 가정)
    dummy_state = {
        "message_id": "test_msg_001",
        "content": "디비(db-prod-01) 커넥션 타임아웃 오류가 엄청 발생하고 있습니다. 서버가 멈췄어요! 확인해주세요!",
        "metadata": {
            "provider": "slack",
            "channel_name": "alerts-db-prod",
            "is_direct_target": True,
            "has_attachments": False
        },
        "conversation_history": [],
        "initial_urgency": "",
        "retrieved_context": [],
        "judgment_rationale": "",
        "final_urgency": "",
        "should_store": False,
        "storable_summary": ""
    }
    
    # MemorySaver용 스레드 ID 필요 (타임트래블 기준점)
    config = {"configurable": {"thread_id": "test_session_01"}}
    
    print("🚀 LangGraph 실시간 파이프라인 전체 흐름 테스트를 시작합니다\n")
    print("-" * 50)
    
    # astream을 사용하여 파이프라인의 각 노드 실행 과정을 Stream으로 추적
    async for event in realtime_graph.astream(dummy_state, config=config):
        for node_name, state_update in event.items():
            print(f"🟢 [통과 노드]: {node_name}")
            
            # 노드별 중요 변경사항 요약 출력
            if node_name == "analyze_message":
                print(f"   👉 1차 산출 긴급도 : {state_update.get('initial_urgency')}")
                print(f"   👉 판 단 근 거     : {state_update.get('judgment_rationale')}")
            
            elif node_name == "fast_retrieve_emergency_context":
                print(f"   🚨 Emergency 라우팅 발동! 초저지연 RAG 검색 수행됨")
                print(f"   👉 검색된 SOP 지침 : {state_update.get('retrieved_context')}")
                
            elif node_name == "deep_retrieve_context":
                print(f"   🔍 High/Normal 라우팅 발동! 다단계 정밀 검색 수행됨")
                print(f"   👉 검색된 과거문서: {state_update.get('retrieved_context')}")
                
            elif node_name == "fast_reassess_importance" or node_name == "reassess_importance":
                print(f"   👉 최종 확정 긴급도: {state_update.get('final_urgency')}")
                
            print("-" * 50)
            
    print("\n✅ 파이프라인 그래프 정상 종료 완료.")
    
    # =====================================================================
    # 🔍 Checkpointer(MemorySaver) 타임트래블 확인 파트
    # =====================================================================
    print("\n📸 [Checkpointer 기록 확인]")
    
    # 1. 뼈대 전체의 현재 최종 상태 가져오기
    current_state = realtime_graph.get_state(config)
    print(f"- 현재 저장된 노드 단계: {current_state.next if current_state.next else '종료됨(END)'}")
    print(f"- 메모리에 백업된 최종 Rationale 요약: {current_state.values.get('judgment_rationale')[:30]}...")

    # 2. 어떻게 변해왔는지 과거 히스토리 전부 긁어오기
    history = list(realtime_graph.get_state_history(config))
    print(f"\n- 롤백 가능한 과거 스냅샷 총 개수: {len(history)}장")
    
    print("\n[시간 역순 스냅샷 히스토리]")
    for i, snapshot in enumerate(history):
        # snapshot.values 에 그 당시의 MessageState가 담겨있습니다.
        step_urgency = snapshot.values.get("initial_urgency", "N/A")
        print(f"  [스냅샷 -{i}단계] 저장 시점 긴급도 값: '{step_urgency}'")
        
if __name__ == "__main__":
    asyncio.run(main())
