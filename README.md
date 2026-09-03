# RenewGuard Scanner

Subscription-trap and billing dark-pattern detection engine. Scans real terms & conditions for the clauses that lock you in — auto-renewal traps, termination fees, cancellation barriers, refund elimination, forced arbitration, and more.

**Validated on real terms of service** (scraped live 2026-09-03): full-document and excerpt testing across three real companies plus a clean control —

| Document | Score | Band |
|---|---|---|
| Microsoft Services Agreement (full document, 14,268 words) | ~65/100 | Hostile Terms |
| Adobe General Terms of Use | 45/100 | Caution |
| Netflix Terms of Use | 30/100 | Caution |
| Clean control | 0/100 | Clean |

The scanner correctly catches Adobe's early-cancellation-fee clause (the FTC settlement pattern), Microsoft's forced trial auto-renewal, non-refundable policy, $10 liability cap, and cancellation-charges reservation — while not flagging Netflix's or Microsoft's genuinely clean "cancel at any time" cancellation flows.

## The Novel Mathematics

Three formulas, each verified via three independent paths (in-sandbox execution, Math & Calculus Engine, and MPCCLACULTOR CAS):

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
| Termination fees (incl. cancellation charges) | 4 |
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

All five citations verified against arXiv metadata on 2026-09-03 — titles, authors, and claims match.

## Known Limitations (fully characterized)

- **Heuristic clause scan**: detects explicit contractual language, not what is hidden or omitted
- **Adobe Subscription Terms specifically**: after 8 scraping attempts across FireCrawl, WebScraping.AI, and Bright Data/crawl4ai (including a live headless browser session), the root cause is now fully understood — the terms live in **lazy-loaded accordion panels** (`<button aria-expanded="false">`) whose content does not exist in the DOM until each of ~40 triggers is clicked. Extraction requires a local Playwright/Selenium script that clicks all triggers, waits for panel loads, and dumps the DOM. Not a bot-detection or auth failure — the content genuinely is not in the fetched HTML.
- **Recall lags precision**: paraphrase sensitivity is the recurring gap (e.g., "cancellation charges" was missed until real Microsoft testing caught it in v2.0.2; "Binding, Individual, Confidential Arbitration" was missed until real Netflix testing caught it in v2.0.1)
- The ML layer trains on a small seed set (~37 sentences); expand before production use
- English-only patterns, US-law-focused legal notes
- Absolute scores are corpus-sensitive (Adobe scored 34-57 across runs depending on excerpt coverage); the ORDERING is stable across all tests

## Changelog

- **2.0.2** — Added `cancel(?:lation)?\s+(?:fee|charge)` ETF pattern (recall gap found in real Microsoft §9.g testing: "you may be obligated to pay cancellation charges"); added Microsoft Services Agreement full-document validation corpus and results; documented accordion root cause. Pattern verified with zero new false positives.
- **2.0.1** — Added paraphrased-arbitration patterns (real Netflix testing), "liability... limited to" pattern (real Adobe §10.2 testing), gated "written notice" (fixed false positive on Adobe's consumer-friendly arbitration opt-out); pre-push sanity check caught and fixed a corpus-trimming bug that tied Adobe to Netflix.
- **2.0.0** — Novel-math engine: RCNOR confidence fusion, gamma-power severity, TDI density.
- **1.0.0** — Initial release: 10-category rule engine, noisy-OR confidence, CLI, ML layer stub.

## License

MIT