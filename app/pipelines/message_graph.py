import datetime
from typing import TypedDict, Optional, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END

# ==============================================================================
# 1. State Definitions (상태 정의)
# ==============================================================================

class MessageState(TypedDict):
    """
    실시간 메시지 처리 파이프라인 상태
    """
    message_id: str                  # 외부(API)에서 주입된 PostgreSQL 원본 메시지 식별자
    content: str                     # 발신 내용 원본
    conversation_history: List[Dict[str, Any]] # 메시지가 발생한 스레드의 최근 대화 맥락 (단기 기억 용도)
    metadata: Dict[str, Any]         # 발신자, 시간 등
    
    initial_urgency: str             # "Emergency", "High", "Normal", "Low", ""
    retrieved_context: List[str]     # RAG 검색 결과 (과거 피드백, 문서 등)
    judgment_rationale: str          # LLM이 도출한 응급도 판단 근거 (피드백 시 원인 분석용)
    final_urgency: str               # "Emergency", "High", "Normal", "Low", ""
    
    should_store: bool               # 임베딩/요약 저장 여부
    storable_summary: str            # 저장에 적합하게 가공된 내용 요약


class FeedbackState(TypedDict):
    """
    사용자 피드백 (오분류 정정) 처리 파이프라인 상태
    """
    message_id: str                  # 대상 원본 메시지 식별자 (PostgreSQL)
    original_urgency: str            # 기존에 시스템이 판단했던 잘못된 중요도
    original_rationale: str          # 기존 시스템이 오분류를 내렸던 판단 근거 (RDB 조회)
    user_corrected_urgency: str      # 사용자가 정정한 올바른 중요도
    feedback_reason: str             # (선택) 사용자가 입력한 오분류 사유
    
    extracted_guideline: str         # LLM이 도출한 향후 오분류 방지용 일반화 가이드라인 (Few-shot용)


class MemoryGCState(TypedDict):
    """
    메모리(Vector DB) 가비지 컬렉션 및 유지보수 파이프라인 상태
    """
    target_memories: List[Dict[str, Any]]     # 검토용으로 가져온 오래된 메모리 청크
    evaluation_results: List[Dict[str, Any]]  # 각 메모리에 대한 평가 결과 (유지, 가중치 하락, 삭제 판단)


# ==============================================================================
# 2. Real-time Message Assessment Graph
# ==============================================================================

def analyze_message(state: MessageState) -> dict:
    """1차 긴급도 및 저장 가치(Summary) 판단 (LLM)"""
    # TODO: LLM 호출하여 initial_urgency 결정
    # TODO: should_store 와 storable_summary 결정
    return {
        "initial_urgency": "Normal", # Mock
        "final_urgency": "Normal",   # RAG를 거치지 않는 케이스를 위해 기본값 세팅
        "judgment_rationale": "긴급한 키워드나 긴급 연락 맥락이 없으므로 Normal로 판단함.", # Mock
        "should_store": True,        # Mock
        "storable_summary": "요약된 내용..." 
    }

def fast_retrieve_emergency_context(state: MessageState) -> dict:
    """[Emergency 전용] 초저지연 캐시/하이브리드 직접 검색 (Re-ranking 생략). 핵심 SOP, 치명적 오탐 로그만 조회"""
    # TODO: BM25 및 벡터 1차 필터(ANN) 병렬 조회 (< 150ms)
    return {"retrieved_context": ["SOP: DB 다운 시 즉시 인프라팀 호출방 전달", "오탐 피드백: 'DB 재연결 테스트' 단어는 알람 아님"]}

def fast_reassess_importance(state: MessageState) -> dict:
    """가벼운/빠른 모델을 이용해 Emergency 유지 여부만 1차 확인"""
    return {
        "final_urgency": "Emergency",
        "judgment_rationale": "SOP 대조 결과 치명적 장애로 판단. (초저지연 검증)"
    }

def deep_retrieve_context(state: MessageState) -> dict:
    """[High/Normal 전용] 높은 정확도를 위한 다단계 재랭킹(Multiphase Ranking) 검색"""
    # TODO: 하이브리드 검색 후 Cross-Encoder를 통한 정밀 재랭킹 적용 (< 1.5s)
    return {"retrieved_context": ["일반 가이드라인...", "유사 피드백 광범위 분석 자료..."]}

def reassess_importance(state: MessageState) -> dict:
    """검색된 Context를 바탕으로 중요도 재조정"""
    # TODO: LLM으로 Context 포함시켜 final_urgency 결정, judgment_rationale 갱신(프롬프팅)
    return {
        "final_urgency": state.get("initial_urgency", "Normal"),
        "judgment_rationale": "과거 피드백 정보(유사 건)를 조회한 결과... 그러므로 기존 판단을 유지함."
    }

def route_to_storage_decision(state: MessageState) -> dict:
    """더미 노드: 분기 후 저장 결정으로 모이는 지점 (필요시 데이터 통합 등 수행)"""
    return {}

def store_vector_db(state: MessageState) -> dict:
    """(should_store=True) 임베딩하여 Vector DB에 장기 기억으로 저장"""
    # TODO: state["storable_summary"] 임베딩 후 벡터 DB 삽입
    return {}

# Edge Routing Conditionals
def check_urgency(state: MessageState) -> str:
    urgency = state.get("initial_urgency", "Low")
    if urgency == "Emergency":
         return "emergency"
    elif urgency in ["High", "Normal"]:
         return "high_normal"
    else:
         return "low"

def check_should_store(state: MessageState) -> str:
    return "store" if state.get("should_store", False) else "end"

realtime_builder = StateGraph(MessageState)
realtime_builder.add_node("analyze_message", analyze_message)
realtime_builder.add_node("fast_retrieve_emergency_context", fast_retrieve_emergency_context)
realtime_builder.add_node("fast_reassess_importance", fast_reassess_importance)
realtime_builder.add_node("deep_retrieve_context", deep_retrieve_context)
realtime_builder.add_node("reassess_importance", reassess_importance)
realtime_builder.add_node("route_to_storage_decision", route_to_storage_decision)
realtime_builder.add_node("store_vector_db", store_vector_db)

realtime_builder.set_entry_point("analyze_message")

# 라우팅 1: 분류에 따라 계층화된 검색(Adaptive RAG) 라우팅
realtime_builder.add_conditional_edges(
    "analyze_message",
    check_urgency,
    {
        "emergency": "fast_retrieve_emergency_context",
        "high_normal": "deep_retrieve_context",
        "low": "route_to_storage_decision"
    }
)

# Emergency 분기 처리
realtime_builder.add_edge("fast_retrieve_emergency_context", "fast_reassess_importance")
realtime_builder.add_edge("fast_reassess_importance", "route_to_storage_decision")

# High/Normal 분기 처리
realtime_builder.add_edge("deep_retrieve_context", "reassess_importance")
realtime_builder.add_edge("reassess_importance", "route_to_storage_decision")

# 라우팅 2: 저장 결정
realtime_builder.add_conditional_edges(
    "route_to_storage_decision",
    check_should_store,
    {
        "store": "store_vector_db",
        "end": END
    }
)
realtime_builder.add_edge("store_vector_db", END)
realtime_graph = realtime_builder.compile()


# ==============================================================================
# 3. User Feedback Graph (피드백 학습)
# ==============================================================================

def retrieve_original_message(state: FeedbackState) -> dict:
    """PostgreSQL에서 사용자가 피드백한 원본 메시지와 메타데이터 조회"""
    # TODO: DB 쿼리로 대상 메시지 내용 조회
    return {}

def extract_correction_guideline(state: FeedbackState) -> dict:
    """원분류와 수정분류의 차이로부터 Few-shot 가이드라인을 LLM으로 추출"""
    # TODO: LLM 호출 -> 'A 메시지는 B가 아니라 C입니다. 사유: ...' 형태의 룰 생성
    return {"extracted_guideline": "이런 패턴의 알림은 단순 모니터링이므로 Low로 분류할 것."}

def store_feedback_guideline(state: FeedbackState) -> dict:
    """추출된 가이드라인을 RAG 컨텍스트 생성을 위해 Vector DB (또는 DB)에 저장"""
    # TODO: Vector DB 등에 Insert
    return {}

feedback_builder = StateGraph(FeedbackState)
feedback_builder.add_node("retrieve_original_message", retrieve_original_message)
feedback_builder.add_node("extract_correction_guideline", extract_correction_guideline)
feedback_builder.add_node("store_feedback_guideline", store_feedback_guideline)

feedback_builder.set_entry_point("retrieve_original_message")
feedback_builder.add_edge("retrieve_original_message", "extract_correction_guideline")
feedback_builder.add_edge("extract_correction_guideline", "store_feedback_guideline")
feedback_builder.add_edge("store_feedback_guideline", END)
feedback_graph = feedback_builder.compile()


# ==============================================================================
# 4. Memory GC (Garbage Collection) Graph
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

gc_builder = StateGraph(MemoryGCState)
gc_builder.add_node("fetch_stale_memories", fetch_stale_memories)
gc_builder.add_node("evaluate_memory_relevance", evaluate_memory_relevance)
gc_builder.add_node("update_or_delete_vector_db", update_or_delete_vector_db)

gc_builder.set_entry_point("fetch_stale_memories")
gc_builder.add_edge("fetch_stale_memories", "evaluate_memory_relevance")
gc_builder.add_edge("evaluate_memory_relevance", "update_or_delete_vector_db")
gc_builder.add_edge("update_or_delete_vector_db", END)
memory_gc_graph = gc_builder.compile()


# ==============================================================================
# EXPORTS
# ==============================================================================
__all__ = [
    "realtime_graph",
    "feedback_graph",  
    "memory_gc_graph",
    "MessageState",
    "FeedbackState",
    "MemoryGCState"
]
