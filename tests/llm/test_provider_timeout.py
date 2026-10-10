from greenpath.llm.service import ExplanationService


def test_provider_deadline_is_used_unless_explicitly_overridden():
    class Provider:
        timeout_seconds = 30.0

    assert ExplanationService(Provider()).timeout_seconds == 30.0
    assert ExplanationService(Provider(), timeout_seconds=0.02).timeout_seconds == 0.02
    assert ExplanationService().timeout_seconds == 2.0
