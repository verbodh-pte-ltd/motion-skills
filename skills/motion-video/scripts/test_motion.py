#!/usr/bin/env python3
"""Checks for the score maths in motion.py. Run: python3 test_motion.py"""
from motion import RATE, freq, synth

assert abs(freq("A4") - 440.0) < 1e-9
assert abs(freq("A3") - 220.0) < 1e-9
assert abs(freq("C4") - 261.6256) < 1e-3
assert abs(freq("F#4") - freq("Gb4")) < 1e-9

# One note in the second scene: silence before it, sound at it, peak at the master level.
starts, ends = {"A": 0.0, "B": 2.0}, {"A": 2.0, "B": 4.0}
score = {"master": 0.5, "events": [{"type": "note", "scene": "B", "at": 0.5, "pitch": "A4", "len": 0.5}]}
pcm = synth(score, starts, ends, 4.0)
assert len(pcm) == 4 * RATE
assert max(abs(s) for s in pcm[: int(2.5 * RATE)]) == 0, "sound before the note"
assert max(abs(s) for s in pcm[int(2.6 * RATE): int(2.9 * RATE)]) > 0, "no sound at the note"
assert abs(max(abs(s) for s in pcm) - 0.5 * 32767) < 2, "master level not applied"

# 'len': 'scene' lasts to the end of the scene; every hit sound renders and is deterministic.
pad = {"events": [{"type": "pad", "scene": "A", "at": 0, "pitches": ["C3"], "len": "scene"}]}
pcm = synth(pad, starts, ends, 4.0)
assert max(abs(s) for s in pcm[int(1.5 * RATE): int(1.6 * RATE)]) > 0
assert max(abs(s) for s in pcm[int(2.1 * RATE):]) == 0
hits = {"events": [{"type": "hit", "scene": "A", "at": i * 0.8, "sound": s}
                   for i, s in enumerate(["thud", "pop", "tick", "whoosh"])]}
assert synth(hits, starts, ends, 4.0) == synth(hits, starts, ends, 4.0)
print("motion.py checks passed")
