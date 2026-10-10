"""Transaction categorisation: deterministic rules first, TF-IDF + logistic regression for the rest (spec 10).

For one raw merchant description the hybrid classifier does the following.

1. ``normalise_description`` removes payment noise (card references, dates, postcodes,
   masked and long digit runs, store numbers, punctuation such as ``*``, and words such as
   CONTACTLESS / DD / POS / VIS) and upper-cases the text.
2. Boundary rules read explicit category evidence in the text, such as fuel, energy or
   servicing markers (``BOUNDARY_RULE_DOCS``). They are hand-written, applied before the
   brand dictionary and have confidence 1.0.
3. The brand dictionary maps a leading-token brand key (1 to 3 tokens, longest match wins)
   to one category. A key is used only when it is unambiguous in the training data: at
   least ``min_rule_count`` rows and at least ``rule_purity`` of them share one category.
4. Anything still unresolved goes to a TF-IDF (word 1-2 grams + char_wb 3-5 grams) logistic
   regression. Its ``category_confidence`` is the predicted maximum probability.

Every description receives exactly one ``TransactionCategory`` value. ``predict`` works on
unique normalised strings, so it stays fast on millions of rows.

Boundary rules, in the order they are checked (first match wins). ``BOUNDARY_RULE_DOCS``
holds the same list in machine-readable form for the evaluation report.

- ``fuel_marker``: PFS, PETROL or UNLEADED anywhere in the text -> FUEL. This is what
  separates a supermarket forecourt ("TESCO PFS") from the supermarket's grocery sales.
  DIESEL is not a marker because it is also a clothing brand.
- ``automotive_service``: TYRES, TYRE, MOT, AUTOCENTRE, AUTOCARE, or the phrases
  CAR SERVICE / CAR SERVICING / CAR WASH / CAR REPAIR / AUTO CENTRE -> AUTOMOTIVE.
- ``dual_fuel``: electricity and gas markers both present -> UTILITIES (bundled supplier).
- ``electricity_only``: ELECTRICITY / ELECTRIC / ELEC with no gas marker -> ELECTRICITY.
  Not applied when a non-supply word (EV charging, electric bikes, appliances) is present.
- ``gas_only``: GAS with no electricity marker -> GAS.
- ``bundled_utility``: ENERGY, UTILITIES, UTILITY, WATER or the phrase DUAL FUEL, with no
  fuel-specific evidence -> UTILITIES.

A description that normalises to nothing (for example "CARD 1234") is OTHER with confidence 0.0.

Training uses the unique (normalised text, category) pairs with row-count sample weights.
The weights apply class balancing at row level, which is the same as
``class_weight="balanced"`` on the full row set. The model sees every non-empty training row,
including rows the dictionary covers, so it also handles brands outside the dictionary.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from greenpath.config import SEED_MODEL
from greenpath.contracts import TransactionCategory

CATEGORY_VALUES: tuple[str, ...] = tuple(member.value for member in TransactionCategory)
METHOD_RULE = "RULE"
METHOD_MODEL = "MODEL"
DEFAULT_MIN_RULE_COUNT = 20
DEFAULT_RULE_PURITY = 0.98
_MAX_KEY_TOKENS = 3

_FUEL = TransactionCategory.FUEL.value
_ELECTRICITY = TransactionCategory.ELECTRICITY.value
_GAS = TransactionCategory.GAS.value
_AUTOMOTIVE = TransactionCategory.AUTOMOTIVE.value
_UTILITIES = TransactionCategory.UTILITIES.value
_OTHER = TransactionCategory.OTHER.value

BOUNDARY_RULE_DOCS: tuple[tuple[str, str, str], ...] = (
    ("fuel_marker", _FUEL,
     "PFS, PETROL or UNLEADED token anywhere in the text (e.g. 'TESCO PFS', 'SHELL PETROL')."),
    ("automotive_service", _AUTOMOTIVE,
     "TYRES, TYRE, MOT, AUTOCENTRE, AUTOCARE, or CAR SERVICE / CAR SERVICING / CAR WASH / "
     "CAR REPAIR / AUTO CENTRE phrases (e.g. 'KWIK FIT TYRES')."),
    ("dual_fuel", _UTILITIES,
     "Electricity and gas markers both present (dual-fuel supplier)."),
    ("electricity_only", _ELECTRICITY,
     "ELECTRICITY / ELECTRIC / ELEC with no gas marker and no non-supply word "
     "(EV charging, electric bikes, appliances)."),
    ("gas_only", _GAS,
     "GAS with no electricity marker (e.g. 'CADENT GAS')."),
    ("bundled_utility", _UTILITIES,
     "ENERGY / UTILITIES / UTILITY / WATER, or the phrase DUAL FUEL, with no fuel-specific evidence "
     "(e.g. 'OCTOPUS ENERGY')."),
)

# DIESEL is deliberately not a fuel marker: it is also a clothing brand.
_FUEL_MARKERS = frozenset({"PFS", "PETROL", "UNLEADED"})
_AUTOMOTIVE_MARKERS = frozenset({"TYRES", "TYRE", "MOT", "AUTOCENTRE", "AUTOCARE"})
_AUTOMOTIVE_PHRASES = frozenset({
    ("CAR", "SERVICE"), ("CAR", "SERVICING"), ("CAR", "WASH"), ("CAR", "REPAIR"),
    ("AUTO", "CENTRE"),
})
_ELECTRICITY_MARKERS = frozenset({"ELECTRICITY", "ELECTRIC", "ELEC"})
_GAS_MARKERS = frozenset({"GAS"})
# Words that show "electric" is not a metered electricity supply.
_NON_SUPPLY_TOKENS = frozenset({
    "CHARGING", "CHARGER", "CHARGE", "VEHICLE", "VEHICLES", "EV", "POD", "BIKE", "BIKES",
    "SCOOTER", "SCOOTERS", "CAR", "CARS", "APPLIANCE", "APPLIANCES",
})
_BUNDLED_MARKERS = frozenset({"ENERGY", "UTILITIES", "UTILITY", "WATER"})
_BUNDLED_PHRASES = frozenset({("DUAL", "FUEL")})

# Payment and channel words that carry no merchant identity. CARD is not listed: a bare
# CARD can be part of a merchant name ("CARD FACTORY"), so only card references are removed.
_NOISE_TOKENS = frozenset({
    "CONTACTLESS", "DD", "DEB", "DEBIT", "CRD", "POS", "VIS", "VISA", "MC",
    "MASTERCARD", "PMT", "PAYMENT", "FPI", "BGC", "GB", "GBR",
})
_LEADING_CONNECTIVES = frozenset({"TO", "FROM"})
_MONTH = (r"(?:JANUARY|JAN|FEBRUARY|FEB|MARCH|MAR|APRIL|APR|MAY|JUNE|JUN|JULY|JUL|"
          r"AUGUST|AUG|SEPTEMBER|SEPT|SEP|OCTOBER|OCT|NOVEMBER|NOV|DECEMBER|DEC)(?![A-Z])")
_APOSTROPHE_RE = re.compile(r"['`]")
_CARD_RE = re.compile(r"\b(?:CARD|CRD)\s*(?:ENDING\s*|NO\.?\s*)?[X*]*\d{2,}\b")
_CARD_PHRASE_RE = re.compile(r"\bCARD\s+(?:PAYMENT|PURCHASE|PMT|TRANSACTION|TXN)\b")
_STORE_RE = re.compile(r"\b(?:STORE|STR|BRANCH|BR)\s*(?:NO\.?\s*)?\d+\b")  # "STORE 1234"; keeps "STORES"
_DATE_RES = (
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(r"\b\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?\b"),
    re.compile(r"\b\d{1,2}\s*" + _MONTH + r"\s*\d{2,4}\b"),
    re.compile(r"\b" + _MONTH + r"\s*\d{4}\b"),
)
_POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b")
_MASK_RE = re.compile(r"\bX{3,}\d*\b")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_LONG_DIGITS_RE = re.compile(r"\d{3,}")
_SHORT_DIGITS_RE = re.compile(r"(?<![A-Z0-9])\d{1,2}(?![A-Z0-9])")


def normalise_description(text: str) -> str:
    """Return the brand-level form of a raw merchant description.

    Upper-cases the text, removes card references, dates, postcodes, masked and long digit
    runs, store numbers, punctuation and payment noise words, and collapses whitespace.
    Missing values (None, NaN) become the empty string.
    """
    if not isinstance(text, str):
        if text is None or (pd.api.types.is_scalar(text) and pd.isna(text)):
            return ""
        text = str(text)
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").upper()
    s = _APOSTROPHE_RE.sub("", s)
    s = _CARD_RE.sub(" ", s)
    s = _CARD_PHRASE_RE.sub(" ", s)
    s = _STORE_RE.sub(" ", s)
    for pattern in _DATE_RES:
        s = pattern.sub(" ", s)
    s = _POSTCODE_RE.sub(" ", s)
    s = _MASK_RE.sub(" ", s)
    s = _NON_ALNUM_RE.sub(" ", s)
    s = _LONG_DIGITS_RE.sub(" ", s)
    s = _SHORT_DIGITS_RE.sub(" ", s)
    tokens = [token for token in s.split() if token not in _NOISE_TOKENS]
    while tokens and tokens[0] in _LEADING_CONNECTIVES:  # "PAYMENT TO X" -> "X"
        tokens.pop(0)
    return " ".join(tokens)


def _boundary_category(tokens: Sequence[str]) -> str | None:
    """Return the category from the hand-written boundary rules, or None (see BOUNDARY_RULE_DOCS)."""
    words = set(tokens)
    bigrams = set(zip(tokens, tokens[1:], strict=False))
    if words & _FUEL_MARKERS:
        return _FUEL
    if words & _AUTOMOTIVE_MARKERS or bigrams & _AUTOMOTIVE_PHRASES:
        return _AUTOMOTIVE
    electricity = bool(words & _ELECTRICITY_MARKERS) and not (words & _NON_SUPPLY_TOKENS)
    gas = bool(words & _GAS_MARKERS)
    if electricity and gas:
        return _UTILITIES
    if electricity:
        return _ELECTRICITY
    if gas:
        return _GAS
    if words & _BUNDLED_MARKERS or bigrams & _BUNDLED_PHRASES:
        return _UTILITIES
    return None


def _rule_category(tokens: list[str], brand_rules: dict[str, str]) -> str | None:
    """Boundary rules first, then the longest matching leading-token brand key."""
    boundary = _boundary_category(tokens)
    if boundary is not None:
        return boundary
    for size in range(min(_MAX_KEY_TOKENS, len(tokens)), 0, -1):
        category = brand_rules.get(" ".join(tokens[:size]))
        if category is not None:
            return category
    return None


def _build_brand_rules(counts: pd.DataFrame, min_count: int, purity: float) -> dict[str, str]:
    """Map each leading-token brand key whose training rows are unambiguous to its category."""
    support: dict[str, Counter[str]] = defaultdict(Counter)
    for text, category, n in zip(counts["text"], counts["category"], counts["n"], strict=True):
        tokens = str(text).split()
        for size in range(1, min(_MAX_KEY_TOKENS, len(tokens)) + 1):
            support[" ".join(tokens[:size])][str(category)] += int(n)
    rules: dict[str, str] = {}
    for key, by_category in support.items():
        total = sum(by_category.values())
        if total < min_count:
            continue
        category, top = by_category.most_common(1)[0]
        if top / total >= purity:
            rules[key] = category
    return rules


def _build_pipeline(seed: int) -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                                 token_pattern=r"(?u)\b\w+\b")),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(max_iter=1000, random_state=seed)),
    ])


def _fit_model(trainable: pd.DataFrame, seed: int) -> tuple[Pipeline | None, str | None]:
    """Fit the TF-IDF + logistic regression on unique (text, category) pairs.

    Returns (pipeline, None), or (None, category) when only one category is present.
    """
    per_class = trainable.groupby("category")["n"].sum()
    classes = [str(c) for c in per_class.index]
    if len(classes) == 1:
        return None, classes[0]
    total = float(per_class.sum())
    balance = {str(c): total / (len(classes) * float(n)) for c, n in per_class.items()}
    weights = (trainable["n"].to_numpy(dtype=float)
               * trainable["category"].map(balance).to_numpy(dtype=float))
    pipeline = _build_pipeline(seed)
    pipeline.fit(trainable["text"].to_numpy(dtype=object),
                 trainable["category"].to_numpy(dtype=object),
                 clf__sample_weight=weights)
    return pipeline, None


def _text_or_empty(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None or (pd.api.types.is_scalar(value) and pd.isna(value)):
        return ""
    return str(value)


def _as_text_array(values: Iterable[object]) -> np.ndarray:
    items = list(values)
    out = np.empty(len(items), dtype=object)
    for i, value in enumerate(items):
        out[i] = _text_or_empty(value)
    return out


def _as_label_array(values: Iterable[object]) -> np.ndarray:
    items = [str(getattr(value, "value", value)) for value in values]
    out = np.empty(len(items), dtype=object)
    out[:] = items
    unknown = sorted(set(items) - set(CATEGORY_VALUES))
    if unknown:
        raise ValueError(f"unknown transaction categories: {unknown[:5]}")
    return out


def _normalise_array(raw: np.ndarray) -> np.ndarray:
    """Normalise each distinct raw string once, then map back to rows."""
    codes, uniques = pd.factorize(raw)
    normalised = np.empty(len(uniques), dtype=object)
    for i, text in enumerate(uniques):
        normalised[i] = normalise_description(text)
    return normalised[codes]


class TransactionCategoriser:
    """Hybrid categoriser: boundary rules and brand dictionary first, then TF-IDF + logistic regression.

    ``normalise`` and ``use_rules`` exist for ablations and baselines. The default
    configuration is the hybrid classifier. ``use_rules=False`` gives TF-IDF + logistic
    regression on normalised text. ``normalise=False, use_rules=False`` gives the plain
    TF-IDF + logistic regression baseline on raw text.
    """

    version: str = "txn_cat_v1"

    def __init__(
        self,
        *,
        normalise: bool = True,
        use_rules: bool = True,
        min_rule_count: int = DEFAULT_MIN_RULE_COUNT,
        rule_purity: float = DEFAULT_RULE_PURITY,
        seed: int = SEED_MODEL,
    ) -> None:
        if use_rules and not normalise:
            raise ValueError("rules operate on normalised text; set normalise=True with use_rules=True")
        if min_rule_count < 1:
            raise ValueError("min_rule_count must be >= 1")
        if not 0.0 < rule_purity <= 1.0:
            raise ValueError("rule_purity must be in (0, 1]")
        self.normalise = normalise
        self.use_rules = use_rules
        self.min_rule_count = int(min_rule_count)
        self.rule_purity = float(rule_purity)
        self.seed = int(seed)
        self._rules: dict[str, str] = {}
        self._pipeline: Pipeline | None = None
        self._constant: str | None = None
        self._fitted = False

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def rules(self) -> dict[str, str]:
        """Brand dictionary: leading-token key -> category (copy)."""
        return dict(self._rules)

    def fit(self, descriptions: Sequence[str], categories: Sequence[str]) -> TransactionCategoriser:
        """Build the brand dictionary and fit the classifier on training rows only."""
        raw = _as_text_array(descriptions)
        labels = _as_label_array(categories)
        if raw.shape[0] != labels.shape[0]:
            raise ValueError("descriptions and categories differ in length")
        if raw.shape[0] == 0:
            raise ValueError("no training rows")
        texts = _normalise_array(raw) if self.normalise else raw
        counts = (pd.DataFrame({"text": texts, "category": labels})
                  .groupby(["text", "category"], sort=False).size()
                  .reset_index(name="n"))
        self._rules = (_build_brand_rules(counts, self.min_rule_count, self.rule_purity)
                       if self.use_rules else {})
        trainable = counts[counts["text"] != ""]
        if trainable.empty:
            raise ValueError("no non-empty descriptions to train on")
        self._pipeline, self._constant = _fit_model(trainable, self.seed)
        self._fitted = True
        return self

    def predict(self, descriptions: Sequence[str]) -> pd.DataFrame:
        """Return one row per description with category, category_confidence and method.

        The index is the input Series' index when a Series is passed, otherwise a RangeIndex, so
        the result aligns with the transactions it came from.
        """
        if not self._fitted:
            raise RuntimeError("TransactionCategoriser is not fitted")
        index = descriptions.index if isinstance(descriptions, pd.Series) else None
        raw = _as_text_array(descriptions)
        if raw.size == 0:
            categories = np.empty(0, dtype=object)
            confidence = np.empty(0, dtype=float)
            methods = np.empty(0, dtype=object)
        else:
            codes, uniques = pd.factorize(raw)
            texts = _normalise_array(uniques) if self.normalise else uniques
            norm_codes, norm_uniques = pd.factorize(texts)
            unique_categories, unique_confidence, unique_methods = self._resolve(list(norm_uniques))
            rows = norm_codes[codes]
            categories = unique_categories[rows]
            confidence = unique_confidence[rows]
            methods = unique_methods[rows]
        return pd.DataFrame({
            "category": categories,
            "category_confidence": confidence,
            "method": methods,
        }, index=index if index is not None else pd.RangeIndex(raw.size))

    def save(self, path: str | Path) -> None:
        """Write the fitted categoriser with joblib. Load only artefacts this project produced."""
        if not self._fitted:
            raise RuntimeError("cannot save an unfitted TransactionCategoriser")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "version": self.version,
            "normalise": self.normalise,
            "use_rules": self.use_rules,
            "min_rule_count": self.min_rule_count,
            "rule_purity": self.rule_purity,
            "seed": self.seed,
            "rules": dict(self._rules),
            "pipeline": self._pipeline,
            "constant": self._constant,
        }
        joblib.dump(payload, target)

    @classmethod
    def load(cls, path: str | Path) -> TransactionCategoriser:
        payload = joblib.load(Path(path))
        if payload.get("version") != cls.version:
            raise ValueError(f"categoriser version {payload.get('version')!r} != {cls.version!r}")
        obj = cls(
            normalise=payload["normalise"],
            use_rules=payload["use_rules"],
            min_rule_count=payload["min_rule_count"],
            rule_purity=payload["rule_purity"],
            seed=payload["seed"],
        )
        obj._rules = dict(payload["rules"])
        obj._pipeline = payload["pipeline"]
        obj._constant = payload["constant"]
        obj._fitted = True
        return obj

    def _resolve(self, texts: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Categorise distinct normalised texts: rules first, the model for the rest."""
        n = len(texts)
        categories = np.empty(n, dtype=object)
        confidence = np.ones(n, dtype=float)
        methods = np.empty(n, dtype=object)
        pending: list[int] = []
        for i, text in enumerate(texts):
            if not text:
                categories[i], confidence[i], methods[i] = _OTHER, 0.0, METHOD_MODEL
                continue
            hit = _rule_category(text.split(), self._rules) if self.use_rules else None
            if hit is None:
                pending.append(i)
            else:
                categories[i], methods[i] = hit, METHOD_RULE
        if pending:
            labels, probabilities = self._model_predict([texts[i] for i in pending])
            categories[pending] = labels
            confidence[pending] = probabilities
            methods[pending] = METHOD_MODEL
        return categories, confidence, methods

    def _model_predict(self, texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
        if self._pipeline is None:
            if self._constant is None:
                raise RuntimeError("TransactionCategoriser is not fitted")
            return (np.full(len(texts), self._constant, dtype=object),
                    np.ones(len(texts), dtype=float))
        proba = self._pipeline.predict_proba(np.asarray(texts, dtype=object))
        best = proba.argmax(axis=1)
        classes = np.asarray(self._pipeline.classes_, dtype=object)
        return classes[best], proba[np.arange(len(best)), best]
