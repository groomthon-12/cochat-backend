from typing import Dict, Any

from app.integrations.normalizer import NotificationEvent
from app.pipelines.state import MessageState
from app.pipelines.realtime_graph import realtime_graph
from app.core.redis_manager import fetch_short_term_memory, add_to_short_term_memory

async def run_pipeline_with_memory(event: NotificationEvent) -> Dict[str, Any]:
    """
    웹훅으로부터 발생한 NotificationEvent를 받아 
    단기기억(Redis) 컨텍스트를 주입한 뒤 LangGraph 파이프라인을 구동하고,
    마지막에 이번 메시지를 다시 단기기억 버퍼에 추가하는 전방위 진입점입니다.
    """
    
    # 1. 단기기억(Conversation History) 확보
    channel_id = event.channel_id
    recent_history = []
    if channel_id:
        recent_history = await fetch_short_term_memory(channel_id)
        
    # 2. 이번 메시지 문자열 깔끔하게 포매팅
    sender = event.sender_name or "Unknown"
    formatted_current_msg = f"[{sender}]: {event.original_text}"

    # 3. LangGraph 초기 상태(State) 구성
    metadata = {
        "provider": event.provider,
        "source_type": event.source_type,
        "workspace_id": event.workspace_id,
        "channel_id": channel_id,
        "sender_id": event.sender_id,
        "sender_name": event.sender_name,
        "channel_name": event.channel_name,
        "is_direct_target": event.is_direct_target,
        "is_broadcast": event.is_broadcast,
        "has_attachments": event.has_attachments,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "source_url": event.source_url
    }
    
    initial_state = {
        "message_id": event.provider_object_id,
        "content": event.original_text,
        "metadata": metadata,
        "conversation_history": recent_history
    }
    
    # Thread ID 지정을 통해 Checkpointer 트래킹
    config = {"configurable": {"thread_id": event.provider_object_id}}
    
    # 4. 실시간 파이프라인 실행
    print(f"🚀 [Pipeline Entry] 이벤트 분석 시작 (ID: {event.provider_object_id})")
    print(f"👉 장착된 단기기억(스레드 문맥) 개수: {len(recent_history)}개")
    final_state = await realtime_graph.ainvoke(initial_state, config=config)
    
    # 5. 파이프라인 무사고 통과 시, 이 메시지를 단기기억에 Push
    # (반드시 After Execution 에 해야 LLM이 중복/동어반복 오류를 일으키지 않음)
    if channel_id:
        await add_to_short_term_memory(channel_id, formatted_current_msg)
        
    print(f"✅ [Pipeline Entry] 처리 완료 및 단기기억 최신화 완료.")
    
    # 분석된 결과 일부 반환 (Webhook 응답 등에서 사용)
    return {
        "final_urgency": final_state.get("final_urgency"),
        "issue_type": final_state.get("issue_type"),
        "judgment_rationale": final_state.get("judgment_rationale")
    }
