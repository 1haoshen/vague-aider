"""Pairwise significance for binary success rate.

Inputs are per-task binary outcomes from two variants (e.g. BASE vs KNOWGUI_FULL),
aligned by task_id, ideally averaged over seeds first.

  python significance.py --a base.json --b knowgui.json
"""

import argparse
import json
import math
from pathlib import Path

try:
    from scipy import stats  # type: ignore
except Exception:  # pragma: no cover
    stats = None


def load_outcomes(path: Path) -> dict[str, int]:
    """Expect [{"task_id": ..., "success": 0|1}, ...]."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(d["task_id"]): int(bool(d["success"])) for d in data}


def mcnemar(a: dict[str, int], b: dict[str, int]) -> dict:
    """McNemar's test on paired binary outcomes — the right test for paired SR."""
    keys = sorted(set(a) & set(b))
    b01 = sum(1 for k in keys if a[k] == 0 and b[k] == 1)  # b helped
    b10 = sum(1 for k in keys if a[k] == 1 and b[k] == 0)  # b hurt
    n = b01 + b10
    if n == 0:
        return {"n_discordant": 0, "p_value": 1.0, "stat": 0.0}
    if stats is not None and n >= 25:
        chi2 = (abs(b01 - b10) - 1) ** 2 / n  # continuity-corrected
        p = 1 - stats.chi2.cdf(chi2, df=1)
        return {"n_discordant": n, "stat": chi2, "p_value": p, "test": "mcnemar_chi2"}
    # Exact binomial under H0: b01 ~ Binom(n, 0.5)
    k = min(b01, b10)
    p = 2 * sum(math.comb(n, i) * 0.5 ** n for i in range(0, k + 1))
    p = min(p, 1.0)
    return {"n_discordant": n, "stat": k, "p_value": p, "test": "mcnemar_exact"}


def bootstrap_ci(
    a: dict[str, int], b: dict[str, int], n_boot: int = 1000, seed: int = 0
) -> dict:
    """Bootstrap 95% CI on the paired SR difference (b - a)."""
    import random as _r

    rng = _r.Random(seed)
    keys = sorted(set(a) & set(b))
    diffs = [b[k] - a[k] for k in keys]
    n = len(diffs)
    boots = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        boots.append(sum(diffs[i] for i in idx) / n)
    boots.sort()
    lo, hi = boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot)]
    return {"delta": sum(diffs) / n, "ci95": [lo, hi], "n": n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, type=Path, help="baseline outcomes")
    parser.add_argument("--b", required=True, type=Path, help="variant outcomes")
    parser.add_argument("--n_boot", type=int, default=1000)
    args = parser.parse_args()

    a = load_outcomes(args.a)
    b = load_outcomes(args.b)
    print(json.dumps({
        "mcnemar": mcnemar(a, b),
        "bootstrap": bootstrap_ci(a, b, n_boot=args.n_boot),
    }, indent=2))


if __name__ == "__main__":
    main()
