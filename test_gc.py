import asyncio
import os

from app.pipelines.state import MemoryGCState
from app.pipelines.memory_gc_graph import memory_gc_graph

async def main():
    if not os.getenv("GOOGLE_API_KEY"):
        print("💡 에러: GOOGLE_API_KEY 환경변수가 설정되지 않았습니다!")
        print("💡 .env 파일에 키를 넣거나 터미널에서 export 해주세요.")
        return

    # GC Pipeline은 사실상 초기 상태 변수(state)에 빈 딕셔너리만 넣으면
    # 내부적으로 알아서 DB에서 메모리를 긁어와 처리합니다.
    dummy_state = {}
    config = {"configurable": {"thread_id": "gc_session_01"}}
    
    print("🚀 LangGraph 백그라운드 [메모리 가비지 컬렉션(GC)] 테스트를 시작합니다\n")
    print("-" * 50)
    
    async for event in memory_gc_graph.astream(dummy_state, config=config):
        for node_name, state_update in event.items():
            print(f"🟢 [통과 노드]: {node_name}")
            
            if node_name == "fetch_stale_memories":
                targets = state_update.get('target_memories', [])
                print(f"   👉 Vector DB에서 가장 오래된 알림 요약본 {len(targets)}개를 긁어왔습니다.")
                for tm in targets:
                    occ = tm.get("metadata", {}).get("occurred_at", "미확인")
                    print(f"      - [ID: {tm['id']}] (발생시각: {occ}) {tm['content'][:30]}...")
                    
            elif node_name == "evaluate_memory_relevance":
                evals = state_update.get('evaluation_results', [])
                keep_cnt = sum(1 for e in evals if e["action"] == "keep")
                del_cnt = sum(1 for e in evals if e["action"] == "delete")
                print(f"   🤖 LLM 심사 결과 (총 {len(evals)}개 판단 완료)")
                print(f"      - 보존(Keep): {keep_cnt}개, 파괴(Delete): {del_cnt}개")
                for e in evals:
                    icon = "🔥" if e['action'] == "delete" else "💾"
                    print(f"      [{icon} {e['action'].upper()}] (사유: {e['reason']}) ID: {e['id']}")
                    
            elif node_name == "update_or_delete_vector_db":
                print(f"   🧹 GC 청소 완료 단계 통과")
                
            print("-" * 50)
            
    print("\n✅ GC 파이프라인 그래프 정상 종료 완료.")

if __name__ == "__main__":
    asyncio.run(main())
