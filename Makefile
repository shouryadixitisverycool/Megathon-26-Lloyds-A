.PHONY: setup test test-trained test-impact api app all pipeline data perturbed train evaluate evaluate-llm scenarios evaluate-system schemas build manifest
.NOTPARALLEL: all

CUSTOMERS ?= 4000

setup:
	uv sync --locked

test:
	GREENPATH_PROVIDER=fixture uv run --locked pytest

test-trained:
	GREENPATH_LLM_API_KEY= GREENPATH_PROVIDER=fixture uv run --locked pytest \
		tests/integration/test_trained_acceptance.py tests/integration/test_trained_safety.py \
		tests/integration/test_artifact_providers.py tests/integration/test_demo_providers.py \
		tests/api/test_api.py::test_default_demo_wires_real_services_and_explicit_history

test-impact:
	uv run --locked pytest tests/impact

api:
	uv run --locked uvicorn greenpath.api.main:app --host 127.0.0.1 --port 8000

app:
	uv run --locked python -m greenpath.demo.run

evaluate-llm:
	uv run --locked python -m greenpath.llm.evaluate

pipeline:
	uv run --locked python -m greenpath.pipelines.run all --customers $(CUSTOMERS)

data:
	uv run --locked python -m greenpath.data_generation --customers $(CUSTOMERS)

perturbed:
	uv run --locked python -m greenpath.data_generation --perturbed --customers $(CUSTOMERS)

train:
	uv run --locked python -m greenpath.pipelines.run train

evaluate:
	uv run --locked python -m greenpath.pipelines.run evaluate

schemas:
	uv run --locked python -m greenpath.contracts.export_schemas

build:
	uv build --wheel

evaluate-system:
	uv run --locked python -m greenpath.extensions.evaluate

scenarios:
	uv run --locked python -m greenpath.demo.evaluate

manifest:
	uv run --locked python -m greenpath.pipelines.run manifest

all: setup pipeline test evaluate-llm scenarios evaluate-system manifest
