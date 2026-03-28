
import os, re, json, math, statistics
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SUB_A = BASE / "submissions" / "A"
SUB_B = BASE / "submissions" / "B"
SRC = BASE / "sources" / "internet_like"

def tokenize(text):
    return re.findall(r"[a-z0-9_]+", text.lower())

def jaccard(a, b):
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def longest_common_span_words(a, b):
    wa, wb = tokenize(a), tokenize(b)
    # simple DP on token sequences
    dp = [0]*(len(wb)+1)
    best = 0
    for i in range(1, len(wa)+1):
        new = [0]*(len(wb)+1)
        for j in range(1, len(wb)+1):
            if wa[i-1] == wb[j-1]:
                new[j] = dp[j-1] + 1
                if new[j] > best:
                    best = new[j]
        dp = new
    return best

def external_plagiarism(text):
    flags = []
    for src_file in SRC.glob("*.txt"):
        src = src_file.read_text(encoding="utf-8")
        jac = jaccard(text, src)
        lcs = longest_common_span_words(text, src)
        if jac > 0.33 or lcs >= 18:
            flags.append({
                "source": src_file.name,
                "jaccard": round(jac, 3),
                "longest_common_span_words": lcs,
                "severity": "high" if lcs >= 25 or jac > 0.45 else "medium",
            })
    return flags

def intra_plagiarism(all_texts):
    names = list(all_texts)
    pairs = []
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            jac = jaccard(all_texts[a], all_texts[b])
            lcs = longest_common_span_words(all_texts[a], all_texts[b])
            if jac > 0.35 or lcs >= 18:
                pairs.append({
                    "a": a, "b": b,
                    "jaccard": round(jac, 3),
                    "longest_common_span_words": lcs,
                    "severity": "high" if lcs >= 25 or jac > 0.45 else "medium",
                })
    return pairs

def score_A(text, all_A):
    lower = text.lower()
    ext = external_plagiarism(text)
    intra = [p for p in intra_plagiarism(all_A) if any(x in p["a"]+p["b"] for x in [Path("dummy").name])]  # unused placeholder

    correctness = 0
    # OMP core ideas
    omp_terms = ["correlation", "residual", "atom", "support", "least-squares", "dictionary"]
    correctness += min(sum(t in lower for t in omp_terms), 5) / 5 * 50
    # reasoning
    reasoning_markers = ["because", "therefore", "using", "then", "until", "repeats", "update"]
    reasoning = min(sum(m in lower for m in reasoning_markers), 5) / 5 * 20
    # bonus
    bonus = 0
    if "q2" in lower or "bonus" in lower:
        if "stomp" in lower or "stagewise omp" in lower:
            bonus = 20
        elif "swomp" in lower or "stagewise weak orthogonal" in lower:
            bonus = 8
        elif any(k in lower for k in ["accelerate", "faster", "multiple atoms", "threshold"]):
            bonus = 3
    # coherence
    coherence = 10
    if "not fully sure" in lower or "not clear" in lower:
        coherence -= 5
    if len(text.split()) < 80:
        coherence -= 2
    coherence = max(coherence, 3)
    raw = correctness + reasoning + bonus + coherence

    # plagiarism penalties
    decision = "AUTO GRADE"
    explanation = []
    if ext:
        explanation.append("external plagiarism detected")
        raw *= 0.75
        decision = "HUMAN REVIEW"
    return {
        "raw_score": round(raw, 1),
        "decision": decision,
        "external_flags": ext,
        "explanation": explanation,
    }

def score_B(text):
    lower = text.lower()
    conceptual = 0
    # score content nuance
    concepts = ["centralized", "power", "dissent", "institution", "party", "pluralism", "authoritarian", "dictatorship"]
    conceptual = min(sum(c in lower for c in concepts), 5) / 5 * 40
    # reasoning
    markers = ["because", "therefore", "however", "that said", "when", "if", "rather than", "not inevitable"]
    reasoning = min(sum(m in lower for m in markers), 5) / 5 * 30
    # coherence
    coherence = 20
    if len(text.split()) < 45:
        coherence -= 5
    if "proves the original point" in lower and "because history shows it" in lower:
        coherence -= 8
    if "all " in lower and "automatically" in lower:
        coherence -= 4
    coherence = max(coherence, 5)
    # depth
    depth = 10
    wc = len(text.split())
    if wc < 50:
        depth = 4
    elif wc < 90:
        depth = 6
    elif wc < 140:
        depth = 8

    raw = conceptual + reasoning + coherence + depth
    explanation = []
    decision = "AUTO GRADE"
    # We do not penalize generic LLM use unless plagiarism/unsupported; heuristic style signal only notes.
    if "vanguard" in lower and "institutional checks" in lower and "delegitimized" in lower:
        explanation.append("polished generic style; no penalty applied")
    return {
        "raw_score": round(raw, 1),
        "decision": decision,
        "external_flags": [],
        "explanation": explanation,
    }

def main():
    all_A = {p.name: p.read_text(encoding="utf-8") for p in SUB_A.glob("*.txt")}
    all_B = {p.name: p.read_text(encoding="utf-8") for p in SUB_B.glob("*.txt")}
    intra_A = intra_plagiarism(all_A)
    intra_B = intra_plagiarism(all_B)
    results = {"A": {}, "B": {}, "summary": {}}

    for name, text in all_A.items():
        r = score_A(text, all_A)
        intra_flags = [p for p in intra_A if name in (p["a"], p["b"])]
        if intra_flags:
            r["decision"] = "HUMAN REVIEW"
            r["explanation"].append("intra-cohort plagiarism similarity detected")
            # stronger penalty if also external
            r["raw_score"] = round(r["raw_score"] * (0.8 if r["external_flags"] else 0.9), 1)
        results["A"][name[:-4]] = r

    for name, text in all_B.items():
        r = score_B(text)
        intra_flags = [p for p in intra_B if name in (p["a"], p["b"])]
        if intra_flags:
            r["decision"] = "HUMAN REVIEW"
            r["explanation"].append("intra-cohort plagiarism similarity detected")
            r["raw_score"] = round(r["raw_score"] * 0.9, 1)
        results["B"][name[:-4]] = r

    # attach pairwise flags summary
    results["summary"]["intra_A_pairs"] = intra_A
    results["summary"]["intra_B_pairs"] = intra_B

    out_json = BASE / "results.json"
    out_md = BASE / "results.md"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    lines = ["# Grading Results", ""]
    for group in ["A", "B"]:
        lines += [f"## Group {group}", "", "| Case | Score | Decision | Notes |", "|---|---:|---|---|"]
        for case, r in sorted(results[group].items()):
            notes = "; ".join(r["explanation"]) if r["explanation"] else "-"
            lines.append(f"| {case} | {r['raw_score']} | {r['decision']} | {notes} |")
        lines.append("")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")

if __name__ == "__main__":
    main()
