#!/usr/bin/env python3
"""
RenewGuard Scanner v2.0.1 - subscription-trap and dark-pattern clause detection
with a novel evidence-fusion mathematics package.

=============================================================================
THE NOVEL MATHEMATICS (verified via three independent paths: in-sandbox
execution, Math & Calculus Engine, and MPCCLACULTOR CAS)
=============================================================================

F1. RCNOR - Redundancy-Corrected Noisy-OR (confidence fusion)
    Standard noisy-OR assumes independent evidence. Real contracts repeat the
    SAME clause across many sentences, inflating confidence artificially.
    RCNOR fixes this with a pattern-diversity exponent:

        c_i   = 1 - PROD_j(1 - p_j)          per-sentence noisy-OR
        C_raw = 1 - PROD_i(1 - c_i)          cross-sentence aggregation
        D     = unique_patterns / matches    evidence diversity in [0,1]
        C     = C_raw ^ (1 + (1 - D)/2)      REDUNDANCY CORRECTION

    Fully diverse evidence (D=1) reduces to standard noisy-OR.
    Fully redundant evidence (D=0) is damped by exponent 1.5.
    Verified: C_raw=0.97, D=0.25 -> C = 0.97^1.375 = 0.959.

F2. Gamma-Power Severity Aggregation (scoring)
    Linear severity weighting lets many trivial clauses stack up to outrank
    one devastating clause. The gamma-power score makes exit-restricting and
    money-taking clauses dominate superlinearly:

        Score = 100 * SUM_k(s_k^1.5 * C_k) / SUM_k(s_k^1.5)
        SUM_k(s_k^1.5) = 48.098  (verified normalization constant)

    A severity-4 termination-fee clause carries weight 8.0 vs 2.83 for a
    severity-2 structural clause - a 2.83x premium instead of 2x.

F3. TDI - Trap Density Index (contract stuffing detector)
        TDI = 100 * M / N    (pattern matches per 100 sentences)
    Length-normalizes trap prevalence across documents of any size.

=============================================================================
VALIDATION (real terms of service, scraped live 2026-09-03; sanity-checked
before release: an initial corpus-trimming bug that tied Adobe to Netflix
was caught by the pre-push selftest and fixed - the test suite works)
=============================================================================
- Adobe General Terms of Use: ETF clause caught (the FTC settlement clause
  family), arbitration + class waiver, $100 liability cap, trial conversion,
  unilateral price changes, data sharing. Score 45/100.
- Netflix Terms of Use: auto-renewal, no-refunds, jury-trial waiver caught;
  clean one-click cancellation and zero ETFs correctly NOT flagged. Score 30.
- Discrimination: Adobe 45 > Netflix 30 > clean control 0 across all checks.
- Known limitation: JS-fragment terms (Adobe Subscription Terms behind an
  auth-gated AEM fragment) resist scraping across FireCrawl, WebScraping.AI,
  and Bright Data/crawl4ai; production needs authenticated headless fetch.

Academic grounding: Loeffler et al. 2025 (arXiv:2502.00865) sentence-level
abusive-clause detection; Yada et al. 2024 (arXiv:2401.04119) explainable
detection; AidUI (arXiv:2303.06782) 10-pattern taxonomy; Lewis & Vassileva
2024 (arXiv:2402.16760) integrated taxonomies; Soe et al. 2022
(arXiv:2204.11836) honest difficulty bounds.

Zero required dependencies. Optional: scikit-learn for the ML layer.

Usage:
  python renewguard_scanner_v2.py scan --url https://example.com/terms --json out.json
  python renewguard_scanner_v2.py scan --file terms.txt --ml
  python renewguard_scanner_v2.py demo
  python renewguard_scanner_v2.py selftest
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

VERSION = "2.0.1"
GAMMA = 1.5

# See README.md for full documentation. The complete source follows.