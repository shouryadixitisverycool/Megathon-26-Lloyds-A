import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from greenpath.partners import PartnerCatalogue, get_promoted_catalogue, load_catalogue

CATALOGUE_PATH = Path("src/greenpath/partners/catalogue.json")
EXPECTED_CATEGORIES = {"EV_FINANCE", "SOLAR_FINANCE", "GREEN_HOME"}
TOP_LEVEL_FIELDS = {
    "version",
    "reviewed_on",
    "disclaimer",
    "commercial_disclaimer",
    "products",
}
OPTION_FIELDS = {
    "id", "partner", "relationship", "title", "summary", "highlights",
    "suitability", "disclosure", "revenue_path", "source", "destination_url",
    "cta_label", "placeholder",
    "promoted",
}


def _payload():
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def test_packaged_catalogue_exposes_two_promoted_placeholder_concepts_per_category():
    catalogue = load_catalogue()

    assert {category.product for category in catalogue.products} == EXPECTED_CATEGORIES
    assert {
        category.product: len(category.options) for category in catalogue.products
    } == {"EV_FINANCE": 2, "SOLAR_FINANCE": 2, "GREEN_HOME": 2}
    for category in catalogue.products:
        for option in category.options:
            assert option.promoted is True
            assert option.placeholder is True
            assert option.source is None
            assert option.destination_url is None
            assert option.partner.startswith("Demo ")
            assert "Proposed referral fee on completion" in option.revenue_path
            assert "optional finance or lease income" in option.revenue_path
            assert "No arrangement or revenue exists" in option.revenue_path
            assert (
                "not a live" in option.disclosure
                or "not an installation" in option.disclosure
            )


def test_serialized_response_has_exact_contract_and_no_unpromoted_candidates(tmp_path):
    payload = _payload()
    hidden_candidate = deepcopy(payload["products"][0]["options"][0])
    hidden_candidate.update(id="candidate-not-promoted", promoted=False)
    payload["products"][0]["options"].append(hidden_candidate)
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    response = load_catalogue(path).model_dump(mode="json")

    assert set(response) == TOP_LEVEL_FIELDS
    assert [set(category) for category in response["products"]] == [
        {"product", "title", "subtitle", "hero_tag", "options"}
    ] * 3
    assert all(
        set(option) == OPTION_FIELDS and option["promoted"]
        for category in response["products"]
        for option in category["options"]
    )
    assert "candidate-not-promoted" not in json.dumps(response)


def test_each_load_returns_independent_models(tmp_path):
    first = load_catalogue()
    second = load_catalogue()
    first.products[0].options[0].highlights.append("mutated by caller")

    assert "mutated by caller" not in second.products[0].options[0].highlights

    override = tmp_path / "catalogue.json"
    override.write_text(CATALOGUE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    third = get_promoted_catalogue(override)
    third.products[0].options.clear()
    assert len(load_catalogue(override).products[0].options) == 2


def test_explicit_path_precedes_environment_override(tmp_path, monkeypatch):
    payload = _payload()
    payload["products"] = payload["products"][:1]
    env_path = tmp_path / "environment.json"
    env_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("GREENPATH_PARTNER_CATALOGUE", str(env_path))

    assert len(load_catalogue().products) == 1
    assert len(load_catalogue(CATALOGUE_PATH).products) == 3


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(reviewed_on="11/10/2026"),
        lambda data: data.update(unexpected="not in the exact contract"),
        lambda data: data["products"].append(deepcopy(data["products"][0])),
        lambda data: data["products"][1]["options"][0].update(
            id=data["products"][0]["options"][0]["id"]
        ),
        lambda data: data["products"][0]["options"][0].update(title="  "),
        lambda data: data["products"][0]["options"][0].update(
            destination_url="http://provider.example/offer"
        ),
        lambda data: data["products"][0]["options"][0].update(
            destination_url="https://user:password@provider.example/offer"
        ),
        lambda data: data["products"][0]["options"][0].update(
            destination_url="https://"
        ),
        lambda data: data["products"][0]["options"][0].update(
            destination_url="https://provider.example/offer"
        ),
    ],
)
def test_catalogue_rejects_invalid_contract_duplicate_keys_and_unsafe_links(change):
    payload = _payload()
    change(payload)

    with pytest.raises(ValidationError):
        PartnerCatalogue.model_validate(payload)


def test_candidate_validation_happens_before_promoted_filtering(tmp_path):
    payload = _payload()
    hidden = deepcopy(payload["products"][0]["options"][0])
    hidden.update(
        id="hidden-invalid",
        promoted=False,
        destination_url="http://unsafe.example/",
    )
    payload["products"][0]["options"].append(hidden)
    path = tmp_path / "catalogue.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_catalogue(path)


def test_non_placeholder_real_product_requires_provenance_and_safe_links():
    payload = _payload()
    real_option = payload["products"][0]["options"][0]
    real_option.update(
        placeholder=False,
        partner="Selected mobility provider",
        relationship="Referral partner",
        disclosure="Reviewed terms apply; see the provider's offer information.",
        revenue_path="Referral fee terms separately agreed.",
        source={
            "label": "Provider offer information",
            "url": "https://provider.example/offer",
        },
        destination_url="https://provider.example/apply",
    )

    valid = PartnerCatalogue.model_validate(payload)
    assert valid.products[0].options[0].placeholder is False

    real_option["source"]["url"] = "https://person:secret@provider.example/offer"
    with pytest.raises(ValidationError):
        PartnerCatalogue.model_validate(payload)


def test_real_option_cannot_omit_source_or_destination():
    payload = _payload()
    payload["products"][0]["options"][0]["placeholder"] = False

    with pytest.raises(ValidationError):
        PartnerCatalogue.model_validate(payload)
