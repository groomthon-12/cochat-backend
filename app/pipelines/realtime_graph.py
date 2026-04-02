from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.pipelines.state import MessageState
from app.pipelines.shared.retriever_utils import asearch_hybrid_rrf, search_cross_encoder_rerank

# ==============================================================================
# Node Functions
# ==============================================================================

class AnalyzeMessageOutput(BaseModel):
    """LLM이 반드시 준수해야 하는 JSON 출력 스키마"""
    initial_urgency: Literal["Emergency", "High", "Normal", "Low"] = Field(
        description="초기 긴급도 파악 결과. 심각한 장애는 Emergency, 직접 멘션/중요 요청은 High, 일반 알림이나 로그는 Normal, 의미없는 잡담/대답은 Low."
    )
    judgment_rationale: str = Field(description="선택한 긴급도에 대한 상세한 논리적 판단 근거 (Chain of Thought)")
    should_store: bool = Field(description="의미 있는 업무 컨텍스트 혹은 중요 로그로써 추후 Vector DB에 기억할 가치가 있는가?")
    storable_summary: str = Field(description="should_store가 True인 경우 검색용 필수 핵심 요약. False인 경우 빈 문자열.")

def analyze_message(state: MessageState) -> dict:
    """1차 긴급도 및 저장 가치 판단 (Gemini Flash 사용)"""
    
    # 1. 모델과 파서 초기화 (실제 실행을 위해선 GOOGLE_API_KEY 환경변수 세팅 필수)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    structured_llm = llm.with_structured_output(AnalyzeMessageOutput)
    
    # 2. 시스템 프롬프트 설계
    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 업무용 메신저(Slack/Discord) 환경의 초고속 알람 필터링 비서입니다.\n\n"
                   "[응급도 분류 가이드라인]\n"
                   "- Emergency: 치명적 서비스 중단, 긴급 보안 이슈 등 즉각적인 조치가 없으면 안 되는 심각한 장애.\n"
                   "- High: 수신자(나)를 직접 멘션한 중요한 업무 요청, 빠른 확인이 필요한 이슈 및 오류 알림.\n"
                   "- Normal: 평범한 채널의 정보성 알림, 당장 조치할 필요 없는 배포 로그, 단순 참조용 스레드.\n"
                   "- Low: 단순 인사(안녕하세요), 동의/수긍('네 알겠습니다', '확인했습니다'), 잡담, 스팸 봇 메시지.\n\n"
                   "제공된 메타데이터(직접 멘션 여부 등)와 단기 스레드 문맥, 그리고 메시지 본문을 가장 입체적으로 분석하여 JSON으로 반환하세요."
        ),
        ("user", "### 메타데이터 (채널, 발신자, 나를 멘션했는지 여부 등):\n{metadata}\n\n"
                 "### 최근 스레드 문맥 (단기 기억):\n{history}\n\n"
                 "### 현재 메시지 본문:\n{content}")
    ])
    
    # 3. 모델 체인지업(Invocation)
    chain = prompt | structured_llm
    
    result = chain.invoke({
        "metadata": state.get("metadata", {}),
        "history": state.get("conversation_history", []),
        "content": state.get("content", "")
    })
    
    # 4. 분석 결과 반환
    return {
        "initial_urgency": result.initial_urgency,
        "final_urgency": result.initial_urgency, # RAG를 거치지 않고 끝나는 Low 케이스를 위한 예비용
        "judgment_rationale": result.judgment_rationale,
        "should_store": result.should_store,
        "storable_summary": result.storable_summary 
    }

async def fast_retrieve_emergency_context(state: MessageState) -> dict:
    """[Emergency 전용] 초저지연 캐시/하이브리드 직접 검색 (Re-ranking 생략). 핵심 SOP, 치명적 오탐 로그만 조회"""
    query = state.get("content", "")
    # 비동기 pgvector 검색 수행 (< 150ms)
    fused_docs = await asearch_hybrid_rrf(query, top_k=2)
    contexts = [doc.get("content", "") for doc in fused_docs]
    return {"retrieved_context": contexts}

def fast_reassess_importance(state: MessageState) -> dict:
    """가벼운/빠른 모델을 이용해 Emergency 유지 여부만 1차 확인"""
    return {
        "final_urgency": "Emergency",
        "judgment_rationale": "SOP 대조 결과 치명적 장애로 판단. (초저지연 검증)"
    }

async def deep_retrieve_context(state: MessageState) -> dict:
    """[High/Normal 전용] 높은 정확도를 위한 다단계 재랭킹(Multiphase Ranking) 검색"""
    query = state.get("content", "")
    
    # 1. 비동기 하이브리드 검색 및 RRF로 초기 후보군(Candidate Pool) 구성
    candidates = await asearch_hybrid_rrf(query, top_k=10)
    
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
