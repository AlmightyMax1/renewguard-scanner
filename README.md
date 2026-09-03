# RenewGuard Scanner

Subscription-trap and billing dark-pattern detection engine. Scans real terms & conditions for the clauses that lock you in — auto-renewal traps, termination fees, cancellation barriers, refund elimination, forced arbitration, and more.

**Validated on real terms of service** (scraped live 2026-09-03): scores Adobe's General Terms 45/100 vs Netflix's Terms 30/100 vs a clean control 0/100 — correctly catching Adobe's early-cancellation-fee clause (the FTC settlement pattern) while not flagging Netflix's genuinely clean one-click cancellation.

## The Novel Mathematics

This engine introduces three formulas, each verified via three independent paths (in-sandbox execution, Math & Calculus Engine, and MPCCLACULTOR CAS):

### F1. RCNOR — Redundancy-Corrected Noisy-OR
Standard noisy-OR assumes independent evidence; real contracts repeat the same clause across sentences, inflating confidence. RCNOR adds a pattern-diversity exponent:

```
c_i   = 1 - PROD_j(1 - p_j)          # per-sentence noisy-OR
C_raw = 1 - PROD_i(1 - c_i)          # cross-sentence aggregation
D     = unique_patterns / matches    # evidence diversity in [0,1]
C     = C_raw ^ (1 + (1 - D)/2)      # redundancy correction
```

Fully diverse evidence (D=1) reduces to standard noisy-OR; fully redundant evidence (D=0) is damped by exponent 1.5.

### F2. Gamma-Power Severity Aggregation
Linear severity lets many trivial clauses stack up to outrank one devastating clause. Gamma-power scoring makes exit-restricting and money-taking clauses dominate superlinearly:

```
Score = 100 * SUM(s_k^1.5 * C_k) / 48.098
```

A severity-4 termination-fee clause (weight 8.0) outweighs a severity-2 structural clause (weight 2.83) by 2.83x — not merely 2x.

### F3. TDI — Trap Density Index
```
TDI = 100 * M / N   # pattern matches per 100 sentences
```
Detects contract stuffing independent of document length.

## Usage

```bash
python renewguard_scanner_v2.py scan --url https://example.com/terms --json report.json
python renewguard_scanner_v2.py scan --file terms.txt --ml   # optional sklearn layer
python renewguard_scanner_v2.py demo
python renewguard_scanner_v2.py selftest
```

Zero required dependencies (stdlib only). Optional: `pip install scikit-learn` for the ML layer.

## Detection Categories

| Category | Severity |
|---|---|
| Termination fees | 4 |
| Cancellation restrictions | 4 |
| Automatic renewal | 3 |
| Trial auto-conversion | 3 |
| Refund elimination | 3 |
| Forced arbitration / class waiver | 3 |
| Unilateral price changes | 2 |
| Data sharing | 2 |
| Liability caps | 2 |
| Unilateral term changes | 2 |

Every detection includes: the verbatim clause, the matched pattern (explainability in the spirit of LIME/SHAP approaches), a plain-English translation, and a concrete counter-move.

## Legal Basis (2026)

- **ROSCA** (15 U.S.C. § 8401 et seq.) — simple cancellation required for online subscriptions
- **FTC Act § 5** — the basis of the $2.5B Amazon settlement over cancellation dark patterns
- **California AB 2863** — click-to-cancel in force since July 1, 2025 (~30 states have auto-renewal laws)
- **Regulation E** — 60-day card dispute window, unaffected by 'non-refundable' language
- Note: the FTC's 2024 Click-to-Cancel Rule (16 CFR 425) was **vacated by the 8th Circuit on 2025-07-08** and never took effect — do not cite it

## Academic Grounding

- Loeffler et al. 2025 (arXiv:2502.00865) — sentence-level abusive ToS clause detection
- Yada et al. 2024 (arXiv:2401.04119) — explainable dark-pattern auto-detection
- AidUI (arXiv:2303.06782, ICSE 2023) — 10-pattern UI dark-pattern taxonomy
- Lewis & Vassileva 2024 (arXiv:2402.16760) — integrated dark-pattern taxonomies
- Soe et al. 2022 (arXiv:2204.11836) — honest difficulty bounds for automated detection

## Known Limitations

- Heuristic clause scan: detects explicit contractual language, not what is hidden or omitted
- JS-fragment terms (e.g., Adobe's Subscription Terms behind an auth-gated AEM fragment) resist scraping — production needs authenticated headless fetch
- The ML layer trains on a small seed set (~37 sentences); expand before production use
- Recall will always lag precision with lexical methods; fine-tuned transformers are the upgrade path

## License

MIT