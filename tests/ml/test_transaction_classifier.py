"""Transaction categoriser: normalisation, rules, model behaviour, persistence and unseen-merchant evaluation."""

import json

import numpy as np
import pandas as pd
import pytest

from greenr.contracts import TransactionCategory
from greenr.evaluation.transaction import evaluate_categoriser, write_report
from greenr.models.transaction_classifier import (
    CATEGORY_VALUES,
    METHOD_MODEL,
    METHOD_RULE,
    TransactionCategoriser,
    normalise_description,
)

FUEL = TransactionCategory.FUEL.value
ELECTRICITY = TransactionCategory.ELECTRICITY.value
GAS = TransactionCategory.GAS.value
PUBLIC_TRANSPORT = TransactionCategory.PUBLIC_TRANSPORT.value
HOME_IMPROVEMENT = TransactionCategory.HOME_IMPROVEMENT.value
AUTOMOTIVE = TransactionCategory.AUTOMOTIVE.value
UTILITIES = TransactionCategory.UTILITIES.value
OTHER = TransactionCategory.OTHER.value

# Synthetic merchant catalogue for these tests only (brand -> category, rows per merchant).
MERCHANTS: dict[str, tuple[str, int]] = {
    "SHELL": (FUEL, 40), "ESSO": (FUEL, 40), "BP": (FUEL, 40),
    "TESCO PFS": (FUEL, 30), "ASDA PETROL": (FUEL, 30), "SAINSBURYS PFS": (FUEL, 30),
    "TESCO STORES": (OTHER, 40), "ASDA GROCERY": (OTHER, 40), "GROCER MART": (OTHER, 40),
    "COSTA COFFEE": (OTHER, 40), "NETFLIX": (OTHER, 40), "AMAZON MKTP": (OTHER, 40),
    "GREGGS": (OTHER, 40), "BOOTS PHARMACY": (OTHER, 40),
    "SSE ELECTRICITY": (ELECTRICITY, 40), "NPOWER ELECTRIC": (ELECTRICITY, 40),
    "CADENT GAS": (GAS, 40), "SCOTTISH GAS NETWORKS": (GAS, 40),
    "OCTOPUS ENERGY": (UTILITIES, 40), "EDF ENERGY": (UTILITIES, 40), "THAMES WATER": (UTILITIES, 40),
    "HALFORDS": (AUTOMOTIVE, 40), "KWIK FIT TYRES": (AUTOMOTIVE, 40), "CITY CAR SERVICE": (AUTOMOTIVE, 40),
    "B&Q": (HOME_IMPROVEMENT, 40), "SCREWFIX": (HOME_IMPROVEMENT, 40), "WICKES": (HOME_IMPROVEMENT, 40),
    "EASTSIDE HARDWARE": (HOME_IMPROVEMENT, 40), "TRADE HARDWARE CO": (HOME_IMPROVEMENT, 40),
    "HARDWARE DEPOT": (HOME_IMPROVEMENT, 40),
    "TFL": (PUBLIC_TRANSPORT, 40), "TRAINLINE": (PUBLIC_TRANSPORT, 40),
    "NATIONAL RAIL": (PUBLIC_TRANSPORT, 40), "CITY BUS": (PUBLIC_TRANSPORT, 40),
}
_PREFIXES = ["", "CONTACTLESS ", "POS ", "DD ", "VIS "]
_SUFFIXES = ["", " 1234", " CARD 5678 12/03/26", " SW1A 1AA", " LONDON GB", " 0231 12MAR26"]


def build_fixture(seed: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (descriptions, true categories, merchant ids) with noisy variants of each brand."""
    rng = np.random.default_rng(seed)
    descriptions, categories, merchants = [], [], []
    for brand, (category, rows) in MERCHANTS.items():
        for _ in range(rows):
            prefix = _PREFIXES[rng.integers(len(_PREFIXES))]
            suffix = _SUFFIXES[rng.integers(len(_SUFFIXES))]
            descriptions.append(f"{prefix}{brand}{suffix}")
            categories.append(category)
            merchants.append(brand)
    return (np.array(descriptions, dtype=object), np.array(categories, dtype=object),
            np.array(merchants, dtype=object))


@pytest.fixture(scope="module")
def fitted() -> TransactionCategoriser:
    descriptions, categories, _ = build_fixture()
    return TransactionCategoriser(min_rule_count=5).fit(descriptions, categories)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CONTACTLESS SHELL 4421 LONDON GB", "SHELL LONDON"),
        ("POS TESCO PFS 1234 CARD 5678 12/03/26", "TESCO PFS"),
        ("DD OCTOPUS ENERGY 0012345678", "OCTOPUS ENERGY"),
        ("shell*petrol 0231", "SHELL PETROL"),
        ("VIS 12MAR26 HALFORDS SW1A 1AA", "HALFORDS"),
        ("CARD 1234", ""),
        ("  multiple   spaces  ", "MULTIPLE SPACES"),
        ("SAINSBURY'S 1234", "SAINSBURYS"),
        ("PAYMENT TO CADENT GAS 0001 GB", "CADENT GAS"),
        ("CARD XXXX1234 PAYPAL *ETSY 1 MAY 2026", "PAYPAL ETSY"),
        ("DECATHLON 1234", "DECATHLON"),
        ("TFL TRAVEL CH 2025-11-03", "TFL TRAVEL CH"),
        ("CARD FACTORY 1234", "CARD FACTORY"),  # a merchant name, not noise
        ("CARD PAYMENT TO CADENT GAS 0001", "CADENT GAS"),
        ("POS CARD PURCHASE TFL 4421", "TFL"),
        ("TESCO STORE 1234 LONDON", "TESCO LONDON"),
        ("TESCO STORES 1234", "TESCO STORES"),
        ("O2 STORE 0099", "O2"),
    ],
)
def test_normalise_strips_payment_noise(raw, expected):
    assert normalise_description(raw) == expected


def test_normalise_treats_missing_values_as_empty():
    assert normalise_description(None) == ""
    assert normalise_description(float("nan")) == ""


def test_brand_rules_resolve_known_brands_under_new_noise(fitted):
    out = fitted.predict(["CONTACTLESS SHELL 4421 LONDON GB", "POS ESSO 0231 CARD 1234 12/03/26",
                          "HALFORDS 9911 SW1A 1AA"])
    assert out["category"].tolist() == [FUEL, FUEL, AUTOMOTIVE]
    assert out["method"].tolist() == [METHOD_RULE] * 3
    assert np.all(out["category_confidence"].to_numpy() == 1.0)


def test_boundary_rule_takes_precedence_over_brand_dictionary(fitted):
    # GROCER MART is pure OTHER in training, so the dictionary would say OTHER.
    assert fitted.rules.get("GROCER MART") == OTHER
    out = fitted.predict(["GROCER MART PETROL 1234"])
    assert out.iloc[0]["category"] == FUEL
    assert out.iloc[0]["method"] == METHOD_RULE


def test_boundary_rules_for_energy_and_servicing(fitted):
    cases = {
        "OCTOPUS ENERGY 0012345678": UTILITIES,
        "SSE ELECTRICITY 1234": ELECTRICITY,
        "CADENT GAS 1234": GAS,
        "BRITISH GAS ELECTRIC 99": UTILITIES,  # dual-fuel evidence
        "KWIK FIT TYRES 4421": AUTOMOTIVE,
        "CITY CAR SERVICE 4": AUTOMOTIVE,
    }
    out = fitted.predict(list(cases))
    assert out["category"].tolist() == list(cases.values())
    assert set(out["method"]) == {METHOD_RULE}


@pytest.mark.parametrize("description", [
    "ELECTRIC VEHICLE CHARGING POINT 77",
    "ELECTRIC BIKES SHOP 4",
    "DIESEL STORE 9",  # clothing brand: DIESEL must not act as a fuel marker
])
def test_non_supply_or_non_fuel_words_do_not_trigger_boundary_rules(fitted, description):
    out = fitted.predict([description])
    assert not (out.iloc[0]["category"] in (ELECTRICITY, FUEL) and out.iloc[0]["method"] == METHOD_RULE)


def test_dual_fuel_phrase_is_bundled_utility(fitted):
    out = fitted.predict(["DUAL FUEL ENERGY SUPPLY 12"])
    assert out.iloc[0]["category"] == UTILITIES
    assert out.iloc[0]["method"] == METHOD_RULE


def test_single_category_training_predicts_that_category():
    model = TransactionCategoriser().fit(["ALPHA SHOP 1", "ALPHA SHOP 2", "BETA 9"], [OTHER, OTHER, OTHER])
    out = model.predict(["UNKNOWN STORE 5", "ALPHA SHOP 3"])  # 2 and 3 rows: below the default rule support
    assert out["category"].tolist() == [OTHER, OTHER]
    assert out["category_confidence"].tolist() == [1.0, 1.0]
    assert out["method"].tolist() == [METHOD_MODEL, METHOD_MODEL]


def test_model_handles_unseen_brand_with_descriptive_token(fitted):
    unseen = ["NORTHGATE HARDWARE SUPPLY", "SOUTHBANK RAIL TICKETS"]
    out = fitted.predict(unseen)
    assert out["category"].tolist() == [HOME_IMPROVEMENT, PUBLIC_TRANSPORT]
    assert out["method"].tolist() == [METHOD_MODEL, METHOD_MODEL]
    assert np.all((out["category_confidence"] > 0) & (out["category_confidence"] <= 1))


def test_brand_rules_need_both_purity_and_support():
    descriptions = (["MIXED BRAND 1234"] * 30 + ["MIXED BRAND 4321"] * 30  # 50/50: impure
                    + ["THIN BRAND 1"] * 2                                  # below min_rule_count
                    + ["PURE BRAND 1"] * 10)                                 # pure and frequent
    categories = [FUEL] * 30 + [OTHER] * 30 + [GAS] * 2 + [HOME_IMPROVEMENT] * 10
    model = TransactionCategoriser(min_rule_count=5).fit(descriptions, categories)
    assert "MIXED BRAND" not in model.rules
    assert "MIXED" not in model.rules
    assert "THIN BRAND" not in model.rules
    assert model.rules.get("PURE BRAND") == HOME_IMPROVEMENT
    assert model.predict(["MIXED BRAND 77"]).iloc[0]["method"] == METHOD_MODEL


def test_exactly_one_valid_category_per_row(fitted):
    descriptions = ["CONTACTLESS SHELL 1 LONDON", "", "CARD 1234", "XYZ LOCAL SHOP 9",
                    "NORTHGATE HARDWARE SUPPLY", None, "TESCO STORES 42", "SSE ELECTRICITY 1234"]
    out = fitted.predict(descriptions)
    assert list(out.columns) == ["category", "category_confidence", "method"]
    assert len(out) == len(descriptions)
    assert out["category"].isin(CATEGORY_VALUES).all()
    assert out["category"].notna().all()
    assert out["method"].isin([METHOD_RULE, METHOD_MODEL]).all()
    assert out["category_confidence"].between(0.0, 1.0).all()
    assert out.index.equals(pd.RangeIndex(len(descriptions)))


def test_predict_keeps_series_index_and_handles_empty_input(fitted):
    descriptions = pd.Series(["CONTACTLESS SHELL 1", "NORTHGATE HARDWARE SUPPLY"], index=[101, 77])
    out = fitted.predict(descriptions)
    assert out.index.tolist() == [101, 77]
    assert out["category"].tolist() == [FUEL, HOME_IMPROVEMENT]
    empty = fitted.predict([])
    assert len(empty) == 0
    assert list(empty.columns) == ["category", "category_confidence", "method"]


def test_predict_deduplicates_repeated_descriptions(fitted):
    base = ["CONTACTLESS SHELL 1 LONDON", "NORTHGATE HARDWARE SUPPLY", "XYZ LOCAL SHOP 9", "CARD 1"]
    many = base * 25_000  # 100k rows, only four distinct descriptions
    out = fitted.predict(many)
    assert len(out) == len(many)
    single = fitted.predict(base)
    expected = single.iloc[[i % len(base) for i in range(len(many))]].reset_index(drop=True)
    pd.testing.assert_frame_equal(out, expected)


def test_save_and_load_round_trip(fitted, tmp_path):
    path = tmp_path / "txn.joblib"
    fitted.save(path)
    loaded = TransactionCategoriser.load(path)
    probe = ["CONTACTLESS SHELL 4421 LONDON GB", "NORTHGATE HARDWARE SUPPLY", "XYZ LOCAL SHOP 9", "CARD 1"]
    before, after = fitted.predict(probe), loaded.predict(probe)
    assert loaded.version == "txn_cat_v1"
    assert after["category"].tolist() == before["category"].tolist()
    assert after["method"].tolist() == before["method"].tolist()
    np.testing.assert_allclose(after["category_confidence"].to_numpy(),
                               before["category_confidence"].to_numpy())


def test_fit_and_predict_validate_inputs():
    with pytest.raises(ValueError, match="unknown transaction categories"):
        TransactionCategoriser().fit(["SHELL 1"], ["PETROL_STATION"])
    with pytest.raises(ValueError, match="differ in length"):
        TransactionCategoriser().fit(["SHELL 1", "ESSO 2"], [FUEL])
    with pytest.raises(RuntimeError, match="not fitted"):
        TransactionCategoriser().predict(["SHELL 1"])


def test_unseen_merchant_evaluation_runs_and_is_consistent(tmp_path):
    descriptions, categories, merchants = build_fixture()
    results = evaluate_categoriser(descriptions, categories, merchants, seed=43)

    split = results["split"]
    assert split["merchants_total"] == len(MERCHANTS)
    assert split["merchants_train"] + split["merchants_unseen"] == len(MERCHANTS)
    assert 0 < split["merchants_unseen"] < len(MERCHANTS)
    assert split["rows_fit"] + split["rows_known_holdout"] + split["rows_unseen"] == len(descriptions)
    assert results["labels"] == list(CATEGORY_VALUES)

    for model_name in ("hybrid", "model_only_normalised", "plain_tfidf_lr_raw"):
        block = results["models"][model_name]
        for split_name in ("unseen_merchants", "known_merchants"):
            metrics = block[split_name]
            assert 0.0 <= metrics["macro_f1"] <= 1.0
            assert 0.0 <= metrics["weighted_f1"] <= 1.0
            matrix = np.asarray(metrics["confusion_matrix"])
            assert matrix.shape == (len(CATEGORY_VALUES), len(CATEGORY_VALUES))
            per_category_support = [metrics["per_category"][c]["support"] for c in CATEGORY_VALUES]
            assert matrix.sum(axis=1).tolist() == per_category_support
    assert results["models"]["plain_tfidf_lr_raw"]["unseen_merchants"]["rule_coverage"] == 0.0
    assert results["models"]["hybrid"]["unseen_merchants"]["rule_coverage"] > 0.0

    paths = write_report(results, tmp_path)
    loaded = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert loaded["models"]["hybrid"]["unseen_merchants"]["macro_f1"] == results["models"]["hybrid"]["unseen_merchants"]["macro_f1"]
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Unseen macro F1" in markdown and "Confusion matrix" in markdown


def test_models_are_fitted_only_on_training_merchants(monkeypatch):
    descriptions, categories, merchants = build_fixture()
    fitted_texts: list[str] = []
    original_fit = TransactionCategoriser.fit

    def spy_fit(self, descs, cats):
        fitted_texts.extend(str(d) for d in descs)
        return original_fit(self, descs, cats)

    monkeypatch.setattr(TransactionCategoriser, "fit", spy_fit)
    results = evaluate_categoriser(descriptions, categories, merchants, seed=43)

    # Every brand name is embedded in its descriptions, so a brand appears in the fit data iff it is a training merchant.
    brands_in_fit = {brand for brand in MERCHANTS if any(brand in text for text in fitted_texts)}
    assert len(brands_in_fit) == results["split"]["merchants_train"]
    assert len(MERCHANTS) - len(brands_in_fit) == results["split"]["merchants_unseen"]


def test_evaluation_is_seeded_and_samples_large_inputs():
    descriptions, categories, merchants = build_fixture()
    first = evaluate_categoriser(descriptions, categories, merchants, seed=43, max_rows=500)
    second = evaluate_categoriser(descriptions, categories, merchants, seed=43, max_rows=500)
    assert first["rows"] == {"available": len(descriptions), "used": 500, "sampled": True, "max_rows": 500}
    assert first["models"] == second["models"]
    assert first["split"] == second["split"]
