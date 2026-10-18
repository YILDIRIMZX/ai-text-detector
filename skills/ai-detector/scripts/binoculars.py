"""Binoculars-style zero-shot score with two small local models (no API, nothing leaves the machine).

Method: Hans et al. 2024, "Spotting LLMs With Binoculars". score = log-perplexity of the text under
the performer model / cross-perplexity between observer and performer. Lower = more machine-like.
Small Qwen2.5 models are used because they share a tokenizer and handle Turkish and English.
Thresholds for this model pair are NOT calibrated, so the script also scores reference texts
(an AI-written anchor and, if available, known-human samples) and reports the document relative to them.

Usage:
  python binoculars.py <doc.txt> [--ai-ref ai.txt ...] [--human-ref human.txt ...] [--save-calibration]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

OBSERVER = os.environ.get("AIDET_OBSERVER", "Qwen/Qwen2.5-0.5B")
PERFORMER = os.environ.get("AIDET_PERFORMER", "Qwen/Qwen2.5-0.5B-Instruct")
MAX_TOKENS = 512
CALIBRATION = Path(__file__).resolve().parent.parent / "calibration.json"


def load():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    tok = AutoTokenizer.from_pretrained(OBSERVER)
    obs = AutoModelForCausalLM.from_pretrained(OBSERVER, dtype=dtype).to(device).eval()
    perf = AutoModelForCausalLM.from_pretrained(PERFORMER, dtype=dtype).to(device).eval()
    return tok, obs, perf, device


@torch.no_grad()
def score_chunk(ids, obs, perf):
    obs_logits = obs(ids).logits[:, :-1].float()
    perf_logits = perf(ids).logits[:, :-1].float()
    target = ids[:, 1:]
    log_ppl = F.cross_entropy(perf_logits.transpose(1, 2), target).item()
    obs_probs = F.softmax(obs_logits, dim=-1)
    x_ppl = -(obs_probs * F.log_softmax(perf_logits, dim=-1)).sum(-1).mean().item()
    return log_ppl, x_ppl, target.shape[1]


def score_text(text, tok, obs, perf, device):
    """Token-weighted Binoculars score over 512-token chunks. None if the text is too short."""
    ids = tok(text, return_tensors="pt").input_ids.to(device)
    if ids.shape[1] < 16:
        return None
    total_ppl = total_x = total_n = 0.0
    for start in range(0, ids.shape[1], MAX_TOKENS):
        chunk = ids[:, start:start + MAX_TOKENS]
        if chunk.shape[1] < 16:
            break
        lp, xp, n = score_chunk(chunk, obs, perf)
        total_ppl += lp * n
        total_x += xp * n
        total_n += n
    log_ppl, x_ppl = total_ppl / total_n, total_x / total_n
    return {"binoculars": round(log_ppl / x_ppl, 4), "log_ppl": round(log_ppl, 3),
            "tokens": int(total_n)}


def read(path):
    return Path(path).read_text(encoding="utf-8")


def mean_score(paths, *models):
    scores = [s["binoculars"] for p in paths if (s := score_text(read(p), *models))]
    return round(sum(scores) / len(scores), 4) if scores else None


def relative_position(doc, ai_ref, human_ref):
    """0 = like the AI anchor, 1 = like the human anchor (clipped). Needs both anchors."""
    if doc is None or ai_ref is None or human_ref is None or human_ref <= ai_ref:
        return None
    return round(min(1.0, max(0.0, (doc - ai_ref) / (human_ref - ai_ref))), 3)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--ai-ref", nargs="*", default=[])
    ap.add_argument("--human-ref", nargs="*", default=[])
    ap.add_argument("--save-calibration", action="store_true",
                    help="store the mean of --human-ref scores as this user's human baseline")
    args = ap.parse_args()

    models = load()
    text = read(args.doc)
    doc = score_text(text, *models)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if len(p.split()) >= 40]
    per_para = []
    for i, p in enumerate(paragraphs, 1):
        s = score_text(p, *models)
        if s:
            per_para.append({"index": i, "start": p.strip()[:60], **s})

    ai_ref = mean_score(args.ai_ref, *models)
    human_ref = mean_score(args.human_ref, *models)
    calibrated = json.loads(CALIBRATION.read_text()) if CALIBRATION.exists() else {}
    if args.save_calibration and human_ref is not None:
        calibrated = {"human_baseline": human_ref, "samples": len(args.human_ref),
                      "observer": OBSERVER, "performer": PERFORMER}
        CALIBRATION.write_text(json.dumps(calibrated, indent=1))
    if human_ref is None and calibrated.get("observer") == OBSERVER:
        human_ref = calibrated.get("human_baseline")

    doc_score = doc["binoculars"] if doc else None
    print(json.dumps({
        "models": [OBSERVER, PERFORMER], "device": models[3],
        "document": doc, "paragraphs": per_para,
        "ai_anchor": ai_ref, "human_anchor": human_ref,
        "position_0ai_1human": relative_position(doc_score, ai_ref, human_ref),
        "paragraph_positions": [
            {"index": p["index"], "position_0ai_1human": relative_position(p["binoculars"], ai_ref, human_ref)}
            for p in per_para],
        "note": "Lower Binoculars = more machine-like. Uncalibrated for this model pair; "
                "compare only against the anchors scored in the same run.",
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
