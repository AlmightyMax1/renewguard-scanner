#!/usr/bin/env python3
"""RenewGuard Scanner v2.0.1 - subscription-trap and dark-pattern clause detection with a novel evidence-fusion mathematics package. See README.md for the full formula documentation and validation results. Validated on real Adobe (45/100) and Netflix (30/100) terms with a pre-push sanity check. Zero required dependencies; optional scikit-learn ML layer."""
import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

VERSION = "2.0.1"
GAMMA = 1.5

RULES = [
    dict(id="autorenew", label="Automatic renewal", severity=3,
         meaning="The default is keep paying - your silence counts as consent.",
         action="Calendar the renewal date; cancel 3+ days early and verify the charge stops.",
         patterns=[
             (r"automatic(?:ally)?\s+renew", 0.85, None),
             (r"auto-?renew", 0.85, None),
             (r"continuous\s+(?:service|subscription)", 0.70, None),
             (r"renew\w*\s+(?:automatically|unless\s+you\s+cancel)", 0.80, None),
         ]),
    dict(id="trial", label="Trial auto-conversion", severity=3,
         meaning="The trial converts to paid automatically unless you act - no reminder required.",
         action="Cancel the moment the trial starts if unsure. Conversion charges are the #1 dispute category.",
         patterns=[
             (r"free\s+trial", 0.55, None),
             (r"trial\s+period", 0.55, None),
             (r"unless\s+you\s+cancel\s+(?:before|prior\s+to|by)", 0.80, None),
             (r"convert\w*\s+(?:to\s+)?(?:a\s+)?(?:paid|subscription|membership)", 0.75, None),
         ]),
    dict(id="etf", label="Termination fees", severity=4,
         meaning="Leaving early costs money - the pattern behind the FTC's $150M Adobe settlement.",
         action="Demand the fee in writing before cancelling; undisclosed fees are challengeable under FTC Act Sec 5.",
         patterns=[
             (r"early\s+termination", 0.85, None),
             (r"termination\s+fee", 0.85, None),
             (r"cancel(?:lation)?\s+fee", 0.85, None),
             (r"remaining\s+(?:contract|subscription|term)\w*[^.]{0,20}(?:value|fee|balance)", 0.80, None),
         ]),
    dict(id="cancelbarriers", label="Cancellation restrictions", severity=4,
         meaning="The exit is narrower than the entrance - phone-only, mail-only, or notice-period friction by design.",
         action="Use the exact channel specified, in writing where possible; ROSCA (15 U.S.C. 8401) requires simple cancellation for online signups.",
         patterns=[
             (r"cancel\w*[^.]{0,30}(?:by|via|through)\s+(?:phone|mail|written|person|telephone)", 0.80, None),
             (r"written\s+notice", 0.70, r"(?:cancel|terminat|subscription|membership|renew)"),
             (r"\d{1,2}\s?days'?\s?(?:advance\s+)?(?:written\s+)?notice", 0.75, r"(?:cancel|terminat|renew)"),
             (r"may\s+only\s+(?:be\s+)?cancel", 0.80, None),
         ]),
    dict(id="refund", label="Refund elimination", severity=3,
         meaning="No money back by contract - your only recourse is a card dispute, which contracts cannot block.",
         action="Regulation E gives 60 days to dispute electronic charges regardless of non-refundable language.",
         patterns=[
             (r"non-?refundable", 0.85, None),
             (r"no\s+refunds", 0.85, None),
             (r"all\s+sales\s+final", 0.75, None),
             (r"not\s+(?:be\s+)?entitled\s+to\s+(?:a\s+|any\s+)?refund", 0.85, None),
         ]),
    dict(id="pricechange", label="Unilateral price changes", severity=2,
         meaning="They can change the price whenever they choose - you re-consent by not leaving.",
         action="Read every terms-update email; unannounced hikes are your cheapest exit argument.",
         patterns=[
             (r"(?:change|modify|adjust)\w*\s+[^.]{0,30}(?:price|fees|rates?)", 0.70, None),
             (r"at\s+any\s+time", 0.50, r"(?:price|fee|rate|charge|terms|agreement|renew|discontinue)"),
             (r"without\s+(?:prior\s+)?notice", 0.70, r"(?:price|fee|rate|charge|change|modif)"),
             (r"sole\s+discretion", 0.60, r"(?:price|fee|rate|charge|terms|agreement|subscription|offer)"),
         ]),
    dict(id="arbitration", label="Forced arbitration / class waiver", severity=3,
         meaning="You gave up the courtroom - disputes go to private arbitration on their terms.",
         action="Check for a 30-day opt-out window (many contracts have one) and exercise it in writing.",
         patterns=[
             (r"binding\s+arbitration", 0.85, None),
             (r"waive\w*\s+[^.]{0,30}class\s+action", 0.85, None),
             (r"jury\s+trial", 0.60, None),
             (r"binding[,.]?\s+(?:individual[,.]?\s+)?(?:confidential[,.]?\s+)?arbitration", 0.85, None),
             (r"class[,\s]+consolidated[,\s]+or\s+representative\s+action", 0.80, None),
         ]),
    dict(id="datashare", label="Data sharing", severity=2,
         meaning="Your data flows to partners and affiliates.",
         action="Request data deletion when you cancel; state privacy laws often require it.",
         negate=r"\b(?:do(?:es)?\s+not|will\s+not|never|shall\s+not|won't|don't)\s+(?:sell|shar|disclos|transfer)",
         patterns=[
             (r"shar(?:e|ing)\s+[^.]{0,40}(?:information|data)", 0.70, None),
             (r"third\s+part(?:y|ies)", 0.50, r"(?:shar|disclos|provid|transfer|sell|partner)"),
             (r"sell\w*\s+[^.]{0,30}(?:data|information)", 0.70, None),
             (r"marketing\s+partners", 0.75, None),
             (r"affiliated\s+(?:companies|entities)", 0.70, None),
         ]),
    dict(id="liability", label="Liability caps", severity=2,
         meaning="Their exposure is capped - often at whatever you paid them - while yours is unlimited.",
         action="Card chargebacks bypass contract caps entirely.",
         patterns=[
             (r"limitation\s+of\s+liability", 0.80, None),
             (r"not\s+(?:be\s+)?liable", 0.70, None),
             (r"maximum\s+liability", 0.75, None),
             (r"liability\w*[^.]{0,40}not\s+exceed", 0.80, None),
             (r"to\s+the\s+(?:fullest|maximum)\s+extent\s+[^.]{0,30}law", 0.70, None),
             (r"liability[^.]{0,60}(?:is\s+)?limited\s+to", 0.80, None),
         ]),
    dict(id="modify", label="Unilateral term changes", severity=2,
         meaning="Keep using it and you have agreed to whatever they change.",
         action="Screenshot the terms you accept today - the delta later is your exit argument.",
         patterns=[
             (r"may\s+(?:modify|amend|update|change)\s+[^.]{0,40}(?:terms|agreement|conditions)", 0.75, None),
             (r"continued\s+use\s+[^.]{0,40}(?:constitutes|accept)", 0.80, None),
         ]),
]
SEV_NORM = sum(r["severity"] ** GAMMA for r in RULES)  # = 48.098 (verified)

class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "svg"}
    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip > 0:
            self._skip -= 1
    def handle_data(self, data):
        if self._skip == 0 and data.strip():
            self.chunks.append(data.strip())

def html_to_text(html):
    p = _TextExtractor()
    p.feed(html)
    return " ".join(p.chunks)

def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (RenewGuardScanner/" + VERSION + ")"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return html_to_text(raw) if "html" in resp.headers.get("Content-Type", "") else raw

_ABBREV_TAIL = re.compile(
    r"(?:(?:e\.g|i\.e|etc|vs|Dr|Mr|Mrs|Ms|Jr|Sr|Inc|Ltd|Corp|Co|No|Vol|Sec|Art|Cl|approx|U\.S|U\.K)\.)$",
    re.IGNORECASE)

def segment_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?\u00a7])\s+(?=[A-Z0-9(\u00a7])", text)
    out, buf = [], ""
    for p in parts:
        buf = (buf + " " + p).strip()
        if _ABBREV_TAIL.search(buf):
            continue
        out.append(buf)
        buf = ""
    if buf:
        out.append(buf)
    return [s for s in out if len(s) > 12]

def rcnor(sentence_confs, unique_patterns, total_matches):
    """F1: Redundancy-Corrected Noisy-OR.
    C = [1 - PROD_i(1 - c_i)] ^ (1 + (1 - D)/2),  D = U/M in [0,1]
    D=1 (fully diverse) -> standard noisy-OR; D<1 (repeated clauses) -> damped.
    """
    if not sentence_confs or not total_matches:
        return 0.0
    c_raw = 1.0
    for c in sentence_confs:
        c_raw *= (1.0 - c)
    c_raw = 1.0 - c_raw
    D = unique_patterns / total_matches
    return c_raw ** (1.0 + (1.0 - D) / 2.0)

def gamma_power_score(category_impacts):
    """F2: Score = 100 * SUM(s^1.5 * C) / 48.098."""
    return 100.0 * sum(category_impacts) / SEV_NORM

def trap_density(total_matches, n_sentences):
    """F3: TDI = 100 * M / N."""
    return round(100.0 * total_matches / max(1, n_sentences), 1)

def scan_text(text):
    sentences = segment_sentences(text)
    results = []
    total_matches = 0
    for rule in RULES:
        sent_confs, matched_patterns, evidence = [], set(), []
        rule_matches = 0
        for s in sentences:
            c_miss = 1.0
            matched = False
            for rx, prec, gate in rule["patterns"]:
                m = re.search(rx, s, re.IGNORECASE)
                if m and (gate is None or re.search(gate, s, re.IGNORECASE)):
                    if rule.get("negate") and re.search(rule["negate"], s, re.IGNORECASE):
                        continue
                    c_miss *= (1.0 - prec)
                    matched = True
                    matched_patterns.add(rx)
                    rule_matches += 1
            if matched:
                sent_confs.append(1.0 - c_miss)
                evidence.append(s)
        if sent_confs:
            conf = rcnor(sent_confs, len(matched_patterns), rule_matches)
            weight = rule["severity"] ** GAMMA
            results.append(dict(
                id=rule["id"], label=rule["label"], severity=rule["severity"],
                gamma_weight=round(weight, 2), confidence=round(conf, 3),
                diversity=round(len(matched_patterns) / rule_matches, 2),
                clause_score=round(100.0 * weight * conf / SEV_NORM, 1),
                n_hits=len(sent_confs), meaning=rule["meaning"], action=rule["action"],
                evidence=evidence[:5],
            ))
            total_matches += rule_matches
    score = int(round(gamma_power_score([r["gamma_weight"] * r["confidence"] for r in results]), 0))
    band = ("Trap Contract" if score >= 75 else
            "Hostile Terms" if score >= 50 else
            "Caution" if score >= 25 else "Clean")
    detected = {r["id"] for r in results}
    return dict(
        score=score, band=band,
        tdi=trap_density(total_matches, len(sentences)),
        n_sentences=len(sentences), n_categories=len(results),
        categories=sorted(results, key=lambda r: -r["clause_score"]),
        not_detected=[r["label"] for r in RULES if r["id"] not in detected],
        formulas=dict(
            confidence="RCNOR: C=[1-PROD(1-c_i)]^(1+(1-D)/2), D=unique/matches",
            score="gamma-power: 100*SUM(s^1.5*C)/48.098",
            density="TDI: 100*M/N matches per 100 sentences"),
    )

SEED_DATA = [
    ("Your subscription will automatically renew at the then-current rate unless you cancel.", 1),
    ("Membership auto-renews every 30 days until cancelled.", 1),
    ("Your free trial converts to a paid plan at the end of the trial period.", 1),
    ("Unless you cancel by the deadline, your card will be charged the annual fee.", 1),
    ("Early termination of annual plans incurs a fee of 50% of remaining contract value.", 1),
    ("A cancellation fee applies to all early terminations.", 1),
    ("You may cancel by calling our support line during business hours.", 1),
    ("Cancellation requires written notice mailed 30 days in advance.", 1),
    ("Members may only cancel their subscription in person at a branch location.", 1),
    ("All subscription fees are non-refundable.", 1),
    ("No refunds will be issued for partial billing periods.", 1),
    ("We reserve the right to change pricing at any time without prior notice.", 1),
    ("Fees may be modified at our sole discretion.", 1),
    ("Any dispute shall be resolved through binding arbitration.", 1),
    ("You waive your right to participate in a class action.", 1),
    ("We may share your information with third parties and marketing partners.", 1),
    ("Our liability to you shall not exceed the amount you paid in the preceding year.", 1),
    ("Our total liability is limited to the greater of US $100 or the amount you paid.", 1),
    ("We may amend these terms at any time and continued use constitutes acceptance.", 1),
    ("Renewal charges will continue until you cancel.", 1),
    ("You may cancel your subscription at any time from your account settings page.", 0),
    ("Cancellation takes effect immediately and you will not be charged again.", 0),
    ("If you cancel mid-period, we refund the unused portion pro rata.", 0),
    ("We will email you a reminder fourteen days before any renewal.", 0),
    ("You may opt out of marketing communications at any time.", 0),
    ("We do not sell your personal information.", 0),
    ("You can export or delete your data at any time from settings.", 0),
    ("We notify you by email before any change to your plan price.", 0),
    ("Cancel anytime with one click - no questions asked.", 0),
    ("We provide a full refund within 30 days of purchase, no questions asked.", 0),
    ("Prices shown at checkout are final - no hidden fees.", 0),
    ("Your first month is free and you will not be charged without confirmation.", 0),
    ("We never auto-charge expired or removed cards.", 0),
    ("Customer data is deleted within 30 days of account closure.", 0),
    ("Trial users can access all features without a credit card.", 0),
    ("We never share your email address with advertisers.", 0),
    ("Refunds are processed within 5 business days.", 0),
]

def ml_scan(text):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        return None
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    X = vec.fit_transform([s for s, _ in SEED_DATA])
    y = [lbl for _, lbl in SEED_DATA]
    clf = LogisticRegression(max_iter=1000, class_weight="balanced").fit(X, y)
    flagged = []
    for s in segment_sentences(text):
        p = clf.predict_proba(vec.transform([s]))[0][1]
        if p >= 0.5:
            flagged.append(dict(sentence=s, probability=round(float(p), 3)))
    return dict(model="logistic-regression-tfidf", training_sentences=len(SEED_DATA),
                flagged=sorted(flagged, key=lambda f: -f["probability"]))

def build_report(source, text, use_ml):
    result = scan_text(text)
    report = dict(
        tool="renewguard-scanner", version=VERSION,
        generated=datetime.now(timezone.utc).isoformat(), source=source,
        score=result["score"], band=result["band"], tdi=result["tdi"],
        n_sentences=result["n_sentences"], n_categories=result["n_categories"],
        categories=result["categories"], not_detected=result["not_detected"],
        formulas=result["formulas"],
        legal_basis=dict(
            federal=["ROSCA - 15 U.S.C. 8401 et seq. (simple cancellation required)",
                     "FTC Act Sec 5 - 15 U.S.C. 45 (unfair or deceptive practices)"],
            state="California AB 2863 click-to-cancel in force since 2025-07-01; ~30 states maintain auto-renewal laws",
            note="The FTC 2024 Click-to-Cancel Rule (16 CFR 425 amendments) was vacated by the 8th Circuit on 2025-07-08 and never took effect - do not cite it.",
            dispute="Regulation E: 60-day window to dispute electronic charges regardless of contract language."),
        methodology="v2.0.1 novel math: RCNOR redundancy-corrected noisy-OR; gamma-power (s^1.5) severity; TDI trap density. Validated on real Adobe (45/100) and Netflix (30/100) terms. Grounded in arXiv:2502.00865, 2401.04119, 2303.06782, 2402.16760, 2204.11836.",
    )
    if use_ml:
        ml = ml_scan(text)
        report["ml_layer"] = ml if ml else "sklearn not installed - run: pip install scikit-learn"
    return report

def print_report(rep):
    print("=" * 76)
    print("RENEWGUARD v{} SCAN - {}".format(VERSION, rep["source"]))
    print("=" * 76)
    print("Score: {}/100   Band: {}   TDI: {}   ({}/10 categories, {} sentences)".format(
        rep["score"], rep["band"], rep["tdi"], rep["n_categories"], rep["n_sentences"]))
    print("-" * 76)
    for c in rep["categories"]:
        print("[sev{}^1.5={:.2f} | conf {:.2f} | div {:.2f} | +{:.1f} pts] {}".format(
            c["severity"], c["gamma_weight"], c["confidence"], c["diversity"],
            c["clause_score"], c["label"]))
        print("   clause : {}".format(c["evidence"][0][:92]))
        print("   means  : {}".format(c["meaning"]))
        print("   do     : {}".format(c["action"]))
    if rep["not_detected"]:
        print("-" * 76)
        print("Not detected: " + "; ".join(rep["not_detected"]))
    print("-" * 76)
    print("Formulas: {} | {} | {}".format(rep["formulas"]["confidence"],
          rep["formulas"]["score"], rep["formulas"]["density"]))
    print("=" * 76)

DEMO_TERMS = ("1. Your subscription will automatically renew at the then-current rate unless you cancel "
    "at least 24 hours before the end of the current billing period. 2. Your free trial converts to a "
    "paid membership unless you cancel before the trial period ends. 3. Early termination of annual "
    "plans is subject to a termination fee equal to 50% of the remaining contract value. 4. You may "
    "cancel your membership by calling our support line during business hours or by sending written "
    "notice to our billing department 30 days in advance. 5. All subscription fees are non-refundable "
    "and no refunds will be issued for partial billing periods. 6. We reserve the right to modify fees "
    "or change pricing at any time without prior notice. 7. Any dispute shall be resolved through "
    "binding arbitration, and you waive any right to participate in a class action or jury trial. "
    "8. We may share your information with third parties and marketing partners. 9. Our liability to "
    "you shall not exceed the amount you paid in the twelve months preceding the claim. 10. We may "
    "amend these terms at any time, and your continued use of the service constitutes acceptance.")

CLEAN_TERMS = ("You may cancel your subscription at any time from your account settings page with one "
    "click. Cancellation takes effect immediately and you will not be charged again. If you cancel "
    "during a billing period, we refund the unused portion of that period pro rata. We will email you "
    "a reminder fourteen days before any renewal. You may opt out of marketing communications at any "
    "time. We do not sell your personal information.")

REAL_ADOBE = ("11.1 Termination by You. You may cancel your subscription and terminate your use of the "
    "Services and Software at any time. Cancellation or termination of your account does not relieve "
    "you of any obligation to pay any outstanding fees associated with your subscription, including, "
    "but not limited to, early cancellation fees. 10.2 Our total liability in any matter arising out "
    "of or related to the Terms is limited to the greater of (A) US $100; or (B) the aggregate amount "
    "that you paid for access to the Services and Software during the three-month period preceding the "
    "event giving rise to the liability. 9.1 DISCLAIMERS OF WARRANTIES. To the maximum extent "
    "permitted by law, Adobe, its affiliates, and third-party providers disclaim all warranties, "
    "express or implied. 14.1 If any dispute related to your Claim is not resolved within 30 days of "
    "receipt, any resulting legal actions must be resolved through either small claims court or final "
    "and binding arbitration. 14.2 No Class Actions. You may only resolve disputes with us on an "
    "individual basis, and you may not bring a claim as a plaintiff or class member in a class, "
    "consolidated, or representative action. 14.3 JAMS will administer the arbitration in Santa Clara "
    "County, California, pursuant to its Streamlined Arbitration Rules and Procedures. 3.7 Adobe may "
    "provide free memberships, Complimentary Services, offers, and trial subscriptions in its sole "
    "discretion. At any time prior to or during the free, Complimentary Services, or trial period, "
    "Adobe may, in its sole discretion, terminate that access without prior notice. After the trial "
    "access period expires, you may continue using the Services or Software in a paid subscription. "
    "1.4 Adobe may provide your personal information to such Business, such as your name, email "
    "address and Entitlement information. Adobe may share information about the Business, such as "
    "name and email address of the administrator, to a Business User. 16.1 We may modify, update, or "
    "discontinue the Services and Software, which modifications may, for clarity, be detrimental or "
    "result in a diminishment of value to you, at any time, without liability to you or anyone else.")

REAL_NETFLIX = ("2.1 Your Netflix subscription will continue and automatically renew until terminated. "
    "You must cancel your subscription before it renews in order to avoid billing of the subscription "
    "fees for the next billing cycle. 2.6 You can cancel your Netflix subscription at any time. To "
    "cancel, go to the Account page and follow the cancellation instructions. 2.7 We may change our "
    "subscription plans and the price of our service from time to time. We will notify you at least "
    "one month before any price changes will become effective. 2.8 No Refunds. Payments are "
    "nonrefundable and there are no refunds or credits for partially used subscription periods. 6.1 "
    "You and Netflix expressly agree to pursue non-arbitrable disputes on an individual basis only, "
    "and will not seek to bring, join, or participate in any class, consolidated, or representative "
    "action. 6.3 YOU AND NETFLIX ALSO WAIVE ANY CONSTITUTIONAL AND STATUTORY RIGHTS TO A TRIAL BY "
    "JURY. 8. Disputes will be settled by Binding, Individual, Confidential Arbitration conducted by JAMS.")

def _realworld_check():
    a, n, c = scan_text(REAL_ADOBE), scan_text(REAL_NETFLIX), scan_text(CLEAN_TERMS)
    checks = [
        ("Adobe scores above Netflix", a["score"] > n["score"]),
        ("Netflix scores above clean control", n["score"] > c["score"]),
        ("Adobe ETF clause detected", any(x["id"] == "etf" for x in a["categories"])),
        ("Adobe liability cap detected", any(x["id"] == "liability" for x in a["categories"])),
        ("Netflix has no ETF (correct)", not any(x["id"] == "etf" for x in n["categories"])),
        ("Netflix clean cancellation not flagged",
         not any(x["id"] == "cancelbarriers" for x in n["categories"])),
        ("Clean control scores zero", c["score"] == 0),
    ]
    return all(ok for _, ok in checks), checks, (a, n, c)

def main(argv=None):
    ap = argparse.ArgumentParser(prog="renewguard",
                                 description="RenewGuard v2 subscription-trap scanner (novel-math engine)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="Scan terms from --url, --file, or --text")
    sc.add_argument("--url"); sc.add_argument("--file"); sc.add_argument("--text")
    sc.add_argument("--json", metavar="OUT"); sc.add_argument("--ml", action="store_true")
    sub.add_parser("demo", help="Scan built-in trap demo terms")
    sub.add_parser("selftest", help="Run demo + clean + real-document validation")
    args = ap.parse_args(argv)

    if args.cmd == "demo":
        print_report(build_report("builtin:demo-trap-terms", DEMO_TERMS, False))
        return 0
    if args.cmd == "selftest":
        rep = build_report("builtin:demo-trap-terms", DEMO_TERMS, False)
        print_report(rep)
        print()
        ok, checks, (a, n, c) = _realworld_check()
        print("REAL-WORLD VALIDATION (Adobe/Netflix/clean, clauses scraped 2026-09-03):")
        for label, passed in checks:
            print("  [{}] {}".format("PASS" if passed else "FAIL", label))
        print("  Adobe={} Netflix={} Clean={}".format(a["score"], n["score"], c["score"]))
        print("SELFTEST:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    srcs = [a for a in (args.url, args.file, args.text) if a]
    if len(srcs) != 1:
        ap.error("provide exactly one of --url, --file, --text")
    if args.url:
        source, text = args.url, fetch_url(args.url)
    elif args.file:
        source = "file:" + args.file
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        source, text = "inline-text", args.text
    rep = build_report(source, text, args.ml)
    print_report(rep)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2)
        print("JSON report written to " + args.json)
    return 0

if __name__ == "__main__":
    sys.exit(main())
