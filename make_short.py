"""
Serialized mystery Shorts: one story split into daily parts.
Hindi narration, English subtitles, every part ends with a cliffhanger question.

Setup:
    pip install anthropic edge-tts moviepy pillow numpy
    (FFmpeg must be installed)
    export ANTHROPIC_API_KEY="your-key"

Run (creates a new series the first time, then continues it):
    python make_short.py                      # default story seed
    python make_short.py "a haunted haveli"   # your own seed (only used when a new series starts)

Files:
    series.json            story so far (premise, characters, arc, summaries of past parts)
    output/short.mp4       today's video (1080x1920)
    output/meta.json       title, description, tags, audience question
    output/series_next.json  updated story. Copy over series.json ONLY after the upload succeeds:
                             cp output/series_next.json series.json
"""
import asyncio
import json
import math
import os
import re
import sys

import anthropic
import edge_tts
import numpy as np
from moviepy import AudioFileClip, VideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
VOICE = "hi-IN-MadhurNeural"      # female alternative: hi-IN-SwaraNeural
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
OUT = "output"
SERIES_FILE = "series.json"
ARC_LENGTH = 12
DEFAULT_SEED = "a mystery in a small Indian town"

PALETTES = [
    ((8, 10, 25), (40, 20, 70)),
    ((5, 20, 30), (15, 70, 90)),
    ((25, 8, 15), (110, 25, 50)),
    ((10, 10, 10), (60, 60, 80)),
]

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def load_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------- Claude helpers ----------
def ask_json(prompt, max_tokens=3000):
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
    )
    match = re.search(r"\{.*\}", msg.content[0].text, re.DOTALL)
    if not match:
        raise ValueError(f"Failed to parse JSON from LLM response: {msg.content[0].text}")
    return json.loads(match.group(0))


def new_series(seed):
    print(f"Creating new series with seed: '{seed}'...")
    data = ask_json(f"""Create an original fictional mystery series told in short daily parts
(YouTube Shorts, narrated in Hindi). Seed idea: {seed}

Rules:
- Fully original fiction. No real people, real crimes or real brands.
- Exactly {ARC_LENGTH} parts. Each beat must end on a hook or twist.
- Plant clues early so the final reveal feels earned and satisfying.

Return ONLY JSON:
{{
  "title_en": "short series title",
  "premise": "3-4 sentences",
  "characters": ["Name - one line description"],
  "arc": ["one-line beat for part 1", "... up to part {ARC_LENGTH}"]
}}""")
    data["parts"] = []
    return data


def load_series(seed):
    if os.path.exists(SERIES_FILE):
        with open(SERIES_FILE, encoding="utf-8") as f:
            series = json.load(f)
        if len(series.get("parts", [])) < len(series.get("arc", [])):
            return series
        print("Series finished, starting a new one.")
    return new_series(seed)


def write_part(series):
    n = len(series["parts"]) + 1
    total = len(series["arc"])
    previous = "\n".join(f"Part {p['part']}: {p['summary']}" for p in series["parts"][-6:]) or "None yet."
    ending = (
        "This is the FINAL part: resolve the mystery satisfyingly, then ask viewers what kind of story they want next."
        if n == total
        else "End on a cliffhanger."
    )
    print(f"Writing Part {n} of {total}...")
    return ask_json(f"""You are writing Part {n} of {total} of a Hindi mystery Short.

Series: {series['title_en']}
Premise: {series['premise']}
Characters: {'; '.join(series['characters'])}
Story so far:
{previous}
This part's beat: {series['arc'][n - 1]}

Requirements:
- 7-8 scenes, about 35-45 seconds when spoken. Simple, spoken Hindi in Devanagari.
- {"Open with a one-line recap of last part, then a hook." if n > 1 else "Open with a strong hook."}
- {ending}
- The LAST scene is a question to the audience about the story, specific, not generic
  (for example "Do you think X is lying? Comment your guess!"), in Hindi.
- subtitle_en is a natural English translation of narration_hi.

Return ONLY JSON:
{{
  "hook_title_en": "intriguing title under 50 chars",
  "summary_en": "2 sentences on what happened in this part (for story memory)",
  "description_en": "2 sentences teaser, no spoilers",
  "tags": ["5-8 tags"],
  "question_en": "the audience question in English",
  "scenes": [
    {{"narration_hi": "...", "subtitle_en": "...", "headline_en": "2-4 words"}}
  ]
}}""")


# ---------- Voiceover ----------
async def tts(text, path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)


# ---------- Frames ----------
def wrap(draw, text, font, max_w):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def gradient(top, bottom):
    t = np.linspace(0, 1, H)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - t) + np.array(bottom)[None, None, :] * t
    return np.repeat(arr, W, axis=1).astype(np.uint8)


def draw_centered(draw, lines, font, y, fill, stroke=0, gap=12):
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text(((W - w) / 2, y), line, font=font, fill=fill,
                  stroke_width=stroke, stroke_fill=(0, 0, 0))
        y += font.size + gap
    return y


def make_scene(subtitle, headline, dur, idx, part_no, is_last):
    bg = gradient(*PALETTES[idx % len(PALETTES)])
    head_font, cap_font = load_font(110), load_font(78)
    badge_font, q_font = load_font(64), load_font(620)
    words = subtitle.split()
    chunks = [" ".join(words[i:i + 4]) for i in range(0, len(words), 4)]
    if not chunks:
        chunks = ["..."]
    scratch = ImageDraw.Draw(Image.new("RGB", (W, H)))
    head_lines = wrap(scratch, headline.upper(), head_font, W - 140)

    def make_frame(t):
        img = Image.fromarray(bg)
        d = ImageDraw.Draw(img, "RGBA")

        # fog rings (placeholder visual, replace with the mascot later)
        pulse = 1 + 0.06 * math.sin(t * 3)
        for r, a in ((400, 30), (290, 55), (180, 90)):
            rr = r * pulse
            d.ellipse((W / 2 - rr, 900 - rr, W / 2 + rr, 900 + rr), fill=(255, 255, 255, a))

        # big question mark on the final (question) scene
        if is_last:
            qw = d.textlength("?", font=q_font)
            d.text(((W - qw) / 2, 560), "?", font=q_font, fill=(255, 230, 60, 230),
                   stroke_width=8, stroke_fill=(0, 0, 0))

        # PART badge
        label = f"PART {part_no}"
        bw = d.textlength(label, font=badge_font)
        d.rounded_rectangle(((W - bw) / 2 - 36, 90, (W + bw) / 2 + 36, 190), radius=24,
                            fill=(220, 40, 60, 230))
        d.text(((W - bw) / 2, 100), label, font=badge_font, fill=(255, 255, 255))

        # headline slides in
        k = min(t / 0.4, 1)
        ease = 1 - (1 - k) ** 3
        draw_centered(d, head_lines, head_font, 260 - 100 * (1 - ease),
                      (255, 255, 255, int(255 * ease)), stroke=6)

        # English subtitles
        i = min(int(t / dur * len(chunks)), len(chunks) - 1)
        cap_lines = wrap(d, chunks[i], cap_font, W - 140)
        draw_centered(d, cap_lines, cap_font, 1380, (255, 230, 60), stroke=8)
        return np.array(img.convert("RGB"))

    return VideoClip(make_frame, duration=dur)


# ---------- Main ----------
def main(seed):
    os.makedirs(OUT, exist_ok=True)
    series = load_series(seed)
    part = write_part(series)
    n = len(series["parts"]) + 1
    print(f"\n{series['title_en']} - Part {n}: {part['hook_title_en']}")

    clips = []
    scenes = part["scenes"]
    for i, s in enumerate(scenes):
        path = f"{OUT}/scene_{i}.mp3"
        print(f"Generating TTS for scene {i + 1}/{len(scenes)}...")
        asyncio.run(tts(s["narration_hi"], path))
        audio = AudioFileClip(path)
        clip = make_scene(s["subtitle_en"], s["headline_en"], audio.duration, i, n, i == len(scenes) - 1)
        clips.append(clip.with_audio(audio))

    print("\nConcatenating clips and rendering video...")
    final = concatenate_videoclips(clips)
    final.write_videofile(f"{OUT}/short.mp4", fps=FPS, codec="libx264",
                          audio_codec="aac", preset="veryfast")

    meta = {
        "title": f"{part['hook_title_en']} | {series['title_en']} Part {n} #Shorts"[:100],
        "description": (
            f"{part['description_en']}\n\n{part['question_en']}\nComment your guess! "
            f"New part every day.\n\nThis is a work of fiction.\n\n#Shorts #Mystery #Hindi"
        ),
        "tags": part["tags"] + ["Shorts", "Mystery", "Hindi story"],
        "question": part["question_en"],
    }
    with open(f"{OUT}/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    series["parts"].append({"part": n, "summary": part["summary_en"]})
    with open(f"{OUT}/series_next.json", "w", encoding="utf-8") as f:
        json.dump(series, f, indent=2, ensure_ascii=False)
    print("\nDone: output/short.mp4 and output/meta.json created successfully.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SEED)
