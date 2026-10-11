"""Transaction categorisation evaluation (spec 10.4): unseen-merchant and known-merchant tests.

Protocol
- A seeded sample of at most ``max_rows`` transactions (scale guard for multi-million rows).
- Merchant-group split: ``GroupShuffleSplit`` on ``merchant_id`` holds out about 30% of merchants.
  All rows of a merchant land on the same side, so unseen merchants never appear in training.
- Known-merchant holdout: a seeded 20% of the rows of the training merchants is held out from
  fitting. The known-merchant test therefore uses merchants the classifier has seen, but not
  the rows it was fitted on.
- Every model is fitted only on the fit rows, and the brand dictionary is built from the fit rows.
- Compared models: the hybrid (rules, then TF-IDF + logistic regression), the same model without
  rules, and the plain TF-IDF + logistic regression on raw text.

Synthetic-data caveat: the merchant catalogue and noise come from the Greenr generator.
Results show generalisation within that generator, not performance on real bank data.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupShuffleSplit

from greenr.models.transaction_classifier import (
    BOUNDARY_RULE_DOCS,
    CATEGORY_VALUES,
    METHOD_RULE,
    TransactionCategoriser,
)

MAX_EVAL_ROWS = 300_000
UNSEEN_MERCHANT_FRACTION = 0.3
KNOWN_HOLDOUT_FRACTION = 0.2
_SHORT_CODES = {
    "FUEL": "FUEL", "ELECTRICITY": "ELEC", "GAS": "GAS", "PUBLIC_TRANSPORT": "PT",
    "HOME_IMPROVEMENT": "HOME", "AUTOMOTIVE": "AUTO", "UTILITIES": "UTIL", "OTHER": "OTHER",
}


def evaluate_categoriser(
    descriptions: Sequence[str],
    true_categories: Sequence[str],
    merchant_ids: Sequence[str],
    seed: int,
    *,
    max_rows: int = MAX_EVAL_ROWS,
    unseen_fraction: float = UNSEEN_MERCHANT_FRACTION,
    known_fraction: float = KNOWN_HOLDOUT_FRACTION,
) -> dict[str, Any]:
    """Run the merchant-group and known-merchant evaluation and return a JSON-serialisable dict.

    ``true_categories`` and ``merchant_ids`` are evaluation-only truth columns, aligned row by row
    with ``descriptions``. They must never be passed into a feature pipeline.
    """
    desc = np.asarray(list(descriptions), dtype=object)
    truth = np.asarray([str(getattr(c, "value", c)) for c in true_categories], dtype=object)
    merchants = np.asarray(list(merchant_ids), dtype=object)
    if not len(desc) == len(truth) == len(merchants):
        raise ValueError("descriptions, true_categories and merchant_ids must have equal length")
    if len(desc) == 0:
        raise ValueError("no rows to evaluate")
    unknown = sorted(set(truth.tolist()) - set(CATEGORY_VALUES))
    if unknown:
        raise ValueError(f"unknown transaction categories: {unknown[:5]}")

    rng = np.random.default_rng(seed)
    n_available = len(desc)
    sampled = n_available > max_rows
    if sampled:
        keep = np.sort(rng.choice(n_available, size=max_rows, replace=False))
        desc, truth, merchants = desc[keep], truth[keep], merchants[keep]

    splitter = GroupShuffleSplit(n_splits=1, test_size=unseen_fraction, random_state=seed)
    train_pos, unseen_pos = next(splitter.split(np.zeros(len(desc)), truth, merchants))
    if train_pos.size == 0 or unseen_pos.size == 0:
        raise ValueError("merchant split left one side empty; need more merchants")

    known_rng = np.random.default_rng([seed, 1])
    shuffled = known_rng.permutation(train_pos)
    n_known = int(round(known_fraction * shuffled.size))
    if n_known < 1 or n_known >= shuffled.size:
        raise ValueError("known-merchant holdout is empty or swallows the training rows")
    known_pos = np.sort(shuffled[:n_known])
    fit_pos = np.sort(shuffled[n_known:])

    fit_desc, fit_truth = desc[fit_pos], truth[fit_pos]
    hybrid = TransactionCategoriser(seed=seed).fit(fit_desc, fit_truth)
    model_only = TransactionCategoriser(use_rules=False, seed=seed).fit(fit_desc, fit_truth)
    plain = TransactionCategoriser(normalise=False, use_rules=False, seed=seed).fit(fit_desc, fit_truth)

    models = {
        "hybrid": _score(hybrid, desc, truth, unseen_pos, known_pos),
        "model_only_normalised": _score(model_only, desc, truth, unseen_pos, known_pos),
        "plain_tfidf_lr_raw": _score(plain, desc, truth, unseen_pos, known_pos),
    }
    merchant_category = _merchant_categories(merchants, truth)
    comparison = {
        "hybrid_minus_plain_macro_f1_unseen": _delta(models, "hybrid", "plain_tfidf_lr_raw", "unseen_merchants", "macro_f1"),
        "hybrid_minus_plain_weighted_f1_unseen": _delta(models, "hybrid", "plain_tfidf_lr_raw", "unseen_merchants", "weighted_f1"),
        "hybrid_minus_plain_macro_f1_known": _delta(models, "hybrid", "plain_tfidf_lr_raw", "known_merchants", "macro_f1"),
        "hybrid_minus_plain_weighted_f1_known": _delta(models, "hybrid", "plain_tfidf_lr_raw", "known_merchants", "weighted_f1"),
        "hybrid_minus_model_only_macro_f1_unseen": _delta(models, "hybrid", "model_only_normalised", "unseen_merchants", "macro_f1"),
        "hybrid_minus_model_only_macro_f1_known": _delta(models, "hybrid", "model_only_normalised", "known_merchants", "macro_f1"),
    }
    return {
        "version": TransactionCategoriser.version,
        "seed": int(seed),
        "rows": {
            "available": int(n_available),
            "used": int(len(desc)),
            "sampled": bool(sampled),
            "max_rows": int(max_rows),
        },
        "split": {
            "method": "GroupShuffleSplit on merchant_id; seeded row holdout of training merchants for known-merchant test",
            "unseen_merchant_fraction": float(unseen_fraction),
            "known_holdout_fraction": float(known_fraction),
            "merchants_total": int(len(set(merchants.tolist()))),
            "merchants_train": int(len(set(merchants[train_pos].tolist()))),
            "merchants_unseen": int(len(set(merchants[unseen_pos].tolist()))),
            "rows_fit": int(fit_pos.size),
            "rows_known_holdout": int(known_pos.size),
            "rows_unseen": int(unseen_pos.size),
            "merchants_per_category": {
                "train": _count_by_category(merchant_category, set(merchants[train_pos].tolist())),
                "unseen": _count_by_category(merchant_category, set(merchants[unseen_pos].tolist())),
            },
        },
        "rules": {
            "min_rule_count": hybrid.min_rule_count,
            "rule_purity": hybrid.rule_purity,
            "brand_dictionary_keys": len(hybrid.rules),
            "boundary_rules": [
                {"name": name, "category": category, "description": description}
                for name, category, description in BOUNDARY_RULE_DOCS
            ],
        },
        "labels": list(CATEGORY_VALUES),
        "models": models,
        "comparison": comparison,
    }


def write_report(results: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    """Write ``transaction_eval.json`` and ``TRANSACTION_CATEGORISATION.md`` into ``out_dir``."""
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "transaction_eval.json"
    md_path = target / "TRANSACTION_CATEGORISATION.md"
    json_path.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(results), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def _score(model: TransactionCategoriser, desc: np.ndarray, truth: np.ndarray,
           unseen_pos: np.ndarray, known_pos: np.ndarray) -> dict[str, Any]:
    blocks: dict[str, Any] = {}
    for name, pos in (("unseen_merchants", unseen_pos), ("known_merchants", known_pos)):
        prediction = model.predict(desc[pos])
        blocks[name] = _metrics_block(
            truth[pos],
            prediction["category"].to_numpy(dtype=object),
            prediction["method"].to_numpy(dtype=object),
        )
    return blocks


def _metrics_block(y_true: np.ndarray, y_pred: np.ndarray, methods: np.ndarray) -> dict[str, Any]:
    labels = list(CATEGORY_VALUES)
    present = [c for c in labels if c in set(y_true.tolist()) | set(y_pred.tolist())]
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0)
    per_category: dict[str, dict[str, Any]] = {}
    for i, category in enumerate(labels):
        if category in present:
            per_category[category] = {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
        else:
            per_category[category] = {"precision": None, "recall": None, "f1": None, "support": 0}
    by_rule = methods == METHOD_RULE
    correct = y_true == y_pred
    return {
        "rows": int(y_true.size),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, labels=present, average="weighted", zero_division=0)),
        "per_category": per_category,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "rule_coverage": float(by_rule.mean()),
        "rule_accuracy": float(correct[by_rule].mean()) if by_rule.any() else None,
        "model_accuracy": float(correct[~by_rule].mean()) if (~by_rule).any() else None,
        "method_counts": {"RULE": int(by_rule.sum()), "MODEL": int((~by_rule).sum())},
    }


def _merchant_categories(merchants: np.ndarray, truth: np.ndarray) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for merchant, category in zip(merchants.tolist(), truth.tolist(), strict=True):
        mapping.setdefault(merchant, category)
    return mapping


def _count_by_category(merchant_category: dict[str, str], merchant_set: set[str]) -> dict[str, int]:
    counts = {category: 0 for category in CATEGORY_VALUES}
    for merchant in merchant_set:
        counts[merchant_category[merchant]] += 1
    return counts


def _delta(models: dict[str, Any], left: str, right: str, split: str, metric: str) -> float:
    return float(models[left][split][metric] - models[right][split][metric])


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _f(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _render_markdown(results: dict[str, Any]) -> str:
    rows, split, rules = results["rows"], results["split"], results["rules"]
    models = results["models"]
    hybrid = models["hybrid"]
    lines: list[str] = []
    add = lines.append

    add("# Transaction categorisation evaluation")
    add("")
    add("> Synthetic data only. These figures describe generalisation within the Greenr generator's "
        "merchant catalogue. They do not establish categorisation accuracy on real bank transactions.")
    add("")
    sample_note = " (seeded sample)" if rows["sampled"] else ""
    add(f"Categoriser `{results['version']}` · seed {results['seed']} · "
        f"{rows['used']:,} of {rows['available']:,} transactions evaluated{sample_note}.")
    add("")
    add("## Headline")
    add("")
    add("| Model | Unseen macro F1 | Unseen weighted F1 | Known macro F1 | Known weighted F1 | Rule coverage (unseen) |")
    add("|---|---|---|---|---|---|")
    labels = {
        "hybrid": "Hybrid: brand rules and boundary rules, then TF-IDF + LR",
        "model_only_normalised": "TF-IDF + LR on normalised text (no rules)",
        "plain_tfidf_lr_raw": "Plain TF-IDF + LR on raw text (baseline)",
    }
    for key, label in labels.items():
        u, k = models[key]["unseen_merchants"], models[key]["known_merchants"]
        add(f"| {label} | {_f(u['macro_f1'])} | {_f(u['weighted_f1'])} | "
            f"{_f(k['macro_f1'])} | {_f(k['weighted_f1'])} | {_pct(u['rule_coverage'])} |")
    add("")
    comparison = results["comparison"]
    add(f"Hybrid minus plain baseline: macro F1 {comparison['hybrid_minus_plain_macro_f1_unseen']:+.3f} on unseen "
        f"merchants and {comparison['hybrid_minus_plain_macro_f1_known']:+.3f} on known merchants.")
    add("")
    add("## Split")
    add("")
    add(f"- Method: {split['method']}.")
    add(f"- Merchants: {split['merchants_total']} total, {split['merchants_train']} in training, "
        f"{split['merchants_unseen']} held out as unseen.")
    add(f"- Rows: {split['rows_fit']:,} fit, {split['rows_known_holdout']:,} known-merchant holdout, "
        f"{split['rows_unseen']:,} unseen-merchant test.")
    add("- Merchants per category (train / unseen): " + ", ".join(
        f"{c} {split['merchants_per_category']['train'][c]}/{split['merchants_per_category']['unseen'][c]}"
        for c in results["labels"]) + ".")
    add("")
    add("## Per-category results (hybrid)")
    add("")
    add("| Category | Unseen precision | Unseen recall | Unseen F1 | Unseen support | "
        "Known precision | Known recall | Known F1 | Known support |")
    add("|---|---|---|---|---|---|---|---|---|")
    unseen_pc = hybrid["unseen_merchants"]["per_category"]
    known_pc = hybrid["known_merchants"]["per_category"]
    for c in results["labels"]:
        u, k = unseen_pc[c], known_pc[c]
        add(f"| {c} | {_f(u['precision'])} | {_f(u['recall'])} | {_f(u['f1'])} | {u['support']:,} | "
            f"{_f(k['precision'])} | {_f(k['recall'])} | {_f(k['f1'])} | {k['support']:,} |")
    add("")
    add("## Confusion matrix (hybrid, unseen merchants)")
    add("")
    add("Rows are the true category and columns the predicted category. Codes: "
        + ", ".join(f"{_SHORT_CODES[c]} = {c}" for c in results["labels"]) + ".")
    add("")
    header = "| True \\ predicted | " + " | ".join(_SHORT_CODES[c] for c in results["labels"]) + " |"
    add(header)
    add("|---|" + "---|" * len(results["labels"]))
    for c, row in zip(results["labels"], hybrid["unseen_merchants"]["confusion_matrix"], strict=True):
        add(f"| {_SHORT_CODES[c]} | " + " | ".join(f"{int(v):,}" for v in row) + " |")
    add("")
    add("## Deterministic rules")
    add("")
    add(f"- Brand dictionary: {rules['brand_dictionary_keys']} leading-token keys "
        f"(1 to 3 tokens, longest match wins). A key is used only when it has at least "
        f"{rules['min_rule_count']} training rows and at least {100 * rules['rule_purity']:.0f}% share one category.")
    add("- Boundary rules run before the dictionary, in this order:")
    for rule in rules["boundary_rules"]:
        add(f"  - `{rule['name']}` -> {rule['category']}: {rule['description']}")
    add("")
    add("| Rule accuracy and coverage | Unseen merchants | Known merchants |")
    add("|---|---|---|")
    for label, field in (("Rule coverage", "rule_coverage"), ("Rule accuracy", "rule_accuracy"),
                         ("Model accuracy on non-rule rows", "model_accuracy")):
        add(f"| {label} | {_pct(models['hybrid']['unseen_merchants'][field])} | "
            f"{_pct(models['hybrid']['known_merchants'][field])} |")
    add("")
    add("## Limitations")
    add("")
    add("- Training labels come from the generator's merchant catalogue, so the classifier learns that catalogue's naming conventions.")
    add("- Single-token brand keys are the main collision risk: a token that is pure in training can start an unseen merchant name. "
        "The rule-accuracy row above measures this.")
    add("- Macro and weighted F1 average only over categories present in the true or predicted labels of the split.")
    add("")
    return "\n".join(lines)
