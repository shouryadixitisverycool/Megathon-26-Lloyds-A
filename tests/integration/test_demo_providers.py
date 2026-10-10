from greenpath._product_contract_mirror import APPROVED_FEATURES, RecommendationState
from greenpath.demo.providers import DemoRepository
from greenpath.impact import Product, build_registry


def test_demo_personas_are_stable_and_explicitly_synthetic():
    repository = DemoRepository()
    snapshots = repository.list_snapshots()
    assert [s.customer_id for s in snapshots] == [f"GP-{i:03}" for i in range(1, 7)]
    assert all(s.synthetic_demo and set(s.features) <= APPROVED_FEATURES for s in snapshots)
    assert {r.state for r in repository.list_history()} == set(RecommendationState)
    assert {r.month for r in repository.list_history()} == {"2025-10", "2025-11", "2025-12"}


def test_provider_reads_are_independent_and_do_not_mutate_fixtures():
    repository = DemoRepository()
    snapshot = repository.get_snapshot("GP-001")
    snapshot.features.clear()
    assert repository.get_snapshot("GP-001").features
    payload = repository.get_impact_input("GP-001", Product.EV_FINANCE)
    payload["charging_electricity"]["value"] = "9999"
    assert repository.get_impact_input("GP-001", Product.EV_FINANCE)["charging_electricity"]["value"] == "1800"
    assert repository.get_snapshot("unknown") is None


def test_demo_impact_payloads_use_bundled_valid_inputs():
    repository = DemoRepository()
    calculators = build_registry()
    for product in Product:
        result = calculators[product].calculate(repository.get_impact_input("GP-001", product))
        assert result.status == ("UNAVAILABLE" if product == Product.PAPERLESS_BANKING else "AVAILABLE")
        missing = calculators[product].calculate(repository.get_impact_input("GP-002", product))
        assert missing.status == "UNAVAILABLE" and missing.value is None
