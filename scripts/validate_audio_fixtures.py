#!/usr/bin/env python3
"""Evaluate recognized words against original synthetic-fixture scripts, never rewrite ASR.

This measures agreement with the intended synthetic text, not a human-annotated
recording. Numbers are normalized for equivalent spoken representations only.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]


def tokens(text):
    text = text.casefold()
    values = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
    numeric = {"8": "oito", "20": "vinte"}
    return [numeric.get(t, t) for t in values]


def word_error_rate(reference, hypothesis):
    ref, hyp = tokens(reference), tokens(hypothesis)
    d = [[0]*(len(hyp)+1) for _ in range(len(ref)+1)]
    for i in range(len(ref)+1): d[i][0] = i
    for j in range(len(hyp)+1): d[0][j] = j
    for i in range(1,len(ref)+1):
        for j in range(1,len(hyp)+1):
            d[i][j] = min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(ref[i-1]!=hyp[j-1]))
    i,j=len(ref),len(hyp)
    changes=[]
    while i or j:
        if i and j and d[i][j] == d[i-1][j-1]+(ref[i-1]!=hyp[j-1]):
            if ref[i-1]!=hyp[j-1]: changes.append({"type":"substitution","reference":ref[i-1],"recognized":hyp[j-1]})
            i-=1;j-=1
        elif i and d[i][j] == d[i-1][j]+1:
            changes.append({"type":"deletion","reference":ref[i-1]});i-=1
        else:
            changes.append({"type":"insertion","recognized":hyp[j-1]});j-=1
    changes.reverse()
    return {"reference_words":len(ref),"recognized_words":len(hyp),"errors":d[-1][-1],
            "wer":d[-1][-1]/len(ref),"changes":changes}


def overlap(word, pauses, raw=False):
    start=word.get("raw_start",word["start"]) if raw else word["start"]
    end=word.get("raw_end",word["end"]) if raw else word["end"]
    return sum(max(0.,min(end,p["end"])-max(start,p["start"])) for p in pauses)


def main():
    report={"synthetic_test_only":True,"method":"Levenshtein WER; casefold, punctuation removed, numeric 8/20 verbal equivalents; accents retained",
      "limitations":["Reference is the intended synthetic script, not independently annotated actual speech.",
        "Small and turbo use the exact same Piper WAV files for each comparison.",
        "Timing checked against exact inserted gaps and audio silencedetect boundaries, not manually annotated phoneme boundaries.",
        "These fixtures do not establish zero errors on new human recordings."],"comparisons":[]}
    for subject in ["cartas","sol"]:
        script=(ROOT/f"examples/demo_{subject}.txt").read_text(encoding="utf-8")
        for model,suffix in [("small","small_piper"),("large-v3-turbo","turbo")]:
            path=ROOT/f"examples/audio/demo_{subject}_{suffix}_transcript.json"
            transcript=json.loads(path.read_text())
            report["comparisons"].append({"subject":subject,"model":model,"source":transcript["source"],
               "source_sha256":transcript["audio_sha256"],"duration":transcript["duration"],
               "inference_seconds":transcript["transcription"]["elapsed_seconds"],
               "saved_result_reused":transcript.get("cache_hit",False),
               "real_time_factor":transcript["transcription"]["elapsed_seconds"]/transcript["duration"],
               **word_error_rate(script,transcript["text"])})
    truth=json.loads((ROOT/"examples/audio/sincronia_piper_ground_truth.json").read_text())
    transcript=json.loads((ROOT/"examples/audio/sincronia_piper_turbo_transcript.json").read_text())
    inserted=[{"start":a["end"],"end":b["start"]} for a,b in zip(truth["phrases"],truth["phrases"][1:])]
    report["synchronization"]={"source":transcript["source"],"source_sha256":transcript["audio_sha256"],
       "model":transcript["transcription"]["model"],"duration":transcript["duration"],
       "inference_seconds":transcript["transcription"]["elapsed_seconds"],
       "forced_alignment":transcript["transcription"]["forced_alignment"],
       "clipped_words":transcript["transcription"]["silence_refined_words"],
       "exact_inserted_gaps":inserted,
       "raw_word_overlap_inserted_gaps_seconds":sum(overlap(w,inserted,True) for w in transcript["words"]),
       "refined_word_overlap_inserted_gaps_seconds":sum(overlap(w,inserted) for w in transcript["words"]),
       "raw_word_overlap_acoustic_silences_seconds":sum(overlap(w,transcript["pauses"],True) for w in transcript["words"]),
       "refined_word_overlap_acoustic_silences_seconds":sum(overlap(w,transcript["pauses"]) for w in transcript["words"]),
       "words_overlapping_inserted_gap_more_than_20ms":sum(overlap(w,inserted)>.02 for w in transcript["words"]),
       **word_error_rate(" ".join(x["text"] for x in truth["phrases"]),transcript["text"])}
    output=ROOT/"docs/audio-validation.json"
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
