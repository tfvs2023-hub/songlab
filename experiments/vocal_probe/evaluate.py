"""Linear-probe comparison of embedding files produced by ``extract.py``.

For every model and every layer (plus the mean over all layers) a standardised logistic regression
is trained with singer-grouped K-fold cross-validation, so test singers are never seen in
training. Reports accuracy / macro-F1 per layer and per-technique recall for the best layer.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def probe(features: np.ndarray, labels: np.ndarray, groups: np.ndarray, folds: int, c: float) -> Dict:
    accs, f1s = [], []
    predictions = np.empty_like(labels)
    for train, test in GroupKFold(n_splits=folds).split(features, labels, groups):
        clf = make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000))
        clf.fit(features[train], labels[train])
        pred = clf.predict(features[test])
        predictions[test] = pred
        accs.append(accuracy_score(labels[test], pred))
        f1s.append(f1_score(labels[test], pred, average="macro"))
    return {
        "acc": float(np.mean(accs)),
        "acc_std": float(np.std(accs)),
        "f1": float(np.mean(f1s)),
        "predictions": predictions,
    }


def evaluate_file(path: Path, folds: int, c: float) -> List[Dict]:
    data = np.load(path)
    emb, labels, singers = data["embeddings"], data["labels"], data["singers"]
    name = f"{data['model']} ({data['checkpoint']})"
    print(f"\n=== {name}: {emb.shape[0]} clips, {emb.shape[1]} layers x {emb.shape[2]} dims ===")

    rows = []
    layers = [(str(i), emb[:, i]) for i in range(emb.shape[1])] + [("mean", emb.mean(axis=1))]
    for layer, features in layers:
        result = probe(features, labels, singers, folds, c)
        rows.append({"model": str(data["model"]), "layer": layer, **result})
        print(f"  layer {layer:>4}: acc {result['acc']:.3f} ± {result['acc_std']:.3f}   macro-F1 {result['f1']:.3f}")

    best = max(rows, key=lambda r: r["acc"])
    print(f"  best: layer {best['layer']} acc {best['acc']:.3f}")
    techniques = [str(t) for t in data["techniques"] if t in set(labels)]
    recalls = recall_score(labels, best["predictions"], labels=techniques, average=None)
    for technique, recall in zip(techniques, recalls):
        print(f"    {technique:<10} recall {recall:.3f}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", type=Path, nargs="+", help=".npz files from extract.py")
    parser.add_argument("--folds", type=int, default=5, help="Singer-grouped CV folds (default: 5)")
    parser.add_argument("--C", type=float, default=1.0, help="Inverse L2 strength for logistic regression")
    parser.add_argument("--csv", type=Path, help="Optional path to write every layer's scores")
    args = parser.parse_args()

    all_rows = [row for path in args.files for row in evaluate_file(path, args.folds, args.C)]

    print("\n=== Summary (best layer per model) ===")
    for model in dict.fromkeys(r["model"] for r in all_rows):
        rows = [r for r in all_rows if r["model"] == model]
        best = max(rows, key=lambda r: r["acc"])
        mean = next(r for r in rows if r["layer"] == "mean")
        print(
            f"  {model:<5} best layer {best['layer']:>2}: acc {best['acc']:.3f} ± {best['acc_std']:.3f}"
            f" | all-layer mean: acc {mean['acc']:.3f}"
        )

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["model", "layer", "acc", "acc_std", "f1"])
            writer.writeheader()
            for row in all_rows:
                writer.writerow({k: row[k] for k in writer.fieldnames})
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
