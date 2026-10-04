"""Reusable live Mixxx moves for mini-experiments and hand-built live mixes.

Extracted from the scripts Ernest heard and approved (2026-10-01..03): the
reprise->intro handoff, the same-song Diddy skip, the riff crossover between a
song and its own sample, exact loops on live-drummed records, and bar-by-bar
cut patterns. Everything runs live on the original files through
hands.mixxx_control; nothing is rendered. See docs/LIVE_MINI_EXPERIMENTS.md.
"""
from __future__ import annotations

import re
import time
from contextlib import closing, contextmanager
from pathlib import Path

from hands.mixxx_control import MixxxControl
from hands.run_mix_plan import (
    EQ_UNITY,
    FILTER_NEUTRAL,
    deck_group,
    eq_group,
    filter_group,
    load_deck,
    set_bpm_target,
    start_recording,
    stop_recording,
)
from hands.transition import smoothstep
from shared.gentle_faders import GENTLE_BLEND_BEATS

CUT_SECONDS = 0.06          # an in/out cut eases this long so it never clicks
# Fading a song out into a different song: ramp its channel fader down steadily
# over about this many counts (Ernest, 2026-10-03: agents "move that vertical
# knob down TOO FAST ... channel fader needs to be gentler"). Only beat juggling,
# deliberate cuts and same-song handoffs move faster.
GENTLE_FADE_BEATS = GENTLE_BLEND_BEATS     # shared.gentle_faders: one rule for every harness
# smoothstep's steepest point is 1.5x a linear ramp's speed over the same span
_PEAK_SPEED = {"linear": 1.0, "smooth": 1.5}
_CHANNEL = re.compile(r"^\[Channel\d+\]$")
NATIVE_LOOP_BEATS = (1, 2, 4, 8, 16, 32)


def _library_rows(sql: str, params: tuple, index_path: Path | None):
    from brain import library_index

    path = index_path or library_index.current_index_path()
    with closing(library_index.connect(path)) as db:
        return db.execute(sql, params).fetchall()


def library_track(artist: str, title: str, hint: str = "", *, index_path: Path | None = None) -> str:
    """Exact track_id of one available copy, so no drive name is hardcoded."""
    rows = [r[0] for r in _library_rows(
        "SELECT track_id FROM tracks WHERE artist LIKE ? AND title = ? AND available = 1 AND track_id LIKE ?",
        (f"%{artist}%", title, f"%{hint}%"), index_path)]
    if len(rows) != 1:
        raise SystemExit(f"expected one available '{artist} - {title}'"
                         f"{f' matching {hint!r}' if hint else ''}, found {len(rows)}: {rows}")
    return rows[0]


class Track:
    """A recording plus its Mixxx grid: grid beat <-> source seconds."""

    def __init__(self, artist: str, title: str, bpm: float, first_beat: float, hint: str = ""):
        self.artist, self.title, self.bpm, self.first_beat, self.hint = artist, title, bpm, first_beat, hint
        self._path: str | None = None

    def at(self, beat: float) -> float:
        return self.first_beat + beat * 60.0 / self.bpm

    def beat_at(self, seconds: float) -> float:
        return (seconds - self.first_beat) * self.bpm / 60.0

    def path(self) -> str:
        if self._path is None:
            self._path = library_track(self.artist, self.title, self.hint)
        return self._path


def track_from_library(artist: str, title: str, hint: str = "", *, index_path: Path | None = None) -> Track:
    """A Track whose grid comes from the library's beat_phase row."""
    track_id = library_track(artist, title, hint, index_path=index_path)
    rows = _library_rows("SELECT bpm, first_beat_seconds FROM beat_phase WHERE track_id = ?", (track_id,), index_path)
    if not rows:
        raise SystemExit(f"no beat grid analysed for {track_id}; run Analyze & enrich first")
    track = Track(artist, title, float(rows[0][0]), float(rows[0][1]), hint)
    track._path = track_id
    return track


class Live:
    """One Mixxx session: saved state, timing by play position, eased moves."""

    def __init__(self, mixxx: MixxxControl):
        self.m = mixxx
        self.saved: list[tuple[str, str, float]] = []
        self.decks: tuple[int, ...] = ()

    # --- session state ---------------------------------------------------
    def save_set(self, group: str, key: str, value: float) -> None:
        self.saved.append((group, key, self.m.get(group, key)))
        self.m.set(group, key, value)

    def prepare(self, decks, *, master_gain: float | None = None, crossfader: float = 0.0) -> None:
        decks = tuple(decks)
        for deck in decks:
            try:
                playing = self.m.get(deck_group(deck), "play")
            except Exception as exc:
                raise SystemExit(f"Mixxx has no {deck_group(deck)}: show enough decks first ({exc})")
            if playing > 0.5:
                raise SystemExit(f"deck {deck} is playing; stop it first")
        self.decks = decks
        if master_gain is not None:
            self.save_set("[Master]", "gain", master_gain)
        self.save_set("[Master]", "crossfader", crossfader)
        for deck in decks:
            group = deck_group(deck)
            for key, value in (("orientation", 1), ("volume", 0.0), ("pitch_adjust", 0.0)):
                self.save_set(group, key, value)
            self.save_set(filter_group(deck), "super1", FILTER_NEUTRAL)
            for band in (1, 2, 3):
                self.save_set(eq_group(deck), f"parameter{band}", EQ_UNITY)

    def restore(self) -> None:
        for deck in self.decks:
            try:
                self.stop(deck)
            except Exception:
                pass
        for group, key, value in reversed(self.saved):
            try:
                self.m.set(group, key, value)
            except Exception:
                pass
        self.saved.clear()

    @contextmanager
    def recording(self):
        started = start_recording(self.m)
        try:
            yield started
        finally:
            if started:
                stop_recording(self.m)

    # --- timing -------------------------------------------------------------
    def pos(self, deck: int) -> float:
        group = deck_group(deck)
        return self.m.get(group, "playposition") * self.m.get(group, "duration")

    def wait(self, deck: int, seconds: float, lead: float = 0.0) -> None:
        while self.pos(deck) < seconds - lead:
            if self.m.get(deck_group(deck), "play") < 0.5:
                raise RuntimeError(f"deck {deck} stopped before {seconds:.2f}s")
            time.sleep(0.01)

    def automate(self, clock: int, track: Track, b0: float, b1: float, lanes, *, curve: str = "smooth",
                 fast: bool = False) -> None:
        """Ease each (group, key, v0, v1) from clock-deck grid beat b0 to b1.

        curve="smooth" eases in and out (fastest in the middle); "linear" is a
        steady ramp, the gentler choice for a channel fader.

        A channel fader (a deck's "volume") may never move faster than a full
        sweep per GENTLE_FADE_BEATS at its steepest point; a faster move raises
        ValueError before anything is written. Pass fast=True only for beat
        juggling, a deliberate cut, or a same-song handoff."""
        if curve not in _PEAK_SPEED:
            raise ValueError(f"unknown curve {curve!r}")
        if not fast:
            check_gentle_fader(b1 - b0, lanes, curve=curve)
        shape = smoothstep if curve == "smooth" else (lambda v: v)
        t0, t1 = track.at(b0), track.at(b1)
        while True:
            x = (self.pos(clock) - t0) / (t1 - t0) if t1 > t0 else 1.0
            for group, key, v0, v1 in lanes:
                self.m.set(group, key, v0 + (v1 - v0) * shape(min(1.0, max(0.0, x))))
            if x >= 1.0:
                return
            if self.m.get(deck_group(clock), "play") < 0.5:
                raise RuntimeError(f"clock deck {clock} stopped during automation")
            time.sleep(0.02)

    def cut(self, targets, seconds: float = CUT_SECONDS) -> None:
        """Ease (group, key, target) lanes from their current values, like a fader cut."""
        lanes = [(g, k, self.m.get(g, k), v) for g, k, v in targets]
        t0 = time.monotonic()
        while seconds > 0 and (x := (time.monotonic() - t0) / seconds) < 1.0:
            for g, k, v0, v1 in lanes:
                self.m.set(g, k, v0 + (v1 - v0) * x)
            time.sleep(0.01)
        for g, k, _, v1 in lanes:
            self.m.set(g, k, v1)

    # --- deck controls ------------------------------------------------------
    def eq(self, deck: int, low: float = EQ_UNITY, mid: float = EQ_UNITY, high: float = EQ_UNITY) -> None:
        for band, value in ((1, low), (2, mid), (3, high)):
            self.m.set(eq_group(deck), f"parameter{band}", value)

    def vol(self, deck: int, value: float) -> None:
        self.m.set(deck_group(deck), "volume", value)

    def load(self, deck: int, track: Track, beat: float, *, bpm: float | None = None, pitch: float = 0.0) -> None:
        load_deck(self.m, deck, track.path(), cue_seconds=track.at(beat), expected_bpm=track.bpm)
        self.vol(deck, 0.0)
        if bpm and abs(bpm - track.bpm) > 0.05:
            set_bpm_target(self.m, deck, bpm)
        self.m.set(deck_group(deck), "pitch_adjust", pitch)
        self.m.set(filter_group(deck), "super1", FILTER_NEUTRAL)
        self.eq(deck)

    def start(self, deck: int, volume: float = 1.0) -> None:
        self.vol(deck, volume)
        self.m.set(deck_group(deck), "play", 1)
        self.m.set(deck_group(deck), "beatsync_phase", 1)

    def stop(self, deck: int) -> None:
        group = deck_group(deck)
        self.m.set(group, "play", 0)
        self.vol(deck, 0.0)
        try:
            self.m.set(group, "loop_enabled", 0)
        except Exception:
            pass


# --- techniques ---------------------------------------------------------------

def check_gentle_fader(beats: float, lanes, *, curve: str = "linear") -> None:
    """Raise ValueError when any channel-fader lane in (group, key, v0, v1)
    lanes would sweep faster than a full fader travel per GENTLE_FADE_BEATS."""
    for group, key, v0, v1 in lanes:
        if key != "volume" or not _CHANNEL.match(group) or v0 == v1:
            continue
        needed = abs(v1 - v0) * GENTLE_FADE_BEATS * _PEAK_SPEED[curve]
        if beats + 1e-9 < needed:
            raise ValueError(
                f"{group} fader {v0:g} -> {v1:g} over {beats:g} beats ({curve}) is too fast: a blend "
                f"needs at least {needed:g} beats (a full sweep per {GENTLE_FADE_BEATS} counts, linear). "
                "Use a longer, linear ramp; fast=True is only for juggling, deliberate cuts and "
                "same-song handoffs.")


def same_song_handoff(live: Live, *, out_deck: int, in_deck: int, track: Track,
                      at_beat: float, blend_beats: float = 4) -> None:
    """Hand the same recording from out_deck to in_deck (already cued at the
    matching point of the repeated music) with a short blend, bass swapped
    halfway. A zero-length blend is an on-beat cut."""
    live.eq(in_deck, low=0.0)
    live.wait(out_deck, track.at(at_beat), lead=0.05)
    live.start(in_deck, volume=0.0 if blend_beats else 1.0)
    if blend_beats:
        half = at_beat + blend_beats / 2
        live.automate(out_deck, track, at_beat, half, [(deck_group(in_deck), "volume", 0.0, 1.0)], fast=True)
        live.eq(in_deck)
        live.m.set(eq_group(out_deck), "parameter1", 0.0)
        live.automate(out_deck, track, half, at_beat + blend_beats, [(deck_group(out_deck), "volume", 1.0, 0.0)],
                      fast=True)                   # same-song handoff: identical material, short is approved
    else:
        live.eq(in_deck)
    live.stop(out_deck)
    live.eq(out_deck)


def eq_split_crossover(live: Live, *, clock_deck: int, clock_track: Track, out_deck: int, in_deck: int,
                       enter_beat: float, hold_beats: float = 0, cross_beats: float = 8) -> None:
    """For two decks carrying the same riff or drums: in_deck enters bass-only
    with the bass swapped on enter_beat, holds that for hold_beats, then the
    riff crosses over in cross_beats (out mids/highs down, in mids/highs up).
    The outgoing channel fader falls on a steady linear ramp over at least
    GENTLE_FADE_BEATS from the start of the cross, so a short riff cross never
    slams the fader. The approved Diana Ross -> Mo Money bridge is hold 8, cross 8."""
    e_out, e_in = eq_group(out_deck), eq_group(in_deck)
    live.eq(in_deck, low=EQ_UNITY, mid=0.0, high=0.0)
    live.wait(clock_deck, clock_track.at(enter_beat), lead=0.05)
    live.start(in_deck)
    live.m.set(e_out, "parameter1", 0.0)
    cross_from = enter_beat + hold_beats
    if hold_beats:
        live.wait(clock_deck, clock_track.at(cross_from))
    g_out = deck_group(out_deck)
    fader_beats = max(cross_beats, GENTLE_FADE_BEATS)
    at_cross_end = 1.0 - cross_beats / fader_beats
    live.automate(clock_deck, clock_track, cross_from, cross_from + cross_beats, [
        (e_out, "parameter2", EQ_UNITY, 0.0), (e_out, "parameter3", EQ_UNITY, 0.0),
        (e_in, "parameter2", 0.0, EQ_UNITY), (e_in, "parameter3", 0.0, EQ_UNITY),
        (g_out, "volume", 1.0, at_cross_end),
    ], curve="linear")
    if at_cross_end > 0:
        live.automate(clock_deck, clock_track, cross_from + cross_beats, cross_from + fader_beats,
                      [(g_out, "volume", at_cross_end, 0.0)], curve="linear")
    live.stop(out_deck)
    live.eq(out_deck)


def fade_out(live: Live, *, deck: int, clock_deck: int, clock_track: Track, start_beat: float,
             beats: float = GENTLE_FADE_BEATS, stop: bool = True, fast: bool = False) -> None:
    """Bring a deck's channel fader down gently: a steady (linear) ramp from its
    current level to 0 over `beats` of the clock deck, then stop the deck.
    Fewer than GENTLE_FADE_BEATS for a full fader raises unless fast=True."""
    group = deck_group(deck)
    live.automate(clock_deck, clock_track, start_beat, start_beat + beats,
                  [(group, "volume", live.m.get(group, "volume"), 0.0)], curve="linear", fast=fast)
    if stop:
        live.stop(deck)


def exact_loop(live: Live, *, deck: int, track: Track, start_beat: float, beats: float) -> bool:
    """Loop `beats` from `start_beat` on a playing (or about to play) deck.

    Whole-beat starts with 1/2/4/8/16/32 beats use Mixxx's beat loop; any other
    start or length sets exact loop points in interleaved stereo samples.
    Returns True when the native beat loop was used."""
    if beats <= 0:
        raise ValueError("loop length must be positive")
    group = deck_group(deck)
    if float(start_beat).is_integer() and beats in NATIVE_LOOP_BEATS:
        live.m.set(group, f"beatloop_{int(beats)}_activate", 1)
        return True
    rate = live.m.get(group, "track_samplerate")
    live.m.set(group, "loop_start_position", round(track.at(start_beat) * rate) * 2)
    live.m.set(group, "loop_end_position", round(track.at(start_beat + beats) * rate) * 2)
    if live.m.get(group, "loop_enabled") < 0.5:
        live.m.set(group, "reloop_toggle", 1)
    return False


def play_bar_pattern(live: Live, *, clock_deck: int, clock_track: Track, start_beat: float, pattern: str,
                     states: dict[str, list[tuple[str, str, float]]], beats_per_step: float = 4) -> None:
    """One state per character, each switch eased onto its step's downbeat."""
    unknown = sorted(set(pattern) - set(states))
    if unknown:
        raise ValueError(f"pattern uses unknown states {unknown}; known: {sorted(states)}")
    for step, char in enumerate(pattern):
        live.wait(clock_deck, clock_track.at(start_beat + step * beats_per_step), lead=CUT_SECONDS / 2)
        live.cut(states[char])
