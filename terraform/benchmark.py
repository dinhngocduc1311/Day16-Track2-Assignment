#!/usr/bin/env python3
import argparse
import json
import os
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


SEED = 42
THREADS = min(2, os.cpu_count() or 1)  # t3.medium has 2 vCPUs.


def best_f1_threshold(y_true, probabilities):
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    f1 = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-12)
    return float(thresholds[int(np.argmax(f1))])


def predict_probabilities(model, features, threads):
    return model.predict_proba(
        features,
        num_iteration=model.best_iteration_,
        num_threads=threads,
    )[:, 1]


def self_test():
    labels = np.array([0, 0, 1, 1])
    probabilities = np.array([0.10, 0.40, 0.35, 0.80])
    threshold = best_f1_threshold(labels, probabilities)
    tuned_f1 = f1_score(labels, probabilities >= threshold)
    default_f1 = f1_score(labels, probabilities >= 0.5)
    assert 0 <= threshold <= 1 and tuned_f1 >= default_f1
    print("Self-test OK")


def benchmark(data_path, output_path):
    started = time.perf_counter()
    dtypes = {
        "Time": "float32",
        "Amount": "float32",
        "Class": "int8",
        **{f"V{index}": "float32" for index in range(1, 29)},
    }
    data = pd.read_csv(data_path, dtype=dtypes)
    if "Class" not in data:
        raise ValueError("Dataset is missing the Class target column")
    if data.shape != (284_807, 31):
        raise ValueError(f"Expected dataset shape (284807, 31), got {data.shape}")
    if data.isna().any().any() or set(data["Class"].unique()) != {0, 1}:
        raise ValueError("Dataset must have binary Class values (0/1) and no missing values")

    class_counts = data["Class"].value_counts().to_dict()
    if class_counts != {0: 284_315, 1: 492}:
        raise ValueError(f"Unexpected Class distribution: {class_counts}")

    labels = data.pop("Class").to_numpy()
    features = np.ascontiguousarray(data.to_numpy(dtype=np.float32, copy=False))
    load_seconds = time.perf_counter() - started

    train_val_x, test_x, train_val_y, test_y = train_test_split(
        features, labels, test_size=0.20, random_state=SEED, stratify=labels
    )
    train_x, validation_x, train_y, validation_y = train_test_split(
        train_val_x, train_val_y, test_size=0.125, random_state=SEED, stratify=train_val_y
    )

    negatives, positives = np.bincount(train_y, minlength=2)
    class_imbalance_ratio = float(negatives / positives)
    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=1000,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=SEED,
        n_jobs=THREADS,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )

    started = time.perf_counter()
    model.fit(
        train_x,
        train_y,
        eval_set=[(validation_x, validation_y)],
        eval_metric="average_precision",
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
    )
    training_seconds = time.perf_counter() - started

    validation_probabilities = predict_probabilities(model, validation_x, THREADS)
    threshold = best_f1_threshold(validation_y, validation_probabilities)
    test_probabilities = predict_probabilities(model, test_x, THREADS)
    test_predictions = (test_probabilities >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(test_y, test_predictions, labels=[0, 1]).ravel()

    one_row = test_x[:1]
    batch = test_x[:1000]
    for _ in range(10):
        predict_probabilities(model, one_row, 1)
    latency_ms = []
    for _ in range(200):
        started_ns = time.perf_counter_ns()
        predict_probabilities(model, one_row, 1)
        latency_ms.append((time.perf_counter_ns() - started_ns) / 1_000_000)

    for _ in range(3):
        predict_probabilities(model, batch, THREADS)
    batch_repetitions = 20
    started = time.perf_counter()
    for _ in range(batch_repetitions):
        predict_probabilities(model, batch, THREADS)
    batch_seconds = time.perf_counter() - started

    result = {
        "environment": {
            "rows": int(len(labels)),
            "features": int(features.shape[1]),
            "fraud_rows": int(class_counts[1]),
            "missing_values": 0,
            "logical_cpu_count": os.cpu_count(),
            "lightgbm_threads": THREADS,
            "random_seed": SEED,
            "split": {"train": int(len(train_y)), "validation": int(len(validation_y)), "test": int(len(test_y))},
        },
        "timing_seconds": {
            "load_data": round(load_seconds, 6),
            "training": round(training_seconds, 6),
        },
        "training": {
            "best_iteration": int(model.best_iteration_),
            "class_imbalance_ratio": round(class_imbalance_ratio, 6),
            "decision_threshold": round(threshold, 8),
        },
        "metrics": {
            "roc_auc": round(float(roc_auc_score(test_y, test_probabilities)), 8),
            "pr_auc": round(float(average_precision_score(test_y, test_probabilities)), 8),
            "accuracy": round(float(accuracy_score(test_y, test_predictions)), 8),
            "f1_score": round(float(f1_score(test_y, test_predictions)), 8),
            "precision": round(float(precision_score(test_y, test_predictions, zero_division=0)), 8),
            "recall": round(float(recall_score(test_y, test_predictions, zero_division=0)), 8),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        },
        "inference": {
            "single_row_median_ms": round(float(np.median(latency_ms)), 6),
            "single_row_p95_ms": round(float(np.percentile(latency_ms, 95)), 6),
            "batch_size": int(len(batch)),
            "batch_average_ms": round(batch_seconds * 1000 / batch_repetitions, 6),
            "throughput_rows_per_second": round(len(batch) * batch_repetitions / batch_seconds, 2),
        },
    }
    output_path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")

    rows = [
        ("Data load time", f"{result['timing_seconds']['load_data']:.3f} s"),
        ("Training time", f"{result['timing_seconds']['training']:.3f} s"),
        ("Best iteration", result["training"]["best_iteration"]),
        ("Decision threshold", f"{result['training']['decision_threshold']:.6f}"),
        ("AUC-ROC", f"{result['metrics']['roc_auc']:.6f}"),
        ("PR-AUC", f"{result['metrics']['pr_auc']:.6f}"),
        ("Accuracy", f"{result['metrics']['accuracy']:.6f}"),
        ("F1-Score", f"{result['metrics']['f1_score']:.6f}"),
        ("Precision", f"{result['metrics']['precision']:.6f}"),
        ("Recall", f"{result['metrics']['recall']:.6f}"),
        ("Latency 1 row (median)", f"{result['inference']['single_row_median_ms']:.3f} ms"),
        ("Latency 1 row (p95)", f"{result['inference']['single_row_p95_ms']:.3f} ms"),
        ("Throughput batch 1000", f"{result['inference']['throughput_rows_per_second']:.2f} rows/s"),
    ]
    print("\nLIGHTGBM BENCHMARK RESULTS")
    print("-" * 58)
    for name, value in rows:
        print(f"{name:<32} {value:>25}")
    print("-" * 58)
    print(f"Result written to: {output_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="LightGBM benchmark for Credit Card Fraud Detection")
    parser.add_argument("--data", type=Path, default=Path("creditcard.csv"))
    parser.add_argument("--output", type=Path, default=Path("benchmark_result.json"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.data.is_file():
        parser.error(f"Không tìm thấy dataset: {args.data}")
    benchmark(args.data, args.output)


if __name__ == "__main__":
    main()
