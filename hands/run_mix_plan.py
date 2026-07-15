"""Execute a continuous mix plan against Mixxx's control API.

Plays Mixxx like an instrument: loads tracks, rides EQ/filter/rate, beat-syncs,
crossfades, optional scratch-ins — all from brain/data/mix_plan.json.

Requires Mixxx launched with the patched control API:
    mixxx --developer --control-api-port 9995

Usage:
    uv run python -m hands.run_mix_plan --dry-run
    uv run python -m hands.run_mix_plan
    uv run python -m hands.run_mix_plan --plan brain/data/mix_plan.json --port 9995
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from hands.mixxx_control import DEFAULT_PORT, MixxxControl
from hands.transition import crossfader_target, deck_group, smoothstep, wait_for_beats, wait_for_next_beat

PLAN_DEFAULT = Path(__file__).resolve().parent.parent / "brain" / "data" / "mix_plan.json"
LOAD_TIMEOUT_S = 30.0

EQ_GROUP = "[EqualizerRack1_{channel}_Effect1]"
FILTER_GROUP = "[QuickEffectRack1_{channel}]"

# Rust gesture executor (core-rust) — sub-beat timing loops for slip fills
# and platter moves. Plans may name these gestures; when the binary is
# missing every caller degrades to the plain Python path, so plans stay
# portable across machines.
_CLAWDJ_CANDIDATES = (
    Path(__file__).resolve().parent.parent / "core-rust" / "target" / "release" / "clawdj",
    Path(__file__).resolve().parent.parent / "core-rust" / "target" / "debug" / "clawdj",
)
_clawdj_missing_noted = False


def clawdj_binary() -> Path | None:
    for candidate in _CLAWDJ_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def rust_gesture(*args: str, port: int) -> bool:
    """Run one `clawdj gesture …`; True on success, False to fall back."""
    global _clawdj_missing_noted
    import subprocess

    binary = clawdj_binary()
    if binary is None:
        if not _clawdj_missing_noted:
            print("  (clawdj binary not built — Rust gestures degrade to plain blends;"
                  " build: cd core-rust && cargo build --release -p clawdj-cli)")
            _clawdj_missing_noted = True
        return False
    # clap parses parent-level flags (--port) only before the subcommand.
    result = subprocess.run(
        [str(binary), "gesture", "--port", str(port), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  (gesture {args[0]} failed: {(result.stderr or result.stdout).strip()[:200]})")
        return False
    return True


def _wait_for(mixxx: MixxxControl, group: str, key: str, predicate, timeout_s: float) -> float:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        value = mixxx.get(group, key)
        if predicate(value):
            return value
        time.sleep(0.1)
    raise TimeoutError(f"{group},{key} not ready within {timeout_s:.1f}s")


def eq_group(deck: int) -> str:
    return EQ_GROUP.format(channel=f"[Channel{deck}]")


def filter_group(deck: int) -> str:
    return FILTER_GROUP.format(channel=f"[Channel{deck}]")


def reset_instrument(mixxx: MixxxControl) -> None:
    mixxx.set("[Master]", "crossfader", -1.0)
    mixxx.set("[Master]", "gain", 1.0)
    mixxx.set("[Master]", "volume", 1.0)
    for deck in (1, 2):
        group = deck_group(deck)
        mixxx.set(group, "volume", 1.0)
        mixxx.set(group, "pregain", 1.0)
        mixxx.set(group, "rate", 0.0)
        mixxx.set(group, "pitch_adjust", 0.0)
        mixxx.set(group, "keylock", 1)
        mixxx.set(group, "quantize", 1)
        mixxx.set(group, "mute", 0)
        try:
            eg = eq_group(deck)
            mixxx.set(eg, "parameter1", 0.5)
            mixxx.set(eg, "parameter2", 0.5)
            mixxx.set(eg, "parameter3", 0.5)
        except Exception:
            pass
        try:
            mixxx.set(filter_group(deck), "super1", 0.5)
        except Exception:
            pass


def settle_rate(mixxx: MixxxControl, deck: int, steps: int = 8) -> None:
    """Glide the deck back to its native tempo after a beatsync landing.

    Without this, sync chains the first track's tempo through the whole set
    (observed live: every transition anchored at 101 BPM). Riding the pitch
    back to 0 lets each track keep its own energy, and makes the planner's
    tempo-direction choices audible. Keylock is on, so pitch is unaffected.
    """
    group = deck_group(deck)
    try:
        current = mixxx.get(group, "rate")
    except Exception:
        return
    if abs(current) < 0.01:
        mixxx.set(group, "rate", 0.0)
        return
    bpm = mixxx.get(group, "bpm") or 100.0
    period = 60.0 / max(60.0, min(200.0, bpm))
    for i in range(1, steps + 1):
        mixxx.set(group, "rate", current * (1.0 - i / steps))
        time.sleep(period)
    print(f"  rate settled to native tempo on deck {deck}")


def set_bpm_target(mixxx: MixxxControl, deck: int, target_bpm: float) -> None:
    """Set a deliberate bridge tempo and verify the perceived BPM.

    ``rate`` is orientation-dependent in Mixxx skins/configurations, so try
    both slider directions and retain the one whose BPM readback is closest.
    The widened range is local to this deck and keylock remains enabled.
    """
    if target_bpm <= 0:
        raise ValueError(f"invalid BPM target {target_bpm}")
    group = deck_group(deck)
    cue_position = mixxx.get(group, "playposition")
    mixxx.set(group, "rate", 0.0)
    native_bpm = _wait_for(mixxx, group, "bpm", lambda value: value > 0, 2.0)
    delta = target_bpm / native_bpm - 1.0
    if abs(delta) < 0.002:
        return
    rate_range = max(0.08, min(1.0, abs(delta) * 1.25))
    mixxx.set(group, "rateRange", rate_range)
    magnitude = min(1.0, abs(delta) / rate_range)
    candidates: list[tuple[float, float]] = []
    for slider in (magnitude, -magnitude):
        mixxx.set(group, "rate", slider)
        time.sleep(0.1)
        candidates.append((abs(mixxx.get(group, "bpm") - target_bpm), slider))
    _, best_slider = min(candidates)
    mixxx.set(group, "rate", best_slider)
    actual_bpm = _wait_for(
        mixxx,
        group,
        "bpm",
        lambda value: abs(value - target_bpm) <= max(0.5, target_bpm * 0.01),
        2.0,
    )
    # Changing the rate range can make a newly loaded, stopped deck report a
    # transient position near zero. Reassert and verify the planned cue after
    # the tempo control has settled so tempo shaping cannot undo cue shaping.
    mixxx.set(group, "playposition", cue_position)
    _wait_for(
        mixxx,
        group,
        "playposition",
        lambda value: abs(value - cue_position) <= 0.002,
        2.0,
    )
    print(
        f"  deck {deck} bridge tempo: {native_bpm:.2f} -> "
        f"{actual_bpm:.2f} BPM (target {target_bpm:.2f})"
    )


def cue_deck(
    mixxx: MixxxControl,
    deck: int,
    *,
    cue_fraction: float = 0.1,
    cue_seconds: float | None = None,
    duration: float | None = None,
    settle_s: float = 1.5,
) -> tuple[float, str]:
    """Seek a stopped deck and verify Mixxx accepted the requested cue.

    Setting `playposition` once is not enough. Mixxx's `[Controls] CueRecall`
    preference (here: 3 = IntroStart) makes every freshly loaded deck
    auto-seek to its own detected intro-start marker — and that seek fires
    on a DELAY after `track_loaded` flips true, racing our manual seek
    rather than preceding it. Discovered 2026-07-14 live: a deck manually
    seeked to 19.65s (skipping Regulate's spoken intro per a dj_notes
    directive, verified exact against the synced lyrics) would hold for
    tens of milliseconds, then silently jump to ~0.24s (the track's
    auto-detected intro-start) on its own — sometimes before `play`, so
    the wrong content was already cued and playing before a transition
    even reached it. Writing Mixxx's `cue_point`/`cue_set` controls
    directly does NOT help: `cue_point` is a read-only mirror of the
    track's real persisted cue object, refreshed from
    `loadCuesFromTrack()`, not a target you can just set (verified: it
    silently reverts too). The only mechanism that reliably wins the race
    is polling: keep re-asserting `playposition` until it holds steady
    through the deferred auto-seek's actual firing window, then it's safe.
    """
    group = deck_group(deck)
    duration = duration or _wait_for(
        mixxx, group, "duration", lambda value: value > 0, LOAD_TIMEOUT_S
    )
    position = cue_seconds / duration if cue_seconds is not None else cue_fraction
    position = min(0.95, max(0.0, position))
    tolerance = max(0.002, 1.0 / duration)

    mixxx.set(group, "playposition", position)
    _wait_for(mixxx, group, "playposition", lambda value: abs(value - position) <= tolerance, 3.0)

    # Outlast Mixxx's deferred seek-on-load: keep reasserting until the
    # position holds steady for a continuous window, not just once.
    deadline = time.monotonic() + settle_s
    stable_since: float | None = None
    while time.monotonic() < deadline:
        actual = mixxx.get(group, "playposition")
        if abs(actual - position) > tolerance:
            mixxx.set(group, "playposition", position)
            stable_since = None
        elif stable_since is None:
            stable_since = time.monotonic()
        elif time.monotonic() - stable_since >= 0.5:
            break
        time.sleep(0.05)
    actual_position = mixxx.get(group, "playposition")
    actual_seconds = actual_position * duration
    cue_label = (
        f"{cue_seconds:.2f}s verified at {actual_seconds:.2f}s"
        if cue_seconds is not None
        else f"{position:.1%} verified at {actual_position:.1%}"
    )
    return actual_position, cue_label


def load_deck(
    mixxx: MixxxControl,
    deck: int,
    path: str,
    cue_fraction: float = 0.1,
    cue_seconds: float | None = None,
    expected_bpm: float | None = None,
) -> None:
    group = deck_group(deck)
    mixxx.set(group, "play", 0)
    # A freed deck can still carry the previous track's deliberate tempo or
    # key bridge. BPM is a *rate-adjusted* Mixxx readback, so neutralize those
    # controls before loading and before using BPM as the new-track identity
    # barrier. Otherwise a valid new track can wait forever for its native BPM.
    mixxx.set(group, "rate", 0.0)
    mixxx.set(group, "pitch_adjust", 0.0)
    try:
        mixxx.set(group, "eject", 1)
        _wait_for(mixxx, group, "track_loaded", lambda v: v < 0.5, 5.0)
    except TimeoutError:
        pass
    mixxx.load(deck, path)
    mixxx.set(group, "rate", 0.0)
    mixxx.set(group, "pitch_adjust", 0.0)
    _wait_for(mixxx, group, "track_loaded", lambda v: v >= 0.5, LOAD_TIMEOUT_S)
    # track_loaded may remain true across a replacement. Waiting only for a
    # positive BPM/duration can therefore accept the previous track's stale
    # values and cue the wrong file. The plan knows the intended analyzed BPM,
    # so use it as the load-identity barrier before touching playposition.
    tolerance = max(0.35, (expected_bpm or 0.0) * 0.01)
    bpm = _wait_for(
        mixxx,
        group,
        "bpm",
        lambda v: v > 0 and (
            expected_bpm is None or abs(v - expected_bpm) <= tolerance
        ),
        LOAD_TIMEOUT_S,
    )
    duration = _wait_for(mixxx, group, "duration", lambda v: v > 0, LOAD_TIMEOUT_S)
    _, cue_label = cue_deck(
        mixxx,
        deck,
        cue_fraction=cue_fraction,
        cue_seconds=cue_seconds,
        duration=duration,
    )
    mixxx.set(group, "volume", 1.0)
    mixxx.set(group, "keylock", 1)
    mixxx.set(group, "quantize", 1)
    mixxx.set(group, "rate", 0.0)
    mixxx.set(group, "pitch_adjust", 0.0)
    print(
        f"[load] deck {deck}: {Path(path).name}  "
        f"({duration:.0f}s, {bpm:.2f} BPM, cue {cue_label})"
    )


def ensure_deck_playing(mixxx: MixxxControl, deck: int) -> None:
    """Recover a live deck whose play control was lost during a preload."""
    group = deck_group(deck)
    if mixxx.get(group, "play") >= 0.5:
        return
    print(f"  (deck {deck} was stopped unexpectedly; resuming at its current cue)")
    mixxx.set(group, "play", 1)
    _wait_for(mixxx, group, "play", lambda value: value >= 0.5, 3.0)


def apply_moves(mixxx: MixxxControl, from_deck: int, to_deck: int, moves: list[str]) -> None:
    """Pre-transition instrument gestures (EQ/filter/scratch)."""
    out_g, in_g = deck_group(from_deck), deck_group(to_deck)
    for move in moves:
        if move == "eq_kill_out_low":
            try:
                mixxx.set(eq_group(from_deck), "parameter1", 0.0)
            except Exception:
                pass
        elif move == "eq_boost_in_mid":
            try:
                mixxx.set(eq_group(to_deck), "parameter2", 0.7)
            except Exception:
                pass
        elif move == "eq_dip_out_mid":
            try:
                mixxx.set(eq_group(from_deck), "parameter2", 0.25)
            except Exception:
                pass
        elif move == "eq_kill_out_high":
            try:
                mixxx.set(eq_group(from_deck), "parameter3", 0.0)
            except Exception:
                pass
        elif move == "eq_restore":
            for deck in (from_deck, to_deck):
                try:
                    eg = eq_group(deck)
                    mixxx.set(eg, "parameter1", 0.5)
                    mixxx.set(eg, "parameter2", 0.5)
                    mixxx.set(eg, "parameter3", 0.5)
                except Exception:
                    pass
        elif move == "filter_open_in":
            try:
                mixxx.set(filter_group(to_deck), "super1", 0.65)
            except Exception:
                pass
        elif move == "filter_sweep_out":
            try:
                # sweep filter closed on outgoing
                for value in (0.5, 0.35, 0.2, 0.1):
                    mixxx.set(filter_group(from_deck), "super1", value)
                    time.sleep(0.05)
            except Exception:
                pass
        elif move == "filter_reset":
            for deck in (from_deck, to_deck):
                try:
                    mixxx.set(filter_group(deck), "super1", 0.5)
                except Exception:
                    pass
        elif move == "rate_nudge_in":
            mixxx.set(in_g, "rate", 0.05)
        elif move == "optional_scratch_in":
            # Briefly reveal a rate-wiggle, then restore the analyzed cue.
            cue = mixxx.get(in_g, "playposition")
            start_cf = mixxx.get("[Master]", "crossfader")
            preview_cf = start_cf + 0.28 * (crossfader_target(to_deck) - start_cf)
            mixxx.set(in_g, "keylock", 0)
            mixxx.set(in_g, "play", 1)
            for i in range(6):
                mixxx.set(in_g, "rate", -0.6 if i % 2 == 0 else 0.7)
                mixxx.set("[Master]", "crossfader", preview_cf if i % 2 else start_cf)
                time.sleep(0.07)
            mixxx.set("[Master]", "crossfader", start_cf)
            mixxx.set(in_g, "rate", 0.0)
            mixxx.set(in_g, "keylock", 1)
            mixxx.set(in_g, "play", 0)
            mixxx.set(in_g, "playposition", cue)
        elif move == "optional_loop_roll_out":
            try:
                mixxx.set(out_g, "beatloop_4_activate", 1)
                time.sleep(0.4)
                mixxx.set(out_g, "reloop_toggle", 1)
            except Exception:
                pass
        elif move == "echo_out_exit":
            echo_out_exit(mixxx, from_deck)
        # sync / crossfade handled by transition()


# Convention, not a runtime lookup: Mixxx exposes no load-by-name control
# (EffectSlot's `loaded_effect` only takes a 1-indexed position in the
# visible-effects list, which isn't stable across machines/plugin sets —
# see docs/MIXXX_CONTROL_SURFACE.md). So one unit+slot is reserved by
# convention for Echo, loaded ONCE by hand via the Mixxx GUI. On this
# machine's skin that ended up being Unit 2 / slot 3 (the compact 4-DECKS
# effects strips don't label unit numbers, so match whatever's actually
# loaded rather than fight the GUI for a specific slot). Everything after
# that load is name-stable (enabled/mix/routing) — no further GUI
# interaction or index guessing is ever needed.
ECHO_UNIT = "[EffectRack1_EffectUnit2]"
ECHO_SLOT = "[EffectRack1_EffectUnit2_Effect3]"


def echo_ready(mixxx: MixxxControl) -> bool:
    try:
        return mixxx.get(ECHO_SLOT, "loaded") > 0.5
    except Exception:
        return False


def echo_out_exit(mixxx: MixxxControl, deck: int) -> None:
    """Echo-out: route the outgoing deck through the reserved Echo unit,
    ring the tail in as its volume drops, then leave the unit routed off
    (echo naturally decays into the still-playing incoming track).

    No-ops (with a one-time note) if Echo hasn't been loaded into the
    configured unit/slot — see ECHO_UNIT/ECHO_SLOT above.
    """
    global _echo_missing_noted
    if not echo_ready(mixxx):
        if not _echo_missing_noted:
            print(f"  (Echo not loaded into {ECHO_SLOT} — echo_out_exit skipped;"
                  " one-time GUI step, see docs/MIXXX_CONTROL_SURFACE.md)")
            _echo_missing_noted = True
        return
    group = deck_group(deck)
    route_key = f"group_{group}_enable"
    mixxx.set(ECHO_SLOT, "enabled", 1)
    mixxx.set(ECHO_UNIT, route_key, 1)
    mixxx.set(ECHO_UNIT, "mix", 0.0)
    steps = 20
    for i in range(steps + 1):
        progress = i / steps
        mixxx.set(ECHO_UNIT, "mix", progress)
        mixxx.set(group, "volume", 1.0 - progress)
        time.sleep(0.05)
    # Deck volume restored on its next load; echo unit unrouted so it
    # doesn't color whatever plays through this effect unit next.
    mixxx.set(group, "volume", 1.0)
    mixxx.set(ECHO_UNIT, route_key, 0)
    mixxx.set(ECHO_UNIT, "mix", 0.0)


_echo_missing_noted = False


def perform_juggle_intro(mixxx: MixxxControl, event: dict) -> None:
    """Cool DJ-intro juggle: load a second copy of the opener on the other
    deck, chop the crossfader back and forth between the two identical
    copies over the first few bars, then land cleanly on the opener deck
    and let it continue playing straight through -- nothing in the
    beginning gets skipped, it's just presented as a flashy juggle first.

    The other deck is borrowed temporarily; the plan's following `load`
    event reloads the real second track onto it afterward.
    """
    deck = int(event["deck"])
    other = 2 if deck == 1 else 1
    group, other_group = deck_group(deck), deck_group(other)
    track_id = event.get("track_id")
    if not track_id:
        print("  juggle_intro: no track_id on this event, falling back to a plain start")
        mixxx.set("[Master]", "crossfader", crossfader_target(deck))
        mixxx.set(group, "play", 1)
        return

    mixxx.set(group, "volume", 1.0)
    mixxx.set(group, "play", 1)
    bpm = mixxx.get(group, "bpm") or 95.0
    period = 60.0 / max(60.0, min(200.0, bpm))

    load_deck(mixxx, other, track_id, cue_seconds=0.0, expected_bpm=bpm)
    mixxx.set(other_group, "volume", 1.0)
    mixxx.set(other_group, "play", 1)

    chops = max(2, int(event.get("juggle_chops", 6)))
    hold_beats = float(event.get("juggle_hold_beats", 1.0))
    print(f"  juggle_intro: {chops} chops between deck {deck} and deck {other} "
          f"on {event.get('track')}")
    for i in range(chops):
        active = deck if i % 2 == 0 else other
        mixxx.set("[Master]", "crossfader", crossfader_target(active))
        time.sleep(hold_beats * period)

    # Land on the opener deck, kill the borrowed copy -- deck plays on
    # uninterrupted from wherever the juggle left it (no rewind: the point
    # is nothing gets skipped overall).
    mixxx.set("[Master]", "crossfader", crossfader_target(deck))
    mixxx.set(other_group, "play", 0)
    print(f"  juggle landed on deck {deck}; playing straight through")


def perform_opener_effect(mixxx: MixxxControl, event: dict, *, port: int) -> None:
    """Tease the opener, echo/fade it out, rewind, and arm a clean first drop."""
    deck = int(event["deck"])
    group = deck_group(deck)
    style = str(event.get("style") or "echo_tease_drop")

    if style == "juggle_intro":
        perform_juggle_intro(mixxx, event)
        return

    cue_position = mixxx.get(group, "playposition")
    mixxx.set("[Master]", "crossfader", crossfader_target(deck))
    mixxx.set(group, "volume", 1.0)
    mixxx.set(group, "play", 1)
    tease_beats = max(1, int(event.get("tease_beats", 4)))
    print(f"  {style}: teasing {event.get('track')} for {tease_beats} beats")
    wait_for_beats(port, group, tease_beats, timeout_s=15.0)
    if style == "echo_tease_drop" and echo_ready(mixxx):
        echo_out_exit(mixxx, deck)
    else:
        # Portable fallback when the reserved Echo slot is not loaded.
        for step in range(10, -1, -1):
            mixxx.set(group, "volume", step / 10.0)
            time.sleep(0.04)
    mixxx.set(group, "play", 0)
    mixxx.set(group, "rate", 0.0)
    mixxx.set(group, "pitch_adjust", 0.0)
    mixxx.set(group, "playposition", cue_position)
    _wait_for(
        mixxx,
        group,
        "playposition",
        lambda value: abs(value - cue_position) <= 0.002,
        2.0,
    )
    mixxx.set(group, "volume", 1.0)
    print("  opener rewound; clean drop armed")


def perform_transition(mixxx: MixxxControl, event: dict, *, port: int) -> None:
    """Execute one beat-anchored transition with continuous instrument curves."""
    from_deck = int(event["from_deck"])
    to_deck = int(event["to_deck"])
    beats = int(event.get("transition_beats", 16))
    moves = list(event.get("moves") or [])
    technique = event.get("technique", "standard_blend")
    out_g, in_g = deck_group(from_deck), deck_group(to_deck)
    bpm = mixxx.get(out_g, "bpm")
    if bpm <= 0:
        raise RuntimeError(f"{out_g} reports no BPM")
    # A deliberate incoming_bpm_target (dj_notes play_bpm) sets a specific
    # bridge tempo below via set_bpm_target -- beatsync is a one-shot
    # resync to whatever the outgoing deck is actually playing at, and
    # firing it afterward silently overwrites that target back toward the
    # outgoing tempo. Found 2026-07-16: Tha Shiznit's play_bpm=103 bridge
    # was getting reverted this way, audible as "still sounds slow".
    sync = (
        "sync" in moves
        and technique != "half_time_or_cut"
        and event.get("incoming_bpm_target") is None
    )
    # Hard cuts are rare by design — only explicit hard_cut move or the
    # extreme-tempo half_time_or_cut technique (key_clash is now a blend).
    hard = technique in {"key_clash_cut", "half_time_or_cut"} or "hard_cut" in moves

    if event.get("incoming_bpm_target") is not None:
        set_bpm_target(mixxx, to_deck, float(event["incoming_bpm_target"]))

    key_shift = 0.0
    if "key_blend" in moves:
        key_shift = float(event.get("pitch_adjust_semitones") or 0.0)
        if abs(key_shift) > 2.0:
            raise ValueError(f"unsafe key-blend shift {key_shift:+g}; plan limit is ±2 semitones")
        if key_shift:
            mixxx.set(in_g, "pitch_adjust", key_shift)
            print(
                f"  key bridge {key_shift:+g} st"
                f" -> {event.get('pitch_adjust_target', 'compatible key')}"
            )

    # Slip fills on the outgoing deck right before the landing — Rust
    # gestures, beat-anchored internally. Position keeps advancing under
    # slip, so the transition anchor below still lands on grid.
    if "stutter_fill" in moves and rust_gesture(
            "stutter", "--deck", str(from_deck), "--rolls", "2", "--size", "0.5", port=port):
        print("  stutter fill (slip loop-roll)")
    elif "censor_fill" in moves and rust_gesture(
            "censor", "--deck", str(from_deck), "--beats", "2", port=port):
        print("  censor fill (slip reverse)")

    # Platter exits: brake/spinback the outgoing deck to silence, THEN the
    # incoming track hits. The moment of quiet is the drama — use sparingly.
    if "brake_out" in moves or "spinback_out" in moves:
        gesture = ("spinback", "--deck", str(from_deck), "--seconds", "1.6") \
            if "spinback_out" in moves else ("brake", "--deck", str(from_deck), "--seconds", "1.4")
        wait_for_next_beat(port, out_g)
        if rust_gesture(*gesture, port=port):
            mixxx.set("[Master]", "crossfader", crossfader_target(to_deck))
            mixxx.set(deck_group(to_deck), "play", 1)
            print(f"  {gesture[0]} exit -> deck {to_deck}")
            return
        # No binary: fall through to the anchored hard cut below.

    print(f"  anchoring on {out_g} beat ({bpm:.2f} BPM)")
    wait_for_next_beat(port, out_g)
    mixxx.set(in_g, "play", 1)
    if sync:
        mixxx.set(in_g, "beatsync", 1)

    start_cf = mixxx.get("[Master]", "crossfader")
    end_cf = crossfader_target(to_deck)
    if hard:
        mixxx.set("[Master]", "crossfader", end_cf)
        mixxx.set(out_g, "play", 0)
        print(f"  on-beat cut -> deck {to_deck} ({'sync' if sync else 'native tempo'})")
        return

    fade_s = beats * 60.0 / bpm
    bass_swap = any(move in moves for move in ("eq_kill_out_low", "eq_dip_out_mid", "eq_kill_out_high"))
    # Ernest, 2026-07-14: hip-hop needs bass "front and center" -- do NOT
    # pre-kill the incoming deck's low end at progress=0. The old code did,
    # and for a long transition (e.g. 44 beats ≈ 28s) that left the incoming
    # track fully bassless for ~14s while it was actively growing more
    # prominent on the crossfader (audible on Runnin' Wit No Breaks). The
    # incoming deck now keeps its normal bass throughout; only the outgoing
    # deck's bass is killed, and only right at the handoff (progress>=0.5),
    # by which point it's fading out anyway.
    swapped = False
    t0 = time.monotonic()
    while True:
        progress = min(1.0, (time.monotonic() - t0) / fade_s)
        curve = smoothstep(progress)
        mixxx.set("[Master]", "crossfader", start_cf + (end_cf - start_cf) * curve)
        if bass_swap and progress >= 0.5 and not swapped:
            mixxx.set(eq_group(from_deck), "parameter1", 0.0)
            mixxx.set(eq_group(to_deck), "parameter1", 0.5)
            swapped = True
            print("  bass swap")
        if "filter_sweep_out" in moves:
            try:
                mixxx.set(filter_group(from_deck), "super1", 0.5 - 0.4 * curve)
            except Exception:
                pass
        if key_shift and progress >= 0.5:
            # The outgoing deck masks the adjusted key during the first half
            # of the overlap. As it disappears, glide the incoming deck back
            # to native so there is no post-landing pitch jump.
            release = min(1.0, (progress - 0.5) / 0.5)
            mixxx.set(in_g, "pitch_adjust", key_shift * (1.0 - smoothstep(release)))
        if "optional_transformer_cuts" in moves and progress > 0.72:
            # Four restrained chops near the landing, still ending on target.
            phase = int((progress - 0.72) / 0.07)
            if phase < 4 and phase % 2 == 0:
                mixxx.set("[Master]", "crossfader", start_cf)
        if progress >= 1.0:
            break
        time.sleep(0.02)

    mixxx.set("[Master]", "crossfader", end_cf)
    if key_shift:
        mixxx.set(in_g, "pitch_adjust", 0.0)
    mixxx.set(out_g, "play", 0)
    if event.get("landing_seconds") is not None:
        duration = mixxx.get(in_g, "duration")
        actual_landing = mixxx.get(in_g, "playposition") * duration
        expected_landing = float(event["landing_seconds"])
        tolerance = float(event.get("landing_tolerance_seconds", 1.0))
        if abs(actual_landing - expected_landing) > tolerance:
            raise RuntimeError(
                f"verse landing missed: expected {expected_landing:.3f}s, "
                f"Mixxx reports {actual_landing:.3f}s"
            )
        print(
            f"  verse landing verified at {actual_landing:.3f}s "
            f"(target {expected_landing:.3f}s)"
        )
    print(f"  {beats}-beat landing -> deck {to_deck}")


def start_recording(mixxx: MixxxControl, *, timeout_s: float = 5.0) -> bool:
    """Toggle Mixxx's [Recording],toggle_recording on. Returns True if this
    call is the one that started it (so the caller knows to stop it later —
    never touch a recording someone else already had running)."""
    if mixxx.get("[Recording]", "status") >= 1.0:
        print("  already recording (started outside this run) — leaving it alone")
        return False
    mixxx.set("[Recording]", "toggle_recording", 1)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if mixxx.get("[Recording]", "status") >= 1.0:
            print("  recording started (WAV — see Mixxx Preferences > Recording for the directory; "
                  "convert to mp3 afterward with ffmpeg if you want one)")
            return True
        time.sleep(0.1)
    print("  WARNING: asked Mixxx to start recording but status never went high — "
          "check a recording directory is configured in Preferences > Recording")
    return False


def stop_recording(mixxx: MixxxControl, *, timeout_s: float = 5.0) -> None:
    mixxx.set("[Recording]", "toggle_recording", 1)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if mixxx.get("[Recording]", "status") < 1.0:
            print("  recording stopped")
            return
        time.sleep(0.1)
    print("  WARNING: asked Mixxx to stop recording but status never went low — check Mixxx directly")


def run_plan(
    plan: dict, *, port: int, dry_run: bool, max_events: int | None, record: bool = False
) -> None:
    events = plan["events"]
    if max_events:
        events = events[:max_events]

    if dry_run:
        for i, event in enumerate(events, 1):
            op = event.get("op")
            print(f"{i:03d}  {op:24}  {json.dumps({k: v for k, v in event.items() if k != 'op'})[:140]}")
        print(f"dry-run: {len(events)} events (no Mixxx connection)")
        return

    expected_bpms = {
        track.get("track_id"): track.get("bpm")
        for track in (plan.get("tracks") or [])
        if track.get("track_id")
    }
    with MixxxControl(port=port, timeout_s=LOAD_TIMEOUT_S + 5) as mixxx:
        we_started_recording = False
        if record:
            print("starting recording…")
            we_started_recording = start_recording(mixxx)
        try:
            _run_events(mixxx, events, expected_bpms, port=port)
        finally:
            if we_started_recording:
                print("\nstopping recording…")
                stop_recording(mixxx)


def _run_events(mixxx: MixxxControl, events: list[dict], expected_bpms: dict, *, port: int) -> None:
    pending_preload: dict | None = None
    for i, event in enumerate(events, 1):
        op = event["op"]
        print(f"\n[{i}/{len(events)}] {op}")
        if op == "reset_instrument":
            reset_instrument(mixxx)
        elif op == "opener_effect":
            perform_opener_effect(mixxx, event, port=port)
        elif op == "recue":
            _, cue_label = cue_deck(
                mixxx,
                int(event["deck"]),
                cue_fraction=float(event.get("cue_fraction", 0.1)),
                cue_seconds=event.get("cue_seconds"),
            )
            print(f"  deck {event['deck']} re-cued: {cue_label}")
        elif op == "load":
            load_deck(
                mixxx,
                event["deck"],
                event["track_id"],
                event.get("cue_fraction", 0.1),
                event.get("cue_seconds"),
                expected_bpms.get(event["track_id"]),
            )
        elif op == "start":
            deck = event["deck"]
            mixxx.set("[Master]", "crossfader", crossfader_target(deck))
            mixxx.set(deck_group(deck), "play", 1)
            print(f"  deck {deck} playing")
        elif op == "play_body":
            beats = event.get("beats")
            seconds = float(event.get("seconds", 30))
            if beats is not None:
                print(f"  riding {event.get('track')} for {beats} live beats")
            else:
                print(f"  riding {event.get('track')} for {seconds:.0f}s")
            print(f"  hints: {event.get('instrument_hints')}")
            ensure_deck_playing(mixxx, int(event["deck"]))
            if beats is not None:
                # timeout scales with the ride: full verses (verse tour) can outlast
                # the old fixed 90s at slower tempos
                wait_for_beats(port, deck_group(int(event["deck"])), int(beats),
                               timeout_s=max(90.0, int(beats) * 1.5))
            else:
                time.sleep(seconds)
        elif op == "preload_after_transition":
            pending_preload = event
        elif op == "transition":
            from_deck = int(event["from_deck"])
            to_deck = int(event["to_deck"])
            beats = int(event.get("transition_beats", 16))
            moves = list(event.get("moves") or [])
            print(f"  {event.get('technique')}: {event.get('from_track')} → {event.get('to_track')}")
            print(f"  moves: {moves}")
            print(f"  notes: {event.get('notes')}")
            # Ensure incoming is loaded (may already be)
            preview_moves = {
                "optional_scratch_in",
                "optional_loop_roll_out",
                "rate_nudge_in",
                "eq_boost_in_mid",
                "filter_open_in",
            }
            apply_moves(mixxx, from_deck, to_deck, [move for move in moves if move in preview_moves])
            perform_transition(mixxx, event, port=port)
            # restore EQ/filter after land
            apply_moves(mixxx, from_deck, to_deck, ["eq_restore", "filter_reset"])
            if event.get("incoming_bpm_target") is not None:
                print(
                    f"  holding deck {to_deck} at bridge tempo "
                    f"{float(event['incoming_bpm_target']):.2f} BPM"
                )
            else:
                settle_rate(mixxx, to_deck)
            if pending_preload and pending_preload.get("deck") == from_deck:
                print(f"  preload next into freed deck {from_deck}")
                load_deck(
                    mixxx,
                    from_deck,
                    pending_preload["track_id"],
                    pending_preload.get("cue_fraction", 0.1),
                    pending_preload.get("cue_seconds"),
                    expected_bpms.get(pending_preload["track_id"]),
                )
                pending_preload = None
        elif op == "finale":
            beats = event.get("beats")
            seconds = float(event.get("seconds", 30))
            if event.get("play_to_end"):
                deck = int(event["deck"])
                group = deck_group(deck)
                print(f"  finale {event.get('track')} (play to end)")
                ensure_deck_playing(mixxx, deck)
                deadline = time.monotonic() + seconds + 30.0
                while time.monotonic() < deadline:
                    if mixxx.get(group, "play") < 0.5 or mixxx.get(group, "playposition") >= 0.999:
                        break
                    time.sleep(0.25)
            elif beats:
                print(f"  finale {event.get('track')} ({beats} beats)")
                ensure_deck_playing(mixxx, int(event["deck"]))
                # timeout scales with the ride: full verses (verse tour) can outlast
                # the old fixed 90s at slower tempos
                wait_for_beats(port, deck_group(int(event["deck"])), int(beats),
                               timeout_s=max(90.0, int(beats) * 1.5))
            else:
                print(f"  finale {event.get('track')} ({seconds:.0f}s)")
                time.sleep(seconds)
        elif op == "stop_all":
            for deck in (1, 2):
                mixxx.set(deck_group(deck), "play", 0)
            print("  stopped")
        else:
            print(f"  (skip unknown op {op})")
    print("\nmix plan complete")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN_DEFAULT)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-events", type=int, default=None, help="execute only the first N events")
    parser.add_argument(
        "--record", action="store_true",
        help="record the set via Mixxx's own recorder (WAV by default — this build has no mp3 "
             "encoder; convert afterward with ffmpeg, or rebuild Mixxx with -DFFMPEG=ON for "
             "native mp3). Starts/stops automatically around the plan; never touches a recording "
             "that was already running.",
    )
    args = parser.parse_args()
    if not args.plan.exists():
        raise SystemExit(f"missing {args.plan} — run: uv run python -m brain.build_mix_plan")
    plan = json.loads(args.plan.read_text())
    run_plan(plan, port=args.port, dry_run=args.dry_run, max_events=args.max_events, record=args.record)


if __name__ == "__main__":
    main()
