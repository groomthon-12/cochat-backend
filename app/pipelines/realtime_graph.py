from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.pipelines.state import MessageState
from app.pipelines.shared.retriever_utils import search_hybrid_rrf, search_cross_encoder_rerank

# ==============================================================================
# Node Functions
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
    query = state.get("content", "")
    # BM25 및 벡터 1차 필터(ANN) 병렬 조회 후 RRF 융합 수행 (< 150ms)
    fused_docs = search_hybrid_rrf(query, top_k=2)
    contexts = [doc.get("content", "") for doc in fused_docs]
    return {"retrieved_context": contexts}

def fast_reassess_importance(state: MessageState) -> dict:
    """가벼운/빠른 모델을 이용해 Emergency 유지 여부만 1차 확인"""
    return {
        "final_urgency": "Emergency",
        "judgment_rationale": "SOP 대조 결과 치명적 장애로 판단. (초저지연 검증)"
    }

def deep_retrieve_context(state: MessageState) -> dict:
    """[High/Normal 전용] 높은 정확도를 위한 다단계 재랭킹(Multiphase Ranking) 검색"""
    query = state.get("content", "")
    
    # 1. 하이브리드 검색 및 RRF로 초기 후보군(Candidate Pool) 구성
    candidates = search_hybrid_rrf(query, top_k=10)
    
    # 2. Cross-Encoder를 통한 2차 정밀 재랭킹 (< 1.5s)
    reranked_docs = search_cross_encoder_rerank(candidates, query, top_k=3)
    
    contexts = [doc.get("content", "") for doc in reranked_docs]
    return {"retrieved_context": contexts}

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

# ==============================================================================
# Routing Functions
# ==============================================================================

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


# ==============================================================================
# Graph Builder
# ==============================================================================

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

# ==============================================================================
# Graph Compilation with Checkpointer
# ==============================================================================

# 로컬 테스트 및 디버깅용 MemorySaver 적용 (Time Travel, 스냅샷 기록 지원)
# 실제 프로덕션(Postgres 연결 시)에서는 AsyncPostgresSaver 객체를 인자로 넘겨 컴파일해야 합니다.
memory_saver_realtime = MemorySaver()
realtime_graph = realtime_builder.compile(checkpointer=memory_saver_realtime)


# ==============================================================================
# External API Wrappers (DTO 반환용 래퍼 함수)
# ==============================================================================

async def run_realtime_pipeline(initial_state: dict, config: dict = None) -> dict:
    """[실시간 처리] 파이프라인 실행 후 API 계층에 필요한 핵심 속성만 필터링하여 리턴"""
    full_state = await realtime_graph.ainvoke(initial_state, config=config)
    return {
        "message_id": full_state.get("message_id"),
        "final_urgency": full_state.get("final_urgency"),
        "judgment_rationale": full_state.get("judgment_rationale"),
        "should_store": full_state.get("should_store"),
        "storable_summary": full_state.get("storable_summary")
    }

__all__ = ["realtime_graph", "run_realtime_pipeline"]
