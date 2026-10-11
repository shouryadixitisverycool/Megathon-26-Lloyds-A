"""Convert GreenPath raw Parquet tables into validated model-ready features."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from greenpath import config
from greenpath.contracts import Product
from greenpath.models.propensity import PRODUCT_FEATURES
from greenpath.models.propensity.features import prepare_matrix
from greenpath.models.transaction_classifier import TransactionCategoriser
from greenpath.pipelines import run
from greenpath.pipelines.leakage_checks import LeakageError, run_all_checks
from greenpath.pipelines.customer360 import build_customer360
from greenpath.pipelines.snapshot_provider import Customer360SnapshotProvider
from greenpath.pipelines.split import make_labels, split_pipeline_customers, write_split_manifest


def cutoff_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("cutoff must use YYYY-MM-DD") from exc


def write_model_inputs(frame, output_dir: Path, cutoff: date) -> dict[str, Path]:
    model_dir = output_dir / "model_inputs"
    model_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for product in Product:
        matrix = prepare_matrix(frame, PRODUCT_FEATURES[product])
        path = model_dir / f"{product.value.lower()}_{cutoff.isoformat()}.parquet"
        matrix.to_parquet(path)
        paths[product.value] = path
    return paths


def preprocess(
    input_dir: Path,
    output_dir: Path,
    cutoff: date,
    categorizer_artifact: Path | None = None,
) -> dict:
    input_dir = input_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    tables = run.load_tables(input_dir)
    run.log(f"loaded {len(tables['customers'])} customers and {len(tables['transactions'])} transactions")

    if categorizer_artifact is not None:
        categorizer_artifact = categorizer_artifact.expanduser().resolve()
        categorizer = TransactionCategoriser.load(categorizer_artifact)
        fitted_categorizer = False
    else:
        reference = run.labelled_reference(tables, config.SEED_MODEL, cutoff=cutoff)
        if reference.empty:
            raise ValueError(f"no labelled transactions are available by {cutoff}")
        categorizer = TransactionCategoriser().fit(
            reference["merchant_description"].tolist(), reference["true_category"].tolist()
        )
        fitted_categorizer = True

    transactions = run.categorise(categorizer, tables["transactions"])
    raw = run.raw_only(tables)
    frame = build_customer360(raw, transactions, cutoff)
    labels = make_labels(
        tables["customer_outcomes"], frame.index, cutoff,
        coverage=tables.get("outcome_observation"),
    )
    split = split_pipeline_customers(frame.index)

    point_in_time = run.point_in_time_check(raw, transactions, frame, cutoff)
    if point_in_time["status"] != "PASS":
        raise LeakageError(f"point-in-time rebuild differs: {point_in_time['differences']}")
    event_sources = run.feature_event_sources(raw, transactions, cutoff)
    leakage = {
        "point_in_time_rebuild": point_in_time,
        "products": {
            product.value: run_all_checks(
                cutoff=cutoff,
                split=split,
                event_sources=event_sources,
                feature_names=PRODUCT_FEATURES[product],
                products=[product],
            )
            for product in Product
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    transactions_path = output_dir / "transactions_categorised.parquet"
    transactions.to_parquet(transactions_path)
    snapshot_path = Customer360SnapshotProvider({cutoff: frame}).save(output_dir)[0]
    labels_path = output_dir / "labels.parquet"
    labels.to_parquet(labels_path)
    split_path = output_dir / "split_manifest.csv"
    split_digest = write_split_manifest(split, split_path)
    model_paths = write_model_inputs(frame, output_dir, cutoff)
    leakage_path = output_dir / "preprocessing_validation.json"
    run.write_json(leakage_path, leakage)

    saved_categorizer = categorizer_artifact
    if fitted_categorizer:
        saved_categorizer = output_dir / "transaction_categoriser.joblib"
        categorizer.save(saved_categorizer)

    result = {
        "cutoff": cutoff.isoformat(),
        "customers": len(frame),
        "transactions": len(transactions),
        "transactions_path": transactions_path,
        "snapshot_path": snapshot_path,
        "labels_path": labels_path,
        "split_path": split_path,
        "split_sha256": split_digest,
        "categorizer_path": saved_categorizer,
        "model_paths": model_paths,
        "validation_path": leakage_path,
    }
    run.log(f"preprocessing passed for {len(frame)} customers at {cutoff}")
    for product, path in model_paths.items():
        run.log(f"{product}: {len(PRODUCT_FEATURES[Product(product)])} features -> {path}")
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=config.RAW_DIR,
                        help=f"raw dataset directory (default: {config.RAW_DIR})")
    parser.add_argument("--output-dir", type=Path, default=config.PROCESSED_DIR,
                        help=f"processed output directory (default: {config.PROCESSED_DIR})")
    parser.add_argument("--cutoff", type=cutoff_date, default=config.FEATURE_CUTOFF,
                        help=f"point-in-time feature cutoff (default: {config.FEATURE_CUTOFF})")
    parser.add_argument("--categorizer-artifact", type=Path,
                        help="load an existing transaction categoriser instead of fitting one")
    args = parser.parse_args(argv)
    preprocess(args.input_dir, args.output_dir, args.cutoff, args.categorizer_artifact)


if __name__ == "__main__":
    main()
