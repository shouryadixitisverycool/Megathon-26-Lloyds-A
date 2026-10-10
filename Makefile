.PHONY: setup test test-impact api app all evaluate scenarios

setup:
	uv sync --locked

test:
	uv run --locked pytest

test-impact:
	uv run --locked pytest tests/impact

api:
	uv run --locked uvicorn greenpath.api.main:app --host 127.0.0.1 --port 8000

app:
	uv run --locked python -m greenpath.demo.run

evaluate:
	uv run --locked python -m greenpath.llm.evaluate

scenarios:
	uv run --locked python -m greenpath.demo.evaluate

all: test evaluate scenarios
