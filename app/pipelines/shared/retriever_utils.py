from typing import List, Dict, Any

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


def search_hybrid_rrf(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """하이브리드 검색 및 RRF 병합 수행 유틸리티 (실제 구현 시 Async I/O 권장)"""
    
    # TODO: 1. Vector DB (Dense) 검색 실행
    # dense_results = db.search_dense(query)
    dense_mock = [
        {"id": "doc_A", "content": "일반 DB 장애 조치 가이드"},
        {"id": "doc_B", "content": "에러 로그 모니터링 메뉴얼"}
    ]
    
    # TODO: 2. BM25 DB (Sparse) 검색 실행 (밀집 벡터와 병렬로 실행하면 빠름)
    # sparse_results = db.search_bm25(query)
    sparse_mock = [
        {"id": "doc_C", "content": "Error 221 치명적 로그 피드백 지침"},  # 정확한 키워드 매칭은 Sparse가 잘 잡음!
        {"id": "doc_A", "content": "일반 DB 장애 조치 가이드"}
    ]
    
    # 3. RRF 병합
    fused_results = compute_rrf(dense_mock, sparse_mock)
    
    return fused_results[:top_k]


def search_cross_encoder_rerank(candidates: List[Dict[str, Any]], query: str, top_k: int = 2) -> List[Dict[str, Any]]:
    """[High/Normal 전용] Cross-Encoder를 통한 정밀 재랭킹 (Mockup)"""
    
    # TODO: candidates 각 항목에 대해 query와의 Pair-wise 유사도를 Cross-Encoder 모델로 계산하여 재정렬
    # reranked = cross_encoder.predict([(query, c["content"]) for c in candidates])
    
    return candidates[:top_k]
