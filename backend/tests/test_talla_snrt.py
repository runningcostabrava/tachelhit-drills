# -*- coding: utf-8 -*-
"""Stage 03 of the SNRT factory (tools/snrt/fabrica/03_talla.py, #601): audio cuts must never be reused from an older reading.

When stage 02 is re-run (new tifinag clock, new Arabic reader) the ids `<slug>_<k>` are reused with other t_ini/t_fi. Stage 03 used to keep
any wav that already existed, so old cuts stayed under the same ids and no longer matched their subtitle (486 of 700 at the first chapter).
Now it keeps a cut only if `talls/intervals.json` says it was cut from this very interval and the wav duration agrees. Needs ffmpeg/ffprobe.
"""
import json
import os
import shutil
import subprocess
import sys
import wave

import pytest

FABRICA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "snrt", "fabrica")

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe not installed")


def make_chapter(folder, seconds=12):
    os.makedirs(folder, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s=320x180:d={seconds}:r=5",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-shortest", "-c:v", "libx264", "-c:a", "aac",
                    os.path.join(folder, "video.mp4")], check=True)


def write_rows(folder, intervals):
    with open(os.path.join(folder, "subtitols.jsonl"), "w", encoding="utf-8") as f:
        for k, (a, b) in enumerate(intervals):
            f.write(json.dumps({"id": f"cap_{k:04d}", "slug": "cap", "k": k, "t_ini": a, "t_fi": b, "durada": b - a, "credits": False},
                               ensure_ascii=False) + "\n")


def run_03(folder):
    r = subprocess.run([sys.executable, os.path.join(FABRICA, "03_talla.py"), folder], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def dur(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def test_reused_ids_with_new_intervals_are_recut(tmp_path):
    folder = str(tmp_path / "cap")
    make_chapter(folder)
    # first reading: three replicas; second reading (02 re-run): same ids, other intervals (the cuts must follow)
    write_rows(folder, [(1, 3), (4, 5), (6, 9)])
    run_03(folder)
    for k, (a, b) in enumerate([(1, 3), (4, 5), (6, 9)]):
        assert abs(dur(os.path.join(folder, "talls", f"cap_{k:04d}.wav")) - (b - a + 0.5)) < 0.06
    write_rows(folder, [(2, 6), (7, 8), (8.5, 9.5)])
    run_03(folder)
    for k, (a, b) in enumerate([(2, 6), (7, 8), (8.5, 9.5)]):
        assert abs(dur(os.path.join(folder, "talls", f"cap_{k:04d}.wav")) - (b - a + 0.5)) < 0.06, k
    reg = json.load(open(os.path.join(folder, "talls", "intervals.json"), encoding="utf-8"))
    assert reg["cap_0000"] == [1.75, 6.25]


def test_wav_without_registry_is_not_trusted(tmp_path):
    folder = str(tmp_path / "cap")
    make_chapter(folder)
    write_rows(folder, [(1, 3)])
    os.makedirs(os.path.join(folder, "talls"))
    # an old cut with the right duration by chance, but no interval registry: it must be recut and registered
    old = os.path.join(folder, "talls", "cap_0000.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=2.5", "-ac", "1", "-ar", "16000", old], check=True)
    before = os.path.getmtime(old)
    os.utime(old, (before - 1000, before - 1000))
    run_03(folder)
    assert os.path.getmtime(old) > before - 1000
    assert os.path.exists(os.path.join(folder, "talls", "intervals.json"))


def test_unchanged_cuts_are_kept(tmp_path):
    folder = str(tmp_path / "cap")
    make_chapter(folder)
    write_rows(folder, [(1, 3), (5, 7)])
    run_03(folder)
    p = os.path.join(folder, "talls", "cap_0001.wav")
    t = os.path.getmtime(p)
    os.utime(p, (t - 1000, t - 1000))
    run_03(folder)
    assert abs(os.path.getmtime(p) - (t - 1000)) < 1      # same interval: not recut (stage stays resumable by id)
