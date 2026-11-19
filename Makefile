.PHONY: install run demo demo-ingest demo-search test lint

install:
	uv sync

run:
	uv run python -m src.agent.serve

demo: demo-ingest demo-search

demo-ingest:
	@echo "Running ingestion demo..."
	uv run python -m src.agent.demo_ingest

demo-search:
	@uv run python -c "import sys; sys.path.append('src'); from agent.db import init_db; from agent.retrieve import hybrid_search; conn=init_db('data/index.db'); results=hybrid_search(conn, 'Desarrollo', top_k=3); [print(f\"chunk_id={r['chunk_id']}, document={r.get('document')}, score={r['score']:.4f}\") for r in results]"

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
