"""Build a continuous multi-song mix plan from the filtered playlist.

Turns the curated/enriched ordered set into an executable sequence of Mixxx
"instrument" moves: load, cue, play, sync, EQ kills, filter sweeps, rate
nudges, crossfades, optional scratch-ins and beat juggles.

Does not play audio by itself — write brain/data/mix_plan.json, then:
    uv run python -m hands.run_mix_plan
    uv run python -m hands.run_mix_plan --dry-run

Usage:
    uv run python -m brain.build_mix_plan --tracks 8
    uv run python -m brain.build_mix_plan --tracks 6 --seconds-per-track 45
"""
from __future__ import annotations

import argparse
import json
import re
from contextlib import closing
from pathlib import Path

from brain.mix_graph import bpm_compatibility, key_compatibility, parse_key

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_PLAYLIST = DATA_DIR / "playlist.json"
DEFAULT_AFFINITY = DATA_DIR / "mix_affinity.json"
DEFAULT_PHRASES = DATA_DIR / "phrase_analysis.json"
DEFAULT_PLAN = DATA_DIR / "mix_plan.json"

_PITCH_CLASS_NAMES = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)


def pitch_adjust_for_blend(
    outgoing_key: str | None,
    incoming_key: str | None,
    *,
    max_semitones: int = 2,
) -> dict | None:
    """Find the smallest bounded shift that makes the incoming key friendly.

    Mixxx's ``pitch_adjust`` is expressed in semitones (and supports ±3), but
    a one- or two-semitone bridge is the most we want to expose as an ordinary
    blend technique. The mode stays fixed; only the incoming tonic moves.
    """
    outgoing = parse_key(outgoing_key)
    incoming = parse_key(incoming_key)
    if not outgoing or not incoming:
        return None
    current_score, _ = key_compatibility(outgoing_key, incoming_key)
    if current_score >= 0.85:
        return None

    number, mode = incoming
    # Camelot 8A = A minor (pitch class 9), 8B = C major (pitch class 0).
    base = 9 if mode == "A" else 0
    pitch_class = (base + 7 * (number - 8)) % 12
    candidates: list[tuple[int, float, int, str, str | None]] = []
    for distance in range(1, max_semitones + 1):
        for semitones in (-distance, distance):
            target_note = _PITCH_CLASS_NAMES[(pitch_class + semitones) % 12]
            target_key = f"{target_note}m" if mode == "A" else target_note
            score, reason = key_compatibility(outgoing_key, target_key)
            if score >= 0.85:
                # Prefer the smallest audible shift, then the stronger match.
                candidates.append((distance, -score, semitones, target_key, reason))
        if candidates:
            break
    if not candidates:
        return None
    _, neg_score, semitones, target_key, reason = min(candidates)
    return {
        "semitones": semitones,
        "target_key": target_key,
        "compatibility": -neg_score,
        "reason": reason,
    }


def load_affinity_lookup(path: Path = DEFAULT_AFFINITY) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    pairs = payload.get("pairs", payload if isinstance(payload, list) else [])
    out = {}
    for row in pairs:
        out[tuple(sorted((row["a"], row["b"])))] = row
    return out


def load_phrase_lookup(path: Path = DEFAULT_PHRASES) -> dict[str, dict]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    rows = payload.get("tracks", payload if isinstance(payload, list) else [])
    return {row["track_id"]: row for row in rows}


def load_dj_notes_lookup() -> dict[str, str]:
    """Persistent human track knowledge; automated enrichment never edits it."""
    from brain.library_index import connect

    with closing(connect()) as db:
        return {
            row["track_id"]: row["dj_notes"] or ""
            for row in db.execute("SELECT track_id, dj_notes FROM tracks WHERE dj_notes != ''")
        }


def load_lyric_line_lookup() -> dict[str, list[float]]:
    """Sorted lyric-line start times per track, from synced LRC where it
    exists — used to snap a cue point onto an actual word boundary instead
    of trusting the beatgrid/energy phrase-picker blindly (it has no idea
    where a word starts; it can and does land mid-syllable)."""
    from brain.library_index import connect
    from brain.lyric_timeline import parse_lrc

    with closing(connect()) as db:
        rows = db.execute(
            "SELECT track_id, lrc FROM lyric_timelines WHERE lrc IS NOT NULL"
        ).fetchall()
    out: dict[str, list[float]] = {}
    for row in rows:
        lines = parse_lrc(row["lrc"])
        if lines:
            out[row["track_id"]] = sorted(line.t for line in lines if line.text.strip())
    return out


def load_beat_phase_lookup() -> dict[str, dict]:
    """Cached real onset/waveform snare-parity analysis (brain.onset_analysis),
    keyed by track_id -- {"snare_parity": 0|1, "confidence": float, "bpm":
    float, "first_beat_seconds": float}. Filled by
    brain.enrich_set.fill_beat_phase. Missing entries (a track never
    analyzed yet) simply skip the phase check below rather than erroring --
    same graceful-degradation pattern as phrase_lookup/lyric_line_lookup."""
    from brain.library_index import connect

    with closing(connect()) as db:
        rows = db.execute(
            "SELECT track_id, snare_parity, confidence, bpm, first_beat_seconds FROM beat_phase"
        ).fetchall()
    return {
        row["track_id"]: {
            "snare_parity": row["snare_parity"],
            "confidence": row["confidence"],
            "bpm": row["bpm"],
            "first_beat_seconds": row["first_beat_seconds"],
        }
        for row in rows
    }


def snap_to_lyric_line(
    cue_seconds: float, track_id: str, lyric_line_lookup: dict[str, list[float]], *, max_snap_s: float = 6.0
) -> tuple[float, bool]:
    """Nudge a cue point forward to the nearest lyric-line start at or after
    it, so playback never begins mid-word. Never snaps backward (that would
    replay content the phrase-picker's energy target already skipped past)
    and gives up (returns the original point) if the nearest line is
    further away than `max_snap_s` — likely an instrumental stretch, where
    forcing a snap would drift too far from the intended entry point."""
    lines = lyric_line_lookup.get(track_id)
    if not lines:
        return cue_seconds, False
    for start in lines:
        if start >= cue_seconds:
            if start - cue_seconds <= max_snap_s:
                return start, True
            return cue_seconds, False
    return cue_seconds, False


def track_directives(track: dict) -> dict:
    """Parse small machine-readable hints embedded in natural DJ notes."""
    notes = str(track.get("dj_notes") or "")

    def number(name: str) -> float | None:
        # The LAST match wins, not the first: by convention the real
        # directive sits at the end of the note, but prose earlier in the
        # same note sometimes narrates an old value (e.g. "was
        # ride_beats=128, now ...") for human context. Taking the first
        # match silently picked up stale history twice in one session
        # before this was made the parser's own responsibility instead of
        # relying on every note's author never mentioning an old number.
        matches = re.findall(rf"\b{re.escape(name)}\s*=\s*(\d+(?:\.\d+)?)", notes, re.I)
        return float(matches[-1]) if matches else None

    def word(name: str) -> str | None:
        matches = re.findall(rf"\b{re.escape(name)}\s*=\s*([a-z_]+)", notes, re.I)
        return matches[-1].casefold() if matches else None

    return {
        "cue_seconds": number("cue_seconds"),
        "ride_phrases": int(value) if (value := number("ride_phrases")) is not None else None,
        "ride_beats": int(value) if (value := number("ride_beats")) is not None else None,
        "play_bpm": number("play_bpm"),
        "entry_style": word("entry_style"),
        "exit_style": word("exit_style"),
        "opener_style": word("opener_style"),
        "landing_seconds": number("landing_seconds"),
        "landing_beats": int(value) if (value := number("landing_beats")) is not None else None,
        "full_track": bool(re.search(r"\bfull_track\b", notes, re.I)),
        "no_flourish": bool(re.search(r"\bno_flourish\b", notes, re.I)),
        # Ear override: the human certified this exact ride length by
        # listening -- the beat-phase auto-nudge must NOT touch it. Needed
        # because the nudge's snare-parity input can be a near-coin-flip
        # measurement (seen live 2026-07-19: confidence 0.015 drove a nudge
        # the ear then flagged as off by one).
        "trust_ride_beats": bool(re.search(r"\btrust_ride_beats\b", notes, re.I)),
    }


def pick_technique(
    left: dict, right: dict, affinity: dict | None, *, avoid_silence: bool = False
) -> dict:
    """Choose how to play Mixxx between two tracks — instrument vocabulary.

    Default bias (Ernest, hackathon set): *blend* most of the time. Abrupt
    hard cuts are rare — reserved for extreme tempo gaps with no texture
    support (a "drop" moment), not the everyday path.

    `avoid_silence=True` (club-set, mix-to-listen) removes even that rare
    brake/hard-cut fallback — the floor should never stop moving, so an
    extreme tempo gap downgrades to the smoother always-blending
    tempo_gap_blend instead of a dramatic stop.
    """
    bpm_s, bpm_r = bpm_compatibility(left.get("bpm"), right.get("bpm"))
    key_s, key_r = key_compatibility(left.get("key"), right.get("key"))
    reasons = [r for r in (bpm_r, key_r) if r]
    lineage = bool(affinity and any("lineage" in r.lower() or "sample" in r.lower() for r in affinity.get("reasons", [])))
    lyric = float((affinity or {}).get("lyric_score") or 0)
    chroma = float((affinity or {}).get("chroma_score") or 0)
    score = float((affinity or {}).get("score") or (0.45 * bpm_s + 0.35 * key_s))

    key_adjust = (
        pitch_adjust_for_blend(left.get("key"), right.get("key"))
        if bpm_s >= 0.9 and key_s < 0.5
        else None
    )

    # Technique selection — map musical situation → Mixxx knobs/moves.
    # Prefer longer crossfades; only hard_cut when the gap is truly ugly.
    if lineage or lyric > 0.2:
        technique = "sample_callback_blend"
        beats = 28
        notes = "Hold the shared sample/hook in the blend; EQ-swap lows so the sample bed stays continuous."
        moves = ["eq_kill_out_low", "eq_boost_in_mid", "sync", "long_crossfade", "filter_open_in"]
    elif bpm_s >= 0.9 and key_s >= 0.85:
        technique = "smooth_blend"
        beats = 20
        notes = "Near-identical tempo + friendly key — long crossfade with light EQ."
        moves = ["sync", "eq_dip_out_mid", "crossfade", "eq_restore"]
    elif key_adjust is not None:
        technique = "key_adjusted_blend"
        beats = 16
        shift = key_adjust["semitones"]
        notes = (
            f"Tempo works; shift the incoming deck {shift:+d} semitone(s) to "
            f"{key_adjust['target_key']} for the overlap, then return smoothly "
            "to its native key as the outgoing deck disappears."
        )
        moves = ["key_blend", "sync", "filter_sweep_out", "crossfade", "filter_reset", "eq_restore"]
    elif bpm_s >= 0.9 and key_s < 0.5:
        # Unknown/unfixable keys retain the masking recipe rather than making
        # up a pitch adjustment.
        technique = "key_clash_blend"
        beats = 16
        notes = (
            "Tempo works; key is rough — filter-sweep blend masks the clash "
            "because no safe ±2-semitone bridge was found."
        )
        moves = ["sync", "filter_sweep_out", "crossfade", "filter_reset", "eq_restore"]
    elif bpm_s < 0.35 and not lineage and chroma < 0.55 and not avoid_silence:
        # Rare hard cut: only when tempos are far apart and nothing else backs the pair.
        technique = "half_time_or_cut"
        beats = 4
        notes = (
            "Extreme tempo gap with no texture/lineage support — brake the outgoing "
            "platter to a stop, then the new track hits (falls back to a phrase-anchored "
            "hard cut without the clawdj binary). Use sparingly."
        )
        moves = ["brake_out", "hard_cut", "optional_loop_roll_out"]
    elif bpm_s < 0.5:
        technique = "tempo_gap_blend"
        beats = 16
        notes = "Tempo gap large — rate-nudge into a longer EQ/filter blend rather than a slam cut."
        # No "sync" here on purpose: beatsync fully snaps the incoming deck
        # to whatever the outgoing deck is ACTUALLY playing at, which for a
        # genuinely large gap means an audible, jarring speed change (heard
        # live, 2026-07-16: "the speed up... shouldn't be that fast, it
        # sounds terrible"). rate_nudge_in already gives a small, bounded
        # taste of movement (+5%) without forcing a full hard tempo-match —
        # let the mismatch stand and be masked by the EQ/filter blend
        # instead, which is what "rather than a slam cut" already promised.
        moves = ["rate_nudge_in", "filter_sweep_out", "crossfade", "filter_reset", "eq_restore"]
    elif chroma > 0.7:
        technique = "chroma_matched_blend"
        beats = 20
        notes = "Chromagram similar (tonal bed) — trust a longer EQ blend even if keys differ slightly."
        moves = ["sync", "eq_kill_out_high", "crossfade", "eq_restore"]
    else:
        technique = "standard_blend"
        beats = 16
        notes = "Default instrument path: sync, mid scoop, longer crossfade."
        moves = ["sync", "eq_dip_out_mid", "crossfade", "eq_restore"]

    # Showcase spice every few transitions when compatibility is high —
    # scratch preview only, never upgrades a blend into a hard cut.
    if score >= 0.75 and technique in {
        "smooth_blend",
        "sample_callback_blend",
        "chroma_matched_blend",
        "standard_blend",
    }:
        moves = ["optional_scratch_in", *moves]
        notes += " Optional scratch-in on the incoming deck before the fade."

    result = {
        "technique": technique,
        "transition_beats": beats,
        "score": round(score, 3),
        "reasons": reasons + (affinity or {}).get("reasons", [])[:3],
        "moves": moves,
        "notes": notes,
        "lineage_story": lineage,
        "lyric_score": lyric,
        "chroma_score": chroma,
    }
    if key_adjust is not None and technique == "key_adjusted_blend":
        result.update(
            pitch_adjust_semitones=key_adjust["semitones"],
            pitch_adjust_target=key_adjust["target_key"],
            pitch_adjust_compatibility=key_adjust["compatibility"],
        )
        result["reasons"].append(
            f"pitch bridge {right.get('key')}→{key_adjust['target_key']} "
            f"({key_adjust['semitones']:+d} st)"
        )
    return result


def build_plan(
    tracks: list[dict],
    *,
    count: int,
    seconds_per_track: float,
    affinity_lookup: dict[tuple[str, str], dict],
    phrase_lookup: dict[str, dict] | None = None,
    lyric_line_lookup: dict[str, list[float]] | None = None,
    beat_phase_lookup: dict[str, dict] | None = None,
    phrase_beats: int = 32,
    profile: "MixProfile | None" = None,
    provenance: dict | None = None,
) -> dict:
    from brain.mix_profiles import PROFILES
    from brain.onset_analysis import count_shift_beats

    profile = profile or PROFILES["dj-showcase"]
    selected = tracks[:count]
    if len(selected) < 2:
        raise SystemExit("need at least 2 tracks in the filtered playlist")

    phrase_lookup = phrase_lookup or {}
    lyric_line_lookup = lyric_line_lookup or {}
    beat_phase_lookup = beat_phase_lookup or {}
    # Populated by cue_fields() below every time it resolves an absolute
    # cue_seconds for a track -- lets the phase-parity check (further down)
    # look up each track's OWN entry beat_index without re-deriving it.
    cue_beat_index_cache: dict[str, int] = {}
    events: list[dict] = []

    def _remember_cue_beat_index(track_id: str, result: dict) -> dict:
        """Cache the resolved beat_index for this cue so the phase-parity
        check further down can find each track's OWN entry beat_index
        without re-deriving it (needed once this track later becomes the
        OUTGOING side of a transition)."""
        cue_seconds = result.get("cue_seconds")
        phase = beat_phase_lookup.get(track_id)
        if cue_seconds is not None and phase:
            period = 60.0 / phase["bpm"]
            cue_beat_index_cache[track_id] = round(
                (cue_seconds - phase["first_beat_seconds"]) / period
            )
        return result

    def cue_fields(track: dict, fallback_fraction: float, slot: int = 0) -> dict:
        directive = track_directives(track)
        if directive["cue_seconds"] is not None:
            return _remember_cue_beat_index(track["track_id"], {
                "cue_seconds": directive["cue_seconds"],
                "cue_confidence": 1.0,
                "cue_source": "dj_notes",
                "dj_notes": track.get("dj_notes") or "",
            })
        if (
            directive["landing_seconds"] is not None
            and directive["landing_beats"] is not None
            and track.get("bpm")
        ):
            # Incoming audio begins at the start of the overlap. Pre-roll by
            # exactly the overlap length so the requested lyric lands when
            # the crossfader reaches the incoming deck.
            cue_seconds = max(
                0.0,
                directive["landing_seconds"]
                - directive["landing_beats"] * 60.0 / float(track["bpm"]),
            )
            return _remember_cue_beat_index(track["track_id"], {
                "cue_seconds": round(cue_seconds, 3),
                "landing_seconds": directive["landing_seconds"],
                "landing_beats": directive["landing_beats"],
                "cue_confidence": 1.0,
                "cue_source": "dj_notes_landing",
                "dj_notes": track.get("dj_notes") or "",
            })
        phrase = phrase_lookup.get(track["track_id"])
        if not phrase:
            duration = track.get("duration_seconds")
            if duration:
                raw = fallback_fraction * duration
                snapped, did_snap = snap_to_lyric_line(raw, track["track_id"], lyric_line_lookup)
                if did_snap:
                    return _remember_cue_beat_index(track["track_id"], {
                        "cue_seconds": round(snapped, 3),
                        "cue_source": "fraction_fallback+lyric_snap",
                    })
            return {"cue_fraction": fallback_fraction, "cue_source": "fraction_fallback"}
        body = phrase.get("body")
        intro = phrase.get("intro")
        # Default entry: a high-energy phrase past the intro (chorus / first
        # verse). Intros are softer — interesting occasionally, so roughly
        # every 4th slot takes the intro instead, when it holds up. (DJ note
        # from Ernest: don't open every track from the top.)
        pick, source = (body, "phrase_body") if body else (None, "mixxx_beatgrid+energy")
        intro_every = profile.intro_entry_every
        if intro and (
            body is None
            or (
                intro_every
                and slot % intro_every == intro_every // 2
                and intro["score"] >= 0.75 * body["score"]
            )
        ):
            pick, source = intro, "phrase_intro"
        if pick is None:
            pick = phrase
        # The beatgrid/energy phrase-picker has no idea where a word starts —
        # it can and does land mid-syllable. Never start in the middle of a
        # word: snap forward to the nearest actual lyric-line start when
        # synced lyrics are available (Ernest, 2026-07-16, caught on Cassie
        # — Me&U landing on "...wanna see if it's true").
        cue_seconds, did_snap = snap_to_lyric_line(
            pick["cue_seconds"], track["track_id"], lyric_line_lookup
        )
        if did_snap:
            source = f"{source}+lyric_snap"
        return _remember_cue_beat_index(track["track_id"], {
            "cue_seconds": cue_seconds,
            "cue_beat_index": pick.get("beat_index"),
            "cue_confidence": pick.get("confidence"),
            "cue_source": source,
        })
    # Instrument reset
    events.append(
        {
            "op": "reset_instrument",
            "detail": "Zero rates, open EQ, crossfader left, keylock+quantize on",
        }
    )

    # Load first two decks
    events.append(
        {
            "op": "load",
            "deck": 1,
            "track_id": selected[0]["track_id"],
            "artist": selected[0]["artist"],
            "title": selected[0]["title"],
            **cue_fields(selected[0], 0.08, 0),
        }
    )
    events.append(
        {
            "op": "load",
            "deck": 2,
            "track_id": selected[1]["track_id"],
            "artist": selected[1]["artist"],
            "title": selected[1]["title"],
            **cue_fields(selected[1], 0.12, 1),
        }
    )
    opener_directive = track_directives(selected[0])
    if opener_directive["opener_style"]:
        events.append(
            {
                "op": "opener_effect",
                "deck": 1,
                "style": opener_directive["opener_style"],
                "tease_beats": 4,
                "track": f"{selected[0]['artist']} — {selected[0]['title']}",
                "track_id": selected[0]["track_id"],
                "detail": "Tease the iconic opening, echo it out, rewind, then drop clean.",
            }
        )
        # juggle_intro/juggle_brake_intro reuse deck 2 to juggle a second
        # copy of the opener track (see hands.run_mix_plan) and leave it
        # loaded there when they stop — a bare "recue" only re-seeks whatever
        # is currently loaded, it can't reload, so without this the first
        # transition would crossfade back into the opener track instead of
        # the real second track. Explicitly reload deck 2 with the actual
        # next track once the opener effect is done.
        events.append(
            {
                "op": "load",
                "deck": 2,
                "track_id": selected[1]["track_id"],
                "artist": selected[1]["artist"],
                "title": selected[1]["title"],
                **cue_fields(selected[1], 0.12, 1),
            }
        )
    start_event = {
        "op": "start",
        "deck": 1,
        "detail": "Play deck 1; deck 2 cued and silent until first transition",
    }
    if opener_directive["play_bpm"] is not None:
        # The opener has no incoming transition to hang pick_technique's
        # incoming_bpm_target on (that's the only other place play_bpm gets
        # applied) — without this, a play_bpm directive on track 0 silently
        # did nothing. Bump it the moment it actually starts playing instead.
        start_event["bpm_target"] = opener_directive["play_bpm"]
    events.append(start_event)

    live_deck = 1
    play_s = seconds_per_track
    segments = []
    previous_fade_beats = 0

    for index in range(len(selected) - 1):
        outgoing = selected[index]
        incoming = selected[index + 1]
        out_deck = live_deck
        in_deck = 2 if live_deck == 1 else 1
        aff = affinity_lookup.get(tuple(sorted((outgoing["track_id"], incoming["track_id"]))))
        tech = pick_technique(outgoing, incoming, aff, avoid_silence=profile.avoid_silence)
        incoming_directive = track_directives(incoming)

        # Compatibility chooses the base recipe; the profile controls how
        # often we show off and how long the landing takes.
        if profile.transition_scale != 1.0:
            scaled = tech["transition_beats"] * profile.transition_scale
            tech["transition_beats"] = max(4, int(round(scaled / 4)) * 4)
        tech["moves"] = [move for move in tech["moves"] if move != "optional_scratch_in"]
        flourish = "bass_swap"
        if profile.flourish_every and index % profile.flourish_every == 0 and not incoming_directive["no_flourish"]:
            # Rotation includes the Rust slip gestures (stutter/censor);
            # the runner degrades them to plain blends when the clawdj
            # binary is missing, so plans stay portable.
            rotation = (
                "bass_swap",
                "scratch_preview",
                "stutter_fill",
                "loop_roll",
                "censor_fill",
                "transformer_cut",
            )
            flourish = rotation[(index // profile.flourish_every) % len(rotation)]
        if flourish == "scratch_preview" and tech["score"] >= 0.7:
            tech["moves"].insert(0, "optional_scratch_in")
        elif flourish == "loop_roll":
            tech["moves"].insert(0, "optional_loop_roll_out")
        elif flourish == "transformer_cut":
            tech["moves"].insert(0, "optional_transformer_cuts")
        elif flourish in ("stutter_fill", "censor_fill"):
            tech["moves"].insert(0, flourish)
        tech["showcase_move"] = flourish

        if index < profile.smooth_opening_transitions:
            tech["transition_beats"] = max(24, tech["transition_beats"])
            tech["moves"] = [
                move for move in tech["moves"]
                if move not in {
                    "optional_scratch_in", "optional_loop_roll_out",
                    "optional_transformer_cuts", "stutter_fill", "censor_fill",
                    "brake_out", "spinback_out", "hard_cut",
                }
            ]
            # The opening must sound continuous even when the ordinary
            # compatibility recipe would have chosen a dramatic tempo cut.
            if tech["technique"] == "half_time_or_cut":
                tech.update(
                    technique="tempo_gap_blend",
                    # See the other tempo_gap_blend definition above for why
                    # "sync" is deliberately absent.
                    moves=["rate_nudge_in", "filter_sweep_out", "crossfade", "filter_reset", "eq_restore"],
                )
            tech["showcase_move"] = "smooth_opening"
            tech["notes"] += " Opening directive: longer beat-matched blend, no flourish."

        incoming_directive = track_directives(incoming)
        if incoming_directive["entry_style"] == "beat_drop":
            tech.update(
                technique="beat_drop_entry",
                transition_beats=4,
                moves=["brake_out", "hard_cut"],
                showcase_move="beat_drop",
                notes=(
                    "Human DJ note: brake/stop the outgoing track, then start "
                    "the incoming track from its opening as an abrupt beat drop."
                ),
            )
        elif incoming_directive["entry_style"] == "gentle_blend":
            tech.update(
                technique="tempo_bridge_blend",
                transition_beats=max(24, tech["transition_beats"]),
                moves=[
                    "sync", "eq_dip_out_mid", "filter_sweep_out",
                    "crossfade", "filter_reset", "eq_restore",
                ],
                showcase_move="gentle_blend",
                notes=(
                    "Human DJ note: use a gentle, longer synced blend from "
                    "the outgoing track's held bridge tempo."
                ),
            )
        elif incoming_directive["entry_style"] == "verse_landing":
            landing_beats = incoming_directive["landing_beats"] or 24
            tech.update(
                technique="verse_landing_blend",
                transition_beats=landing_beats,
                landing_seconds=incoming_directive["landing_seconds"],
                landing_tolerance_seconds=1.0,
                moves=[
                    "sync", "eq_dip_out_mid", "filter_sweep_out",
                    "crossfade", "filter_reset", "eq_restore",
                ],
                showcase_move="verse_landing",
                notes=(
                    "Human DJ note: pre-roll the incoming track during a "
                    f"{landing_beats}-beat overlap so the crossfader lands "
                    f"on its requested verse at {incoming_directive['landing_seconds']:.3f}s."
                ),
            )
        if incoming_directive["play_bpm"] is not None:
            tech["incoming_bpm_target"] = incoming_directive["play_bpm"]

        # Reserve the final beat for perform_transition() to anchor on. After
        # the first fade, the incoming deck has already consumed fade beats of
        # its phrase, so only count the remainder before the next anchor.
        elapsed_in_phrase = previous_fade_beats
        next_boundary = phrase_beats
        while next_boundary <= elapsed_in_phrase:
            next_boundary += phrase_beats

        # Showcase pacing varies (Ernest, 2026-07-12): not every segment is
        # one phrase — some key parts get to play out, never the whole song.
        # The profile's slot rotation gives the baseline; a confident phrase
        # pick earns an extra phrase.
        pattern = profile.ride_phrases_pattern
        ride_phrases = pattern[index % len(pattern)]
        directive = track_directives(outgoing)
        if directive["exit_style"] == "echo_out":
            # Echo-out exit (docs/DJ_TRANSITIONS_PLAYBOOK.md #4): the
            # outgoing track fades under a rising echo tail, then the
            # incoming starts clean at its own tempo. The standard gentle
            # answer for large tempo gaps -- nothing rhythmic overlaps, so
            # no tempo bridging (and none of tempo_gap_blend's forced
            # stretch) is needed. Directive-driven only, per the playbook's
            # "use as an exit strategy, not a habit" warning. Overrides the
            # incoming's entry_style: there is no overlap to land into.
            tech.update(
                technique="echo_out_exit",
                transition_beats=4,
                moves=["echo_out_exit"],
                showcase_move="echo_out",
                notes=(
                    "Human DJ note: echo-out exit -- fade the outgoing track "
                    "under a rising echo tail, then start the incoming clean "
                    "at its own tempo. No tempo bridging."
                ),
            )
        if directive["ride_phrases"] is not None:
            ride_phrases = max(1, min(8, directive["ride_phrases"]))
        out_phrase = phrase_lookup.get(outgoing["track_id"]) or {}
        if directive["ride_phrases"] is None and ride_phrases == 1 and (out_phrase.get("confidence") or 0.0) >= profile.confidence_extra_phrase:
            ride_phrases = 2
        next_boundary += (ride_phrases - 1) * phrase_beats
        ride_beats = max(0, next_boundary - elapsed_in_phrase - 1)
        if directive["ride_beats"] is not None:
            ride_beats = max(0, min(512, directive["ride_beats"]))

        # Real onset/waveform check (brain.onset_analysis): a standard
        # backbeat puts the snare on every OTHER beat, so which beat-in-bar
        # the transition anchors on (kick vs. snare position) is a real,
        # audible property -- not just a tempo-matching question. Mixxx's
        # generic beatsync locks GENERIC beat ticks together; it has no
        # idea whether that lines up actual drum hits. Found live,
        # 2026-07-16/17: three separate "beats don't match" complaints
        # traced to real, confirmed parity mismatches this check would
        # have caught automatically. Only runs when both tracks have
        # cached analysis (brain.enrich_set.fill_beat_phase) -- silently
        # skipped otherwise, same graceful-degradation pattern as
        # phrase_lookup/lyric_line_lookup.
        outgoing_phase = beat_phase_lookup.get(outgoing["track_id"])
        incoming_phase = beat_phase_lookup.get(incoming["track_id"])
        outgoing_entry_beat = cue_beat_index_cache.get(outgoing["track_id"])
        incoming_entry_beat = cue_beat_index_cache.get(incoming["track_id"])
        if (
            not directive["trust_ride_beats"]
            and outgoing_phase and incoming_phase
            and outgoing_entry_beat is not None and incoming_entry_beat is not None
        ):
            shift = count_shift_beats(
                outgoing_snare_parity=outgoing_phase["snare_parity"],
                outgoing_anchor_beat_index=outgoing_entry_beat + ride_beats,
                incoming_snare_parity=incoming_phase["snare_parity"],
                incoming_cue_beat_index=incoming_entry_beat,
            )
            if shift:
                print(
                    f"  [beat-phase] {outgoing['artist']} — {outgoing['title']} -> "
                    f"{incoming['artist']} — {incoming['title']}: nudging ride_beats "
                    f"{ride_beats} -> {ride_beats + shift} to match snare parity"
                )
                ride_beats += shift

        # Play body of outgoing track
        events.append(
            {
                "op": "play_body",
                "deck": out_deck,
                "seconds": play_s,
                "beats": ride_beats,
                "ride_phrases": ride_phrases,
                "track": f"{outgoing['artist']} — {outgoing['title']}",
                "instrument_hints": [
                    "Optional: tweak [ChannelN] filterHighEq mid-phrase",
                    "Optional: beatjump_1_forward to skip to chorus",
                    "Optional: beatloop_4_toggle for a loop-roll fill",
                ],
            }
        )

        # Prefetch next-next track onto free deck after transition starts planning
        if index + 2 < len(selected):
            nxt = selected[index + 2]
            events.append(
                {
                    "op": "preload_after_transition",
                    "deck": out_deck,  # the deck that will free after fade
                    "track_id": nxt["track_id"],
                    "artist": nxt["artist"],
                    "title": nxt["title"],
                    **cue_fields(nxt, 0.1, index + 2),
                }
            )

        events.append(
            {
                "op": "transition",
                "from_deck": out_deck,
                "to_deck": in_deck,
                "from_track": f"{outgoing['artist']} — {outgoing['title']}",
                "to_track": f"{incoming['artist']} — {incoming['title']}",
                **tech,
            }
        )
        segments.append(
            {
                "index": index,
                "from": f"{outgoing['artist']} — {outgoing['title']}",
                "to": f"{incoming['artist']} — {incoming['title']}",
                "technique": tech["technique"],
                "beats": tech["transition_beats"],
                "score": tech["score"],
                "showcase_move": tech["showcase_move"],
                **(
                    {
                        "pitch_adjust_semitones": tech["pitch_adjust_semitones"],
                        "pitch_adjust_target": tech["pitch_adjust_target"],
                    }
                    if "pitch_adjust_semitones" in tech
                    else {}
                ),
            }
        )
        live_deck = in_deck
        previous_fade_beats = tech["transition_beats"]

    final_track = selected[-1]
    final_directive = track_directives(final_track)
    final_cue = cue_fields(final_track, 0.1, len(selected) - 1)
    full_seconds = None
    if final_directive["full_track"] and final_track.get("duration_seconds"):
        cue_seconds = float(final_cue.get("cue_seconds") or 0.0)
        full_seconds = max(1.0, float(final_track["duration_seconds"]) - cue_seconds)
    finale = {
        "op": "finale",
        "deck": live_deck,
        "seconds": full_seconds if full_seconds is not None else play_s,
        "track": f"{final_track['artist']} — {final_track['title']}",
        "detail": (
            "Play the human-requested remainder of the full track"
            if full_seconds is not None
            else "Ride out the last track; optional loop_roll or EQ kill for ending"
        ),
    }
    if full_seconds is not None:
        finale["play_to_end"] = True
    if full_seconds is None:
        finale["beats"] = max(16, phrase_beats - previous_fade_beats)
    events.append(finale)
    events.append({"op": "stop_all"})

    return {
        "version": 2,
        "track_count": len(selected),
        "seconds_per_track": seconds_per_track,
        "profile": provenance or {"name": profile.name},
        "phrase_interval_beats": phrase_beats,
        "tracks": [
            {
                "artist": t["artist"],
                "title": t["title"],
                "bpm": t.get("bpm"),
                "key": t.get("key"),
                "track_id": t["track_id"],
                "dj_notes": t.get("dj_notes") or "",
                **cue_fields(t, 0.1, slot),
            }
            for slot, t in enumerate(selected)
        ],
        "segments": segments,
        "events": events,
        "instrument_map": INSTRUMENT_MAP,
    }


INSTRUMENT_MAP = {
    "transport": {
        "play/pause": "[ChannelN],play",
        "cue_jump": "[ChannelN],cue_gotoandplay or playposition",
        "sync": "[ChannelN],beatsync",
        "keylock": "[ChannelN],keylock",
        "quantize": "[ChannelN],quantize",
    },
    "levels": {
        "volume": "[ChannelN],volume",
        "pregain": "[ChannelN],pregain",
        "crossfader": "[Master],crossfader  (-1=deck1 … +1=deck2)",
        "headMix": "[Master],headMix",
    },
    "tempo_pitch": {
        "rate": "[ChannelN],rate  (-1..1 pitch slider)",
        "rate_temp": "nudge for slip",
        "bpm_read": "[ChannelN],bpm",
        "key_bridge": "[ChannelN],pitch_adjust  (bounded ±1..2 semitones)",
    },
    "eq_filter": {
        "eq_low": "[EqualizerRack1_[ChannelN]_Effect1],parameter1",
        "eq_mid": "[EqualizerRack1_[ChannelN]_Effect1],parameter2",
        "eq_high": "[EqualizerRack1_[ChannelN]_Effect1],parameter3",
        "quick_filter": "[QuickEffectRack1_[ChannelN]],super1  (filter knob)",
    },
    "phrase_tools": {
        "beatjump": "[ChannelN],beatjump_1_forward / beatjump_4_forward / …",
        "loop": "[ChannelN],beatloop_4_toggle / beatloop_8_toggle",
        "hotcues": "[ChannelN],hotcue_X_activate",
        "reverse_reverseroll": "[ChannelN],reverseroll",
    },
    "fx_ideas": {
        "echo_out": "reserved Echo slot routed to outgoing during exit",
        "flanger_build": "EffectUnit2 wet increase into drop",
    },
}


def compose_mix_plan(
    *,
    playlist: Path = DEFAULT_PLAYLIST,
    profile_name: str = "dj-showcase",
    mix_brief: str = "",
    order_engine: str = "none",
    tracks: int | None = None,
    seconds_per_track: float | None = None,
    phrase_analysis: Path = DEFAULT_PHRASES,
    phrase_beats: int | None = None,
    out: Path = DEFAULT_PLAN,
    ask=None,
) -> dict:
    """Build a mix plan from the finalized playlist and write it to disk.

    Same logic as the CLI entrypoint so the playlist editor and
    `python -m brain.build_mix_plan` stay in lockstep. `tracks=None` means
    "use every analyzed song in the playlist" (the editor default); the CLI
    still defaults to 8 for short demos.

    `order_engine`: when the brief asks for specific pairings / placement /
    a short subset, use `nemoclaw` or `h-agent` to turn that into order
    constraints (see `brain.mix_order_brief`). `none` keeps playlist order
    and only maps feel keywords onto the profile.
    """
    from brain.mix_profiles import PROFILES, apply_brief, profile_provenance

    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile {profile_name!r}; choose from {sorted(PROFILES)}")
    if not playlist.exists():
        raise FileNotFoundError(
            f"missing {playlist} — finalize a set first (playlist editor → Finalize for Mixxx)"
        )

    profile, brief_notes = apply_brief(PROFILES[profile_name], mix_brief)
    rows = json.loads(playlist.read_text())
    dj_notes = load_dj_notes_lookup()
    for row in rows:
        row["dj_notes"] = dj_notes.get(row.get("track_id"), row.get("dj_notes") or "")
    analyzed = [t for t in rows if t.get("bpm")]
    pool = analyzed if len(analyzed) >= 2 else rows
    if len(pool) < 2:
        raise ValueError("need at least 2 tracks with BPM in the finalized playlist")

    order_notes: list[str] = []
    order_constraints: dict | None = None
    if mix_brief.strip() and order_engine not in (None, "", "none", "off", "profile-only"):
        from brain.mix_order_brief import order_from_brief

        pool, order_notes, order_constraints = order_from_brief(
            pool, mix_brief, engine=order_engine, ask=ask
        )

    count = len(pool) if tracks is None else min(tracks, len(pool))
    # When the agent narrowed to a short showcase, don't re-inflate with tracks.
    if order_constraints and order_constraints.get("use_only"):
        count = len(pool)
    provenance = profile_provenance(profile, mix_brief, brief_notes)
    provenance["order_engine"] = order_engine
    provenance["order_notes"] = order_notes
    if order_constraints is not None:
        # Keep provenance path-free / short-id only.
        provenance["order_constraints"] = {
            "use_only": order_constraints.get("use_only"),
            "opener_id": order_constraints.get("opener_id"),
            "adjacent": [list(p) for p in order_constraints.get("adjacent") or []],
            "adjacent_ordered": order_constraints.get("adjacent_ordered"),
            "regions": order_constraints.get("regions"),
            "notes": order_constraints.get("notes"),
        }
    plan = build_plan(
        pool,
        count=count,
        seconds_per_track=seconds_per_track if seconds_per_track is not None else profile.seconds_per_track,
        affinity_lookup=load_affinity_lookup(),
        phrase_lookup=load_phrase_lookup(phrase_analysis),
        lyric_line_lookup=load_lyric_line_lookup(),
        beat_phase_lookup=load_beat_phase_lookup(),
        phrase_beats=phrase_beats if phrase_beats is not None else profile.phrase_beats,
        profile=profile,
        provenance=provenance,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def plan_summary(plan: dict, *, plan_path: Path | None = None) -> dict:
    """Dry-run-style summary for the UI — no Mixxx connection required."""
    segments = plan.get("segments") or []
    events = plan.get("events") or []
    techniques: dict[str, int] = {}
    for seg in segments:
        name = seg.get("technique") or "unknown"
        techniques[name] = techniques.get(name, 0) + 1
    cue_sources: dict[str, int] = {}
    for track in plan.get("tracks") or []:
        source = track.get("cue_source") or "unknown"
        cue_sources[source] = cue_sources.get(source, 0) + 1
    profile = plan.get("profile") or {}
    return {
        "plan_path": str(plan_path) if plan_path else None,
        "version": plan.get("version"),
        "track_count": plan.get("track_count"),
        "event_count": len(events),
        "segment_count": len(segments),
        "seconds_per_track": plan.get("seconds_per_track"),
        "phrase_interval_beats": plan.get("phrase_interval_beats"),
        "profile": profile,
        "order_engine": profile.get("order_engine"),
        "order_notes": profile.get("order_notes") or [],
        "techniques": techniques,
        "cue_sources": cue_sources,
        "tracks": [
            {
                "track_id": t.get("track_id"),
                "artist": t.get("artist"),
                "title": t.get("title"),
                "bpm": t.get("bpm"),
                "key": t.get("key"),
                "cue_source": t.get("cue_source"),
            }
            for t in (plan.get("tracks") or [])
        ],
        "segments": segments,
        "dry_run_ok": True,
        "dry_run_note": f"{len(events)} events validated in-process (no Mixxx connection)",
    }


def main() -> None:
    from brain.mix_profiles import PROFILES

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--tracks", type=int, default=8, help="how many songs in the continuous mix")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="dj-showcase",
        help="how the set should feel; explicit flags below still win",
    )
    parser.add_argument(
        "--mix-brief",
        default="",
        help="free-text mix description: feel keywords AND/OR order asks "
             "(e.g. 'smooth; put Parce Que Tu Crois next to What's The Difference "
             "in the first half')",
    )
    parser.add_argument(
        "--order-engine",
        choices=("none", "nemoclaw", "h-agent"),
        default="none",
        help="when the brief asks for pairings/placement/subset, resolve order "
             "via NemoClaw or H-agent (default: none = playlist order + feel only)",
    )
    parser.add_argument("--seconds-per-track", type=float, default=None)
    parser.add_argument("--phrase-analysis", type=Path, default=DEFAULT_PHRASES)
    parser.add_argument("--phrase-beats", type=int, default=None, choices=(16, 32, 48, 64))
    parser.add_argument("--out", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()

    plan = compose_mix_plan(
        playlist=args.playlist,
        profile_name=args.profile,
        mix_brief=args.mix_brief,
        order_engine=args.order_engine,
        tracks=args.tracks,
        seconds_per_track=args.seconds_per_track,
        phrase_analysis=args.phrase_analysis,
        phrase_beats=args.phrase_beats,
        out=args.out,
    )
    profile = plan.get("profile") or {}
    print(f"profile: {profile.get('name')} — {(profile.get('values') or {}).get('description', '')}")
    for note in profile.get("brief_adjustments") or []:
        print(f"  brief adjustment: {note}")
    for note in profile.get("order_notes") or []:
        print(f"  order: {note}")
    print(f"mix plan: {plan['track_count']} tracks -> {args.out}")
    for seg in plan["segments"]:
        print(
            f"  {seg['index']+1:02d}. [{seg['technique']:22}] {seg['beats']:2} beats  "
            f"{seg['from']} → {seg['to']}  (score {seg['score']})"
        )
    print("\nMixxx instrument controls used are listed in plan['instrument_map'].")
    print("Run: uv run python -m hands.run_mix_plan --dry-run")
    print("Live: uv run python -m hands.run_mix_plan   # Mixxx --control-api-port 9995")


if __name__ == "__main__":
    main()
