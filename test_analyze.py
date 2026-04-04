import asyncio
import os
from pprint import pprint

from app.pipelines.state import MessageState
from app.pipelines.realtime_graph import realtime_graph

async def main():
    if not os.getenv("GOOGLE_API_KEY"):
        print("💡 에러: GOOGLE_API_KEY 환경변수가 설정되지 않았습니다!")
        print("💡 .env 파일에 키를 넣거나 터미널에서 export 해주세요.")
        return

    # 가상의 입력 데이터 (심각한 장애 상황 -> 해결 후 메시지)
    dummy_state_1 = {
        "message_id": "test_msg_005",
        "content": "DB 커넥션 타임아웃 발생했습니다. 지금 시스템이 멈췄어요!",
        "metadata": {
            "provider": "slack",
            "channel_name": "dev-team",
            "channel_id": "C01A2B3C4", # 핵심 식별자
            "workspace_id": "W01G2H3I4",
            "occurred_at": "2026-04-04T10:00:00Z",
            "is_direct_target": True,
            "has_attachments": False
        },
        "conversation_history": [],
        "initial_urgency": "",
        "retrieved_context": [],
        "judgment_rationale": "",
        "final_urgency": "",
        "should_store": False,
        "storable_summary": "",
        "issue_type": "new_issue"
    }
    
    dummy_state_2 = {
        "message_id": "test_msg_006",
        "content": "방금 전 커넥션 이슈, 커넥션 풀을 300으로 늘리니까 아예 해결되었습니다.",
        "metadata": {
            "provider": "slack",
            "channel_name": "dev-team",
            "channel_id": "C01A2B3C4", # 동일 채널
            "workspace_id": "W01G2H3I4",
            "occurred_at": "2026-04-04T10:05:00Z",
            "is_direct_target": False,
            "has_attachments": False
        },
        "conversation_history": [],
        "initial_urgency": "",
        "retrieved_context": [],
        "judgment_rationale": "",
        "final_urgency": "",
        "should_store": False,
        "storable_summary": "",
        "issue_type": "resolved"
    }
    
    async def run_flow(state_data, session_id, title):
        config = {"configurable": {"thread_id": session_id}}
        print(f"🚀 {title}\n")
        print("-" * 50)
        async for event in realtime_graph.astream(state_data, config=config):
            for node_name, state_update in event.items():
                print(f"🟢 [통과 노드]: {node_name}")
                if node_name == "analyze_message":
                    print(f"   👉 분류된 이슈타입: {state_update.get('issue_type')}")
                    print(f"   👉 산출 긴급도 : {state_update.get('initial_urgency')}")
                elif node_name == "store_vector_db":
                    print(f"   💾 VectorDB 저장 완료 통과")
                print("-" * 50)
        print(f"\n✅ {title} 완료.\n")
        
    await run_flow(dummy_state_1, "session_01", "[1단계] 장애 발생 이벤트")
    await run_flow(dummy_state_2, "session_02", "[2단계] 장애 해결 후속 이벤트")
    
    # =====================================================================
    # 🔍 Checkpointer(MemorySaver) 타임트래블 확인 파트
    # =====================================================================
    print("\n📸 [Checkpointer 기록 확인]")
    
    config = {"configurable": {"thread_id": "session_02"}}
    
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
