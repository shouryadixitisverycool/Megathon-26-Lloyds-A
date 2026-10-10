"""Keep developer credentials out of tests; provider tests use explicit mocks."""

import pytest


@pytest.fixture(autouse=True)
def isolate_llm_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GREENPATH_LLM_API_KEY", raising=False)
