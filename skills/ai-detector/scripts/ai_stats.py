"""Stylometric signals for AI-text detection (Turkish + English, stdlib only).

Usage: python ai_stats.py <file.txt|-> [--lang tr|en|auto]
Prints JSON: whole-text metrics, pattern hits with examples, and per-paragraph metrics.
These are weak signals. They describe style; they do not prove authorship.
"""

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter

# Phrases that are over-represented in LLM output. Rates are reported per 1000 words.
PATTERNS = {
    "tr": {
        "kalip_acilis": [
            r"günümüzde", r"son yıllarda", r"hızla gelişen", r"giderek artan",
            r"büyük önem taşı", r"kritik (?:bir )?(?:öneme|rol)", r"önemli bir rol oyna",
            r"vazgeçilmez bir", r"ayrılmaz bir parçası",
        ],
        "kalip_baglac": [
            r"bunun yanı sıra", r"ayrıca", r"öte yandan", r"buna ek olarak",
            r"bu bağlamda", r"bu doğrultuda", r"bu noktada", r"sonuç olarak",
            r"özetle", r"kısacası", r"genel olarak", r"dolayısıyla",
        ],
        "abarti_sifat": [
            r"kapsamlı", r"etkili", r"verimli", r"yenilikçi", r"dinamik",
            r"çok yönlü", r"benzersiz", r"güçlü", r"sağlam", r"sorunsuz",
            r"değerli", r"derinlemesine",
        ],
        "kacamak": [
            r"önemli(?:dir)? olduğunu belirtmek", r"unutulmamalıdır ki",
            r"göz önünde bulundurul", r"dikkate alın", r"belirtmek gerekir",
            r"altını çizmek gerek",
        ],
        "asistan_artigi": [
            r"bir yapay zek[aâ] (?:modeli|dil modeli|asistanı) olarak", r"umarım\b.{0,40}?yardımcı ol",
            r"başka bir sorunuz", r"elbette[!,]", r"tabii ki[!,]", r"işte .{0,40}:\s*$",
            r"\[(?:buraya|isim|tarih|kaynak)[^\]]*\]",
        ],
    },
    "en": {
        "kalip_acilis": [
            r"in today'?s (?:fast-paced|digital|ever-changing)", r"in the (?:modern|digital) (?:era|age|world)",
            r"ever-evolving", r"rapidly evolving", r"plays? a (?:crucial|pivotal|vital|key) role",
            r"is (?:crucial|essential|paramount)", r"cornerstone", r"testament to",
        ],
        "kalip_baglac": [
            r"\bmoreover\b", r"\bfurthermore\b", r"\badditionally\b", r"in addition",
            r"\bin conclusion\b", r"\boverall\b", r"\bultimately\b", r"\bnotably\b",
            r"it is worth noting", r"\bthus\b", r"\bhence\b",
        ],
        "abarti_sifat": [
            r"\bdelve\b", r"\bdelves\b", r"\btapestry\b", r"\bseamless(?:ly)?\b", r"\brobust\b",
            r"\bcomprehensive\b", r"\binnovative\b", r"\bleverag(?:e|ing)\b", r"\bfoster(?:s|ing)?\b",
            r"\bintricate\b", r"\bnuanced\b", r"\bpivotal\b", r"\bunderscore(?:s)?\b",
            r"\bvibrant\b", r"\bmeticulous(?:ly)?\b", r"\bharness(?:ing)?\b", r"\blandscape\b",
            r"\brealm\b", r"\bboast(?:s)?\b",
        ],
        "kacamak": [
            r"it'?s important to (?:note|remember)", r"it is important to (?:note|remember)",
            r"keep in mind", r"it should be noted", r"not only .{1,60} but also",
        ],
        "asistan_artigi": [
            r"as an ai (?:language )?model", r"i hope (?:this|that|it)\b.{0,30}?helps?", r"let me know if",
            r"^certainly[!,]", r"^sure[!,]", r"here(?:'s| is) (?:a|an|the) .{0,40}:\s*$",
            r"\[(?:insert|your name|date|citation)[^\]]*\]", r"as of my (?:last|knowledge) (?:update|cutoff)",
        ],
    },
}

TR_CHARS = set("ğüşıöçĞÜŞİÖÇ")
TR_WORDS = {"ve", "bir", "bu", "için", "ile", "da", "de", "olarak", "çok", "daha", "gibi", "olan"}
EN_WORDS = {"the", "and", "of", "to", "is", "in", "that", "for", "with", "as", "this", "are"}


def lower(text, lang):
    if lang == "tr":
        text = text.replace("I", "ı").replace("İ", "i")
    return text.lower()


def detect_lang(text):
    words = re.findall(r"\w+", text.lower())
    tr = sum(w in TR_WORDS for w in words) + 3 * sum(c in TR_CHARS for c in text)
    en = sum(w in EN_WORDS for w in words)
    return "tr" if tr > en else "en"


def sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+|\n+", text)
    return [p.strip() for p in parts if len(re.findall(r"\w+", p)) >= 2]


def words_of(text, lang):
    return re.findall(r"\w+(?:['’]\w+)?", lower(text, lang))


def mattr(words, window=50):
    """Moving-average type-token ratio; stable across text lengths."""
    if len(words) < window:
        return round(len(set(words)) / len(words), 3) if words else None
    ratios = [len(set(words[i:i + window])) / window for i in range(len(words) - window + 1)]
    return round(sum(ratios) / len(ratios), 3)


def sentence_stats(sents, lang):
    lengths = [len(words_of(s, lang)) for s in sents]
    if len(lengths) < 2:
        return {"sentences": len(lengths), "mean_len": lengths[0] if lengths else None,
                "std_len": None, "burstiness_cv": None}
    mean = statistics.mean(lengths)
    std = statistics.pstdev(lengths)
    return {"sentences": len(lengths), "mean_len": round(mean, 1), "std_len": round(std, 1),
            # Coefficient of variation: humans usually mix short and long sentences (higher CV).
            "burstiness_cv": round(std / mean, 3) if mean else None}


def pattern_hits(text, lang):
    low = lower(text, lang)
    hits = {}
    for category, regexes in PATTERNS[lang].items():
        found = []
        for rx in regexes:
            for m in re.finditer(rx, low, re.IGNORECASE | re.MULTILINE):
                start = max(0, m.start() - 40)
                found.append({"match": m.group(0), "context": text[start:m.end() + 40].replace("\n", " ")})
        hits[category] = found
    return hits


def structure(text, lang):
    lines = [l for l in text.splitlines() if l.strip()]
    bullets = sum(bool(re.match(r"\s*(?:[-*•]|\d+[.)])\s", l)) for l in lines)
    headings = sum(bool(re.match(r"\s*#{1,6}\s|\s*\*\*[^*]+\*\*\s*$", l)) for l in lines)
    conj = r"\w+, \w+(?: \w+)?,? ve \w+" if lang == "tr" else r"\w+, \w+(?: \w+)?,? and \w+"
    return {
        "lines": len(lines),
        "bullet_ratio": round(bullets / len(lines), 2) if lines else 0,
        "headings": headings,
        "bold_spans": len(re.findall(r"\*\*[^*]+\*\*", text)),
        "em_dashes": text.count("—"),
        "colons": text.count(":"),
        "triads": len(re.findall(conj, lower(text, lang))),
    }


def repetition(words):
    trigrams = Counter(zip(words, words[1:], words[2:]))
    repeated = [(" ".join(k), v) for k, v in trigrams.most_common(8) if v > 1]
    return {"repeated_trigrams": repeated}


def sentence_openers(sents, lang):
    firsts = Counter(words_of(s, lang)[0] for s in sents if words_of(s, lang))
    top = firsts.most_common(3)
    share = round(top[0][1] / len(sents), 2) if top and sents else 0
    return {"top_openers": top, "top_opener_share": share}


def analyze(text, lang):
    words = words_of(text, lang)
    sents = sentences(text)
    hits = pattern_hits(text, lang)
    n = max(len(words), 1)
    rates = {k: round(1000 * len(v) / n, 1) for k, v in hits.items()}
    return {
        "words": len(words),
        **sentence_stats(sents, lang),
        "mattr": mattr(words),
        "pattern_rate_per_1000w": rates,
        **structure(text, lang),
        **repetition(words),
        **sentence_openers(sents, lang),
        "_hits": hits,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--lang", default="auto", choices=["auto", "tr", "en"])
    args = ap.parse_args()
    text = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()
    lang = detect_lang(text) if args.lang == "auto" else args.lang

    whole = analyze(text, lang)
    examples = {k: v[:6] for k, v in whole.pop("_hits").items() if v}
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if len(re.findall(r"\w+", p)) >= 25]
    per_para = []
    for i, p in enumerate(paragraphs, 1):
        a = analyze(p, lang)
        per_para.append({
            "index": i, "start": p.strip()[:60], "words": a["words"],
            "burstiness_cv": a["burstiness_cv"], "mattr": a["mattr"],
            "pattern_hits": sum(len(v) for v in a["_hits"].values()),
        })
    print(json.dumps({"lang": lang, "whole": whole, "examples": examples, "paragraphs": per_para},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
