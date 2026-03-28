# MIT License — DocuVault AI
"""Classification accuracy evaluation runner.

Run against the golden dataset to measure per-type, per-language accuracy.
Execute after every prompt change: python tests/eval/run_eval.py

Phase 1 deliverable — you can't improve what you don't measure.
"""
import json
import sys
from pathlib import Path


def load_golden(path: str = "tests/eval/manufacturing_golden.jsonl") -> list[dict]:
    """Load labeled test documents."""
    entries = []
    with open(path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


def evaluate(entries: list[dict], classify_fn) -> dict:
    """Run classification on all entries and compute accuracy.
    
    classify_fn: async callable that takes document text and returns predicted doc_type
    """
    results = {"total": 0, "correct": 0, "by_type": {}, "by_language": {}}
    
    for entry in entries:
        predicted = classify_fn(entry["text"])
        expected = entry["expected_type"]
        language = entry.get("language", "en")
        correct = predicted == expected
        
        results["total"] += 1
        if correct:
            results["correct"] += 1
        
        # Per-type accuracy
        if expected not in results["by_type"]:
            results["by_type"][expected] = {"total": 0, "correct": 0}
        results["by_type"][expected]["total"] += 1
        if correct:
            results["by_type"][expected]["correct"] += 1
        
        # Per-language accuracy
        if language not in results["by_language"]:
            results["by_language"][language] = {"total": 0, "correct": 0}
        results["by_language"][language]["total"] += 1
        if correct:
            results["by_language"][language]["correct"] += 1
    
    # Compute percentages
    results["accuracy"] = results["correct"] / results["total"] if results["total"] > 0 else 0
    for key in ["by_type", "by_language"]:
        for name, data in results[key].items():
            data["accuracy"] = data["correct"] / data["total"] if data["total"] > 0 else 0
    
    return results


def print_report(results: dict) -> None:
    """Print formatted accuracy report."""
    print(f"\n{'='*50}")
    print(f"CLASSIFICATION ACCURACY REPORT")
    print(f"{'='*50}")
    print(f"Overall: {results['correct']}/{results['total']} ({results['accuracy']:.1%})")
    
    print(f"\nBy Document Type:")
    for dtype, data in sorted(results["by_type"].items()):
        print(f"  {dtype:30s} {data['correct']:3d}/{data['total']:3d} ({data['accuracy']:.1%})")
    
    print(f"\nBy Language:")
    for lang, data in sorted(results["by_language"].items()):
        print(f"  {lang:10s} {data['correct']:3d}/{data['total']:3d} ({data['accuracy']:.1%})")
    
    target = 0.90
    status = "PASS" if results["accuracy"] >= target else "FAIL"
    print(f"\nTarget: {target:.0%} | Status: {status}")
    print(f"{'='*50}\n")
    
    if results["accuracy"] < target:
        sys.exit(1)


if __name__ == "__main__":
    entries = load_golden()
    if not entries:
        print("No golden dataset found. Create tests/eval/manufacturing_golden.jsonl first.")
        print("Format: one JSON object per line with 'text', 'expected_type', 'language' fields.")
        sys.exit(0)
    
    # TODO: Replace with actual classify_fn using Claude API
    # For now, this is a placeholder that shows the framework structure
    print(f"Loaded {len(entries)} golden dataset entries.")
    print("To run evaluation, implement classify_fn with your Claude enrichment pipeline.")
