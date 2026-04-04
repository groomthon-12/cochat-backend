from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.pipelines.state import MemoryGCState

# ==============================================================================
# Node Functions
# ==============================================================================

def fetch_stale_memories(state: MemoryGCState) -> dict:
    """일정 기간 경과했거나 중요도가 떨어진 낡은 임베딩을 Vector DB에서 조회"""
    # TODO: Vector DB Query
    return {"target_memories": [{"id": "vec123", "content": "과거 알림", "date": "2026-02-01"}]}

def evaluate_memory_relevance(state: MemoryGCState) -> dict:
    """LLM이 현재 시점 기준으로 메모리의 유효성을 평가 (유지/강등/삭제)"""
    # TODO: Batch LLM 호출 (병렬 처리 권장)
    return {"evaluation_results": [{"id": "vec123", "action": "delete", "reason": "이슈 해결됨"}]}

def update_or_delete_vector_db(state: MemoryGCState) -> dict:
    """평가 결과에 따라 Vector DB의 임베딩 삭제 또는 메타데이터 가중치 하락 연산"""
    # TODO: Delete/Update 쿼리 실행
    return {}

# ==============================================================================
# Graph Builder
# ==============================================================================

gc_builder = StateGraph(MemoryGCState)
gc_builder.add_node("fetch_stale_memories", fetch_stale_memories)
gc_builder.add_node("evaluate_memory_relevance", evaluate_memory_relevance)
gc_builder.add_node("update_or_delete_vector_db", update_or_delete_vector_db)

gc_builder.set_entry_point("fetch_stale_memories")
gc_builder.add_edge("fetch_stale_memories", "evaluate_memory_relevance")
gc_builder.add_edge("evaluate_memory_relevance", "update_or_delete_vector_db")
gc_builder.add_edge("update_or_delete_vector_db", END)

# ==============================================================================
# Graph Compilation with Checkpointer
# ==============================================================================

memory_saver_gc = MemorySaver()
memory_gc_graph = gc_builder.compile(checkpointer=memory_saver_gc)

# ==============================================================================
# External API Wrappers
# ==============================================================================

async def run_gc_pipeline(initial_state: dict, config: dict = None) -> dict:
    """[메모리 정리] 파이프라인 실행 후 처리된 결과 목록 리턴"""
    full_state = await memory_gc_graph.ainvoke(initial_state, config=config)
    return {
        "evaluation_results": full_state.get("evaluation_results", [])
    }

__all__ = ["memory_gc_graph", "run_gc_pipeline"]
