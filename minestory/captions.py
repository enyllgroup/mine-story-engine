"""Editable PT-BR SRT and word-synchronized ASS with social-video safe zones."""
from __future__ import annotations
from pathlib import Path
import re
from typing import Any


def _time(seconds: float, ass: bool = False) -> str:
    scale = 100 if ass else 1000
    value = max(0, round(seconds * scale))
    hours, value = divmod(value, 3600 * scale)
    minutes, value = divmod(value, 60 * scale)
    secs, fraction = divmod(value, scale)
    return (f"{hours}:{minutes:02}:{secs:02}.{fraction:02}" if ass else
            f"{hours:02}:{minutes:02}:{secs:02},{fraction:03}")


def _escape(text: str) -> str:
    # Strip ASS override syntax in recognized text, preserving spoken letters.
    return text.replace("\\", "＼").replace("{", "(").replace("}", ")").replace("\n", " ")


def groups(words: list[dict[str, Any]], max_words: int = 4,
           max_chars: int = 29, max_gap: float = .65) -> list[list[dict[str, Any]]]:
    result, current = [], []
    for word in words:
        token = word["word"].strip()
        if not token or word["end"] <= word["start"]:
            continue
        if current and (len(current) >= max_words or
                        len(" ".join(w["word"] for w in current)) + 1 + len(token) > max_chars or
                        word["start"] - current[-1]["end"] > max_gap):
            result.append(current)
            current = []
        current.append(word)
        if re.search(r"[.!?;:]$", token):
            result.append(current)
            current = []
    if current:
        result.append(current)
    return result


def write_captions(transcript: dict[str, Any], output_dir: str | Path,
                   width: int = 1080, height: int = 1920, font: str = "Pixelify Sans",
                   font_path: str | Path | None = None, max_words: int = 4,
                   **kwargs: Any) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    chunks = groups(transcript["words"], max_words=max_words)
    font_size = round(width * .0593)
    # Keep the rightmost 15% clear of UI buttons; center captions slightly left.
    anchor_x, anchor_y = round(width * .465), round(height * .735)
    margin_x = round(width * .085)
    ass = ["[Script Info]", "Title: MineStory — legendas editáveis", "ScriptType: v4.00+",
           f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: MineStory,{font},{font_size},&H00FFFFFF,&H004AE2FF,&H00141512,&H85000000,-1,0,0,0,100,100,0,0,1,{max(2,round(width*.004))},{max(1,round(width*.002))},5,{margin_x},{margin_x},0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    srt, cue_metadata = [], []
    for i, chunk in enumerate(chunks):
        start, end = float(chunk[0]["start"]), float(chunk[-1]["end"])
        srt.extend([str(i + 1), f"{_time(start)} --> {_time(end)}", " ".join(w["word"] for w in chunk), ""])
        # Reduce rather than wrap into interface areas for unusually long tokens.
        size = font_size
        phrase = " ".join(w["word"] for w in chunk)
        if font_path:
            from PIL import ImageFont
            while size > round(font_size * .64) and ImageFont.truetype(str(font_path), size).getlength(phrase) > width * .77:
                size -= 1
        else:
            size = min(size, round(width * .77 / max(1, len(phrase)) / .61))
        base = rf"{{\an5\pos({anchor_x},{anchor_y})\fs{size}}}"
        for index, word in enumerate(chunk):
            word_start = float(word["start"])
            # A later word may overlap marginally in Whisper. The displayed active
            # word changes at the next start; never produce overlapping ASS events.
            next_start = float(chunk[index + 1]["start"]) if index + 1 < len(chunk) else end
            word_end = min(float(word["end"]), next_start)
            if word_end > word_start:
                row = " ".join((rf"{{\c&H004AE2FF&}}{_escape(w['word'])}{{\c&H00FFFFFF&}}" if j == index else _escape(w["word"])) for j, w in enumerate(chunk))
                ass.append(f"Dialogue: 0,{_time(word_start,True)},{_time(word_end,True)},MineStory,,0,0,0,,{base}{row}")
            if next_start > word_end:
                ass.append(f"Dialogue: 0,{_time(word_end,True)},{_time(next_start,True)},MineStory,,0,0,0,,{base}{_escape(phrase)}")
        cue_metadata.append({"start": start, "end": end, "text": phrase, "font_size": size,
                             "anchor": [anchor_x, anchor_y], "safe_width": width * .77})
    ass_path, srt_path = output / "legendas.ass", output / "legendas.srt"
    ass_path.write_text("\n".join(ass) + "\n", encoding="utf-8-sig")
    srt_path.write_text("\n".join(srt), encoding="utf-8")
    return {"ass": str(ass_path), "srt": str(srt_path), "cues": len(chunks),
            "cue_metadata": cue_metadata, "font": font,
            "safe_zone": {"x_min": .08, "x_max": .85, "y_center": .735,
                          "note": "Margens conservadoras; interfaces das plataformas podem variar."}}
