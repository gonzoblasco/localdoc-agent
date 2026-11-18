"""Run the 18-question eval against the local agent."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, "src")
from agent.agent import answer_question  # noqa: E402
from agent.db import init_db  # noqa: E402

DB = Path("data/index.db")
QUESTIONS = Path("eval/questions.yaml")
OUT = Path(os.environ.get("NIDO_EVAL_OUT", "eval/results.json"))


def keyword_ok(keywords, answer):
    a = (answer or "").lower()
    return all(k.lower() in a for k in keywords)


def main():
    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    conn = init_db(DB)
    results = []
    for q in questions:
        t0 = time.perf_counter()
        try:
            r = answer_question(conn, q["question"])
            latency = time.perf_counter() - t0
            answer = r["answer"]
            ok = keyword_ok(q.get("keywords", []), answer)
            results.append(
                {
                    "id": q["id"],
                    "type": q["type"],
                    "question": q["question"],
                    "expected": q.get("expected", ""),
                    "answer": answer,
                    "correct": ok,
                    "citations": len(r["citations"]),
                    "latency_s": round(latency, 2),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "id": q["id"],
                    "type": q["type"],
                    "question": q["question"],
                    "error": str(exc),
                    "correct": False,
                }
            )
        last = results[-1]
        print(f"{last['id']} {'OK' if last['correct'] else 'FAIL'} {last.get('latency_s', '')}s", flush=True)
    conn.close()

    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    with_citations = sum(1 for r in results if r.get("citations", 0) > 0)
    latencies = [r["latency_s"] for r in results if "latency_s" in r]
    p50 = sorted(latencies)[len(latencies) // 2] if latencies else None
    summary = {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 3) if total else 0,
        "with_citations": with_citations,
        "p50_latency_s": p50,
        "model": os.environ.get("NIDO_MODEL", "gemma4:12b-mlx"),
        "results": results,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAccuracy: {correct}/{total} ({summary['accuracy'] * 100:.1f}%)")
    print(f"P50 latency: {p50}s")
    print(f"Results: {OUT}")


if __name__ == "__main__":
    main()
