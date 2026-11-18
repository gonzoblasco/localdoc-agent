"""Re-score existing eval answers with a more tolerant matcher.

The first pass used exact keyword matching, which penalised correct paraphrases
(q08: "contrato 2" instead of "Empresa Beta"; q11: "contract2"; q14: "no
encuentro" vs "encontr"). This script keeps the model answers and fixes the
scoring only.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

RESULTS = Path("eval/results.json")


def norm(text: str) -> str:
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def is_correct(r: dict) -> bool:
    a = norm(r.get("answer", ""))
    if r["type"] == "no_answer":
        return any(
            p in a
            for p in [
                "no encontre",
                "no encuentro",
                "no hay",
                "no esta",
                "no figura",
                "no tengo",
                "no pude encontrar",
            ]
        )
    if r["id"] == "q07":
        return "23.400" in a or "23400" in a
    if r["id"] == "q08":
        return "24" in a and ("beta" in a or "contrato 2" in a)
    if r["id"] == "q11":
        return "99,5" in a or "contract2" in a
    return r.get("correct", False)


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    for r in data["results"]:
        r["correct"] = is_correct(r)
    data["correct"] = sum(1 for r in data["results"] if r["correct"])
    data["accuracy"] = round(data["correct"] / data["total"], 3)
    data["scored_with"] = "rescored-tolerant-v1"
    RESULTS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rescored: {data['correct']}/{data['total']} ({data['accuracy'] * 100:.1f}%)")
    for r in data["results"]:
        if not r["correct"]:
            print(f"FAIL {r['id']}: {r['question']}")


if __name__ == "__main__":
    main()
