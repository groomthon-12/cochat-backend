from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.pipelines.state import FeedbackState

# ==============================================================================
# Node Functions
# ==============================================================================

def retrieve_original_message(state: FeedbackState) -> dict:
    """PostgreSQL에서 사용자가 피드백한 원본 메시지와 메타데이터 조회"""
    # TODO: DB 쿼리로 대상 메시지 내용 조회
    return {}

def extract_correction_guideline(state: FeedbackState) -> dict:
    """원분류와 수정분류의 차이로부터 Few-shot 가이드라인을 LLM으로 추출"""
    # TODO: LLM 호출 -> 'A 메시지는 B가 아니라 C입니다. 사유: ...' 형태의 룰 생성
    return {"extracted_guideline": "이런 패턴의 알림은 단순 모니터링이므로 Low로 분류할 것."}

def validate_guideline_consistency(state: FeedbackState) -> dict:
    """도출된 신규 가이드라인이 기존 DB의 가이드라인과 겹치거나 충돌하지 않는지(RAG Poisoning 영지) 교차 검증"""
    # TODO: 신규 가이드라인으로 Vector DB에 유사 규칙 검색 수행
    # TODO: LLM 평가원(Evaluator)을 통해 기존 규칙과 'Valid(승인)', 'Merge(병합)', 'Conflict(충돌)' 여부 판별
    return {"validation_result": "Valid"}

def override_conflicting_guideline(state: FeedbackState) -> dict:
    """[1인 환경] 기존 핵심 정책과 충돌하는 경우, 사용자의 최신 피드백을 '최우선(Source of Truth)'으로 보고 과거 규칙을 덮어씀(Override)"""
    # TODO: Vector DB에서 충돌의 원인이 된 과거 가이드라인을 삭제(Delete)하고, 이번 신규 가이드라인을 강제 Insert
    return {}

async def store_feedback_guideline(state: FeedbackState) -> dict:
    """검증을 통과한 가이드라인을 RAG 컨텍스트 생성을 위해 Vector DB에 신규 Insert 수행"""
    guideline = state.get("extracted_guideline")
    if guideline:
        from app.pipelines.shared.retriever_utils import astore_document_to_vector_db
        await astore_document_to_vector_db(
            content=guideline,
            metadata={
                "message_id": state.get("message_id"),
                "source": "user_feedback_guideline"
            }
        )
    return {}

# ==============================================================================
# Routing Functions
# ==============================================================================

def check_guideline_validity(state: FeedbackState) -> str:
    """검증 결과에 따른 라우팅"""
    res = state.get("validation_result", "Valid").lower()
    if res in ["valid", "merge"]:
        return "store"
    else:  # "conflict"
        return "override"

# ==============================================================================
# Graph Builder
# ==============================================================================

feedback_builder = StateGraph(FeedbackState)
feedback_builder.add_node("retrieve_original_message", retrieve_original_message)
feedback_builder.add_node("extract_correction_guideline", extract_correction_guideline)
feedback_builder.add_node("validate_guideline_consistency", validate_guideline_consistency)
feedback_builder.add_node("override_conflicting_guideline", override_conflicting_guideline)
feedback_builder.add_node("store_feedback_guideline", store_feedback_guideline)

feedback_builder.set_entry_point("retrieve_original_message")
feedback_builder.add_edge("retrieve_original_message", "extract_correction_guideline")
feedback_builder.add_edge("extract_correction_guideline", "validate_guideline_consistency")

feedback_builder.add_conditional_edges(
    "validate_guideline_consistency",
    check_guideline_validity,
    {
        "store": "store_feedback_guideline",
        "override": "override_conflicting_guideline"
    }
)
feedback_builder.add_edge("store_feedback_guideline", END)
feedback_builder.add_edge("override_conflicting_guideline", END)

# ==============================================================================
# Graph Compilation with Checkpointer
# ==============================================================================

memory_saver_feedback = MemorySaver()
feedback_graph = feedback_builder.compile(checkpointer=memory_saver_feedback)

# ==============================================================================
# External API Wrappers
# ==============================================================================

async def run_feedback_pipeline(initial_state: dict, config: dict = None) -> dict:
    """[피드백 처리] 파이프라인 실행 후 검증 결과 및 추출된 룰만 리턴"""
    full_state = await feedback_graph.ainvoke(initial_state, config=config)
    return {
        "message_id": full_state.get("message_id"),
        "extracted_guideline": full_state.get("extracted_guideline"),
        "validation_result": full_state.get("validation_result")
    }

__all__ = ["feedback_graph", "run_feedback_pipeline"]
