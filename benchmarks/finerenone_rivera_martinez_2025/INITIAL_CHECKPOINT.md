# Finerenone RapidMeta benchmark — initial execution checkpoint

Date: 7 November 2026  
Status: **Kit example smoke build PASS; published meta-analysis reproduction NOT YET RUN**.

## Verified actions

1. Confirmed the open-access Rivera-Martinez et al. article (DOI 10.1007/s10557-024-07666-x), its three study families, the September 2024 search cutoff and published rounded effect estimates.
2. Read `mahmood726-cyber/rapidmeta-kit` README, source generator and `configs/example_finerenone_ckd.json`.
3. Cloned `rapidmeta-kit` main and ran `python clone.py configs/example_finerenone_ckd.json --out output/finerenone_baseline_smoke.html` successfully. The generator reported three trials, a 1,190,296-byte interactive HTML output, and a copied offline asset folder. `python -m compileall -q clone.py` also passed.
4. `python -m pytest -q` could not run because the active Python environment lacks `pytest` (`No module named pytest`). This is a missing test dependency, **not** a passed or failed test suite.
5. Existing example config describes a *composite cardiovascular endpoint*, and has not been independently verified for the target paper's outcome-specific trial inputs. Therefore the successful smoke build **does not establish a match** to any published paper estimate.

## Next gates

- Independently extract per-trial data for CV death, heart failure hospitalization, all-cause mortality, renal outcomes and harms with verifiable primary source locations.
- Make distinct, source-checked configurations for each compatible HR or RR outcome, preserving original study eligibility, estimand and effect measure.
- Run the Kit and an independent statistical oracle, record two-decimal benchmark agreement, heterogeneity, all assumptions and mismatch investigations.
- Conduct the beyond-cutoff evidence update in a separate analysis. Do not merge or imply clinical or scientific validation merely from a working build.

Canonical protocol: `benchmarks/finerenone_rivera_martinez_2025/PROTOCOL.md` on `benchmark/finerenone-open-meta-2026`.

