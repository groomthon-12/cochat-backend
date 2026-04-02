import os
from typing import List, Dict, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres.vectorstores import PGVector

def compute_rrf(dense_results: List[Dict[str, Any]], sparse_results: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) 알고리즘을 이용해 두 검색 결과를 융합합니다.
    
    Args:
        dense_results: [{"id": "문서고유ID", "content": "문서내용", "score": float}, ...]
        sparse_results: [{"id": "문서고유ID", "content": "문서내용", "score": float}, ...]
        k: RRF 하이퍼파라미터 (일반적으로 60 사용 권장)
    Returns:
        fused_results: RRF Score 기준으로 정렬된 통합 문서 리스트
    """
    rrf_scores = {}
    doc_lookup = {}
    
    # 1. 밀집(Dense) 벡터 순위에 따른 점수 합산
    for rank, doc in enumerate(dense_results, start=1):
        doc_id = doc.get("id")
        if not doc_id:
            continue
        doc_lookup[doc_id] = doc
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        
    # 2. 희소(Sparse/BM25) 벡터 순위에 따른 점수 누적 합산
    for rank, doc in enumerate(sparse_results, start=1):
        doc_id = doc.get("id")
        if not doc_id:
            continue
        doc_lookup[doc_id] = doc
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        
    # 3. 누적 점수 높은 순으로 최종 정렬
    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 4. 정렬된 ID를 바탕으로 결과 조립
    fused_results = []
    for doc_id, score in sorted_docs:
        fused_doc = doc_lookup[doc_id].copy()
        fused_doc["rrf_score"] = score
        fused_results.append(fused_doc)
        
    return fused_results


async def asearch_hybrid_rrf(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """하이브리드 검색 및 RRF 병합 수행 유틸리티 (실제 PostgreSQL pgvector 연결)"""
    
    # 1. DB 환경변수 준비 (langchain-postgres 접속용 URI로 포맷 변환)
    # 로컬 테스트용 기본값 제공
    db_url = os.getenv("DATABASE_URL", "postgresql://cochat:cochat_dev@localhost:5432/cochat")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://")
    elif db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        
    # 2. 임베딩 모델 초기화 (검색 텍스트를 벡터로 변환)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    try:
        # 3. Vector DB 커넥션 및 Dense Search
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name="message_guidelines",
            connection=db_url,
            use_jsonb=True,
        )
        
        # 비동기 검색 (Dense)
        dense_docs = await vector_store.asimilarity_search_with_score(query, k=10)
        dense_results = [
            {"id": str(doc.metadata.get("id", i)), "content": doc.page_content, "score": score} 
            for i, (doc, score) in enumerate(dense_docs)
        ]
    except Exception as e:
        print(f"⚠️ Vector DB 조회 실패 (테이블이 비어있거나 생성되지 않음): {e}")
        dense_results = []
    
    # 4. 희소(Sparse/BM25) 검색
    # TODO: Postgres Full-Text Search(to_tsvector) 또는 로컬 ElasticSearch 연동
    sparse_results = []
    
    # 5. RRF 융합 로직 태우기
    if not dense_results and not sparse_results:
        return []
        
    fused_results = compute_rrf(dense_results, sparse_results)
    
    return fused_results[:top_k]


def search_cross_encoder_rerank(candidates: List[Dict[str, Any]], query: str, top_k: int = 2) -> List[Dict[str, Any]]:
    """[High/Normal 전용] Cross-Encoder를 통한 정밀 재랭킹 (Mockup)"""
    
    # TODO: candidates 각 항목에 대해 query와의 Pair-wise 유사도를 Cross-Encoder 모델로 계산하여 재정렬
    # reranked = cross_encoder.predict([(query, c["content"]) for c in candidates])
    
    return candidates[:top_k]
