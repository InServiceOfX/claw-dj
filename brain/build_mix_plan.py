"""Build a continuous multi-song mix plan from the filtered playlist.

Turns the curated/enriched ordered set into an executable sequence of Mixxx
"instrument" moves: load, cue, play, sync, EQ kills, filter sweeps, rate
nudges, crossfades, effects and beat juggles.

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
import os
import re
from contextlib import closing
from pathlib import Path

from brain.mix_graph import bpm_compatibility, key_compatibility, parse_key
from brain.phrase_analysis import seekable_cue_seconds, usable_first_beat_seconds
from brain.verse import fill_segment_lookup, respect_verse_entry, respect_verse_exit

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


def load_lyric_segment_lookup() -> dict[str, list[dict]]:
    """Detected verse/chorus segments used by strict DJ formats."""
    from brain.library_index import connect

    with closing(connect()) as db:
        rows = db.execute(
            "SELECT track_id, segments FROM lyric_timelines WHERE segments != '[]'"
        ).fetchall()
    out: dict[str, list[dict]] = {}
    for row in rows:
        try:
            segments = json.loads(row["segments"])
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(segments, list) and segments:
            out[row["track_id"]] = segments
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
        "settle_bpm": number("settle_bpm"),
        "exit_bpm": number("exit_bpm"),
        "tempo_ramp_beats": int(value) if (value := number("tempo_ramp_beats")) is not None else None,
        "entry_style": word("entry_style"),
        "exit_style": word("exit_style"),
        "opener_style": word("opener_style"),
        "format_recipe": word("format_recipe"),
        "juggle_chops": int(value) if (value := number("juggle_chops")) is not None else None,
        "juggle_hold_beats": (
            float(value) if (value := number("juggle_hold_beats")) is not None else None
        ),
        # Remix Report ep.12: bars of brake/vocal *before* the real downbeat.
        # Start those early so beat N is on 1 — never treat the pickup as beat 1.
        "pickup_beats": (
            int(value) if (value := number("pickup_beats")) is not None else None
        ),
        # Remix Report 088–099: chorus length in bars (4 beats each). An
        # 8-bar DJ intro against a 10-bar chorus waits 2 bars; against a
        # 6-bar chorus skips 2 bars of the intro. Long (16+) choruses mix
        # out at 8 — do not put 24 here.
        "chorus_bars": (
            int(value) if (value := number("chorus_bars")) is not None else None
        ),
        "landing_seconds": number("landing_seconds"),
        "landing_beats": int(value) if (value := number("landing_beats")) is not None else None,
        "intro_seconds": number("intro_seconds"),
        "chorus_seconds": number("chorus_seconds"),
        "hook_acapella_seconds": number("hook_acapella_seconds"),
        "intro_loop_seconds": number("intro_loop_seconds"),
        "full_track": bool(re.search(r"\bfull_track\b", notes, re.I)),
        "no_flourish": bool(re.search(r"\bno_flourish\b", notes, re.I)),
        # Ear override: the human certified this exact ride length by
        # listening -- the beat-phase auto-nudge must NOT touch it. Needed
        # because the nudge's snare-parity input can be a near-coin-flip
        # measurement (seen live 2026-07-19: confidence 0.015 drove a nudge
        # the ear then flagged as off by one).
        "trust_ride_beats": bool(re.search(r"\btrust_ride_beats\b", notes, re.I)),
        # After Mixxx beatsync, jump one beat so snares lock.
        # +1 / bare snare_align: jump incoming forward.
        # -1: jump outgoing forward (same relative flip; works when the
        # incoming cue is at beat 0 and a backward jump would clamp).
        "snare_align": (
            int(signed[-1])
            if (signed := re.findall(r"\bsnare_align\s*=\s*([+-]?\d+)", notes, re.I))
            else (1 if re.search(r"\bsnare_align\b", notes, re.I) else 0)
        ),
        # Rare escape hatch for an ear-certified cue that deliberately sits
        # between analyzed beatgrid lines. Ordinary cues are snapped to the
        # nearest real beat below; otherwise a half-beat cue can never be
        # repaired by changing an integer ride count.
        "trust_cue_seconds": bool(re.search(r"\btrust_cue_seconds\b", notes, re.I)),
        # Ear-certified: stay at the blend tempo after landing. Do not glide
        # back to the analyzed native BPM (chipmunk-safe records only).
        "keep_blend_tempo": bool(re.search(r"\bkeep_blend_tempo\b", notes, re.I)),
        # Loop the outgoing bed under a dry vocal (instrumental section of a
        # full mix). vocal_over_bed uses this; ignored for other entry styles.
        "bed_loop_beats": (
            int(value) if (value := number("bed_loop_beats")) is not None else None
        ),
        # Skip a middle region (e.g. a guest verse) while the deck keeps playing.
        "skip_from_seconds": number("skip_from_seconds"),
        "skip_to_seconds": number("skip_to_seconds"),
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


def beat_index_for_seconds(
    track: dict,
    seconds: float,
    *,
    phrase_lookup: dict[str, dict],
    beat_phase_lookup: dict[str, dict],
) -> int:
    """Resolve an absolute time onto this track's analyzed beatgrid.

    Strict DJ-format annotations are allowed only when they are close to a
    real beat.  The returned index is later checked for bar-downbeat parity.
    """
    grid = phrase_lookup.get(track["track_id"]) or beat_phase_lookup.get(
        track["track_id"]
    )
    if not grid or not grid.get("bpm") or grid.get("first_beat_seconds") is None:
        raise ValueError(
            f"{track['artist']} — {track['title']}: strict DJ format needs "
            "an analyzed beatgrid (run Analyze & enrich missing)"
        )
    bpm = float(grid["bpm"])
    first = usable_first_beat_seconds(grid["first_beat_seconds"])
    raw_index = (float(seconds) - first) / (60.0 / bpm)
    beat_index = round(raw_index)
    # Timestamps from synced lyrics are approximate, so allow one fifth of a
    # beat; anything further away is not defensible as a beat-1 annotation.
    if abs(raw_index - beat_index) > 0.20:
        raise ValueError(
            f"{track['artist']} — {track['title']}: {seconds:.3f}s is not "
            "close enough to an analyzed beat for strict on-the-1 mixing"
        )
    return beat_index


def seconds_for_beat(
    track: dict,
    beat_index: int,
    *,
    phrase_lookup: dict[str, dict],
    beat_phase_lookup: dict[str, dict],
) -> float:
    grid = phrase_lookup.get(track["track_id"]) or beat_phase_lookup.get(
        track["track_id"]
    )
    if not grid or not grid.get("bpm") or grid.get("first_beat_seconds") is None:
        raise ValueError(
            f"{track['artist']} — {track['title']}: strict DJ format needs "
            "an analyzed beatgrid"
        )
    return round(
        usable_first_beat_seconds(grid["first_beat_seconds"])
        + beat_index * 60.0 / float(grid["bpm"]),
        3,
    )


def build_plan(
    tracks: list[dict],
    *,
    count: int,
    seconds_per_track: float,
    affinity_lookup: dict[tuple[str, str], dict],
    phrase_lookup: dict[str, dict] | None = None,
    lyric_line_lookup: dict[str, list[float]] | None = None,
    lyric_segment_lookup: dict[str, list[dict]] | None = None,
    beat_phase_lookup: dict[str, dict] | None = None,
    phrase_beats: int = 32,
    profile: "MixProfile | None" = None,
    dj_format: "DjFormat | None" = None,
    provenance: dict | None = None,
    transition_beats_by_pair: dict[tuple[str, str], int] | None = None,
    legacy_parity: bool = True,
) -> dict:
    from brain.dj_formats import format_provenance, get_format
    from brain.mix_profiles import PROFILES
    from brain.onset_analysis import count_shift_beats

    profile = profile or PROFILES["dj-showcase"]
    dj_format = dj_format or get_format("none")
    if dj_format.planner not in (
        None,
        "hiphop_rnb_8bar",
        "hiphop_rnb_guided",
    ):
        raise ValueError(
            f"DJ format {dj_format.name!r} names unsupported planner "
            f"{dj_format.planner!r}"
        )
    selected = tracks[:count]
    if len(selected) < 2:
        raise SystemExit("need at least 2 tracks in the filtered playlist")

    phrase_lookup = phrase_lookup or {}
    lyric_line_lookup = lyric_line_lookup or {}
    lyric_segment_lookup = lyric_segment_lookup or {}
    beat_phase_lookup = beat_phase_lookup or {}
    transition_beats_by_pair = transition_beats_by_pair or {}
    # Populated by cue_fields() below every time it resolves an absolute
    # cue_seconds for a track -- lets the phase-parity check (further down)
    # look up each track's OWN entry beat_index without re-deriving it.
    cue_beat_index_cache: dict[str, int] = {}
    format_cue_evidence_cache: dict[str, dict] = {}
    events: list[dict] = []
    selected_by_id = {track["track_id"]: track for track in selected}

    def _remember_cue_beat_index(track_id: str, result: dict) -> dict:
        """Snap an ordinary cue to its grid and cache its absolute index.

        A lyric timestamp or file fraction is a content marker, not a beat
        marker.  Rounding only the index while leaving playback at the raw
        timestamp made the planner reason about one phase while Mixxx played
        another (Paradise and Late Night Bliss were both almost half a beat
        out).  Keep the actual cue and cached index as one invariant.
        """
        result = dict(result)
        if "format_intro_verified" in result:
            format_cue_evidence_cache[track_id] = {
                "verified": bool(result["format_intro_verified"]),
                "source": result.get("cue_source"),
                "reason": result.get("format_intro_reason"),
            }
        cue_seconds = result.get("cue_seconds")
        phase = beat_phase_lookup.get(track_id) or phrase_lookup.get(track_id)
        first_beat = (
            usable_first_beat_seconds(phase.get("first_beat_seconds"))
            if phase and phase.get("first_beat_seconds") is not None
            else None
        )
        if (
            cue_seconds is not None
            and phase
            and phase.get("bpm")
            and first_beat is not None
        ):
            period = 60.0 / float(phase["bpm"])
            # Preserve source-grid provenance even when a human cue is
            # deliberately between grid lines or this track has no solo body.
            result["source_grid"] = {"grid_bpm": float(phase["bpm"]), "first_beat_seconds": first_beat}
            raw_index = (float(cue_seconds) - first_beat) / period
            # The analyzed grid's public beat indices start at zero.  A cue
            # near the file head can round to a hypothetical negative beat;
            # clamping only its seconds would make the stored index disagree
            # with what Mixxx actually plays.  Clamp the index first.
            beat_index = max(0, round(raw_index))
            grid_offset_beats = raw_index - beat_index
            track = selected_by_id.get(track_id) or {"dj_notes": ""}
            preserve = (
                track_directives(track)["trust_cue_seconds"]
                or result.get("cue_source") == "dj_notes_landing"
            )
            if preserve and abs(grid_offset_beats) > 0.01:
                # Do not lie to the parity checker: a deliberately off-grid
                # cue has no exact beat index, so automatic integer nudges
                # must leave it alone.
                result.pop("cue_beat_index", None)
                result["cue_grid_offset_beats"] = round(grid_offset_beats, 3)
                # File-head openers (What Up Gangsta at 0.00s with
                # trust_cue_seconds) sit a few tens of ms before Mixxx's
                # first_beat. Playback stays at 0; planning still uses
                # beat 0 so guided format does not abort the whole set.
                if beat_index == 0:
                    cue_beat_index_cache[track_id] = 0
                return result
            snapped_seconds = first_beat + beat_index * period
            if abs(grid_offset_beats) > 0.01:
                result["cue_seconds_requested"] = round(float(cue_seconds), 4)
                result["cue_seconds"] = round(max(0.0, snapped_seconds), 4)
                source = str(result.get("cue_source") or "analyzed")
                if not source.endswith("+beat_snap"):
                    result["cue_source"] = f"{source}+beat_snap"
            result["cue_beat_index"] = beat_index
            result["cue_grid_offset_beats"] = round(grid_offset_beats, 3)
            cue_beat_index_cache[track_id] = beat_index
            return result
        if result.get("cue_beat_index") is not None:
            cue_beat_index_cache[track_id] = int(result["cue_beat_index"])
        return result

    def strict_intro_cue(track: dict) -> dict:
        """Verified beat-1 cue for the incoming side of the 8-bar format."""
        directive = track_directives(track)
        explicit = directive["intro_seconds"]
        phrase = phrase_lookup.get(track["track_id"]) or {}
        intro = phrase.get("intro") or {}
        if explicit is not None:
            cue_seconds = explicit
            beat_index = beat_index_for_seconds(
                track,
                cue_seconds,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            )
            source = "dj_format_human_intro"
        elif intro.get("cue_seconds") is not None:
            cue_seconds = float(intro["cue_seconds"])
            beat_index = (
                int(intro["beat_index"])
                if intro.get("beat_index") is not None
                else beat_index_for_seconds(
                    track,
                    cue_seconds,
                    phrase_lookup=phrase_lookup,
                    beat_phase_lookup=beat_phase_lookup,
                )
            )
            # Inference is accepted only when the lyric map leaves a full
            # eight-bar runway after the candidate intro downbeat.
            segments = lyric_segment_lookup.get(track["track_id"]) or []
            starts = [
                int(segment["beat_index"])
                for segment in segments
                if segment.get("beat_index") is not None
            ]
            if not starts or min(starts) - beat_index < dj_format.phrase_beats:
                raise ValueError(
                    f"{track['artist']} — {track['title']}: cannot prove an "
                    f"{dj_format.phrase_bars}-bar intro; add a verified "
                    "intro_seconds=<seconds> DJ note"
                )
            source = "dj_format_inferred_intro"
        else:
            raise ValueError(
                f"{track['artist']} — {track['title']}: strict DJ format "
                "needs an 8-bar intro; add intro_seconds=<seconds>"
            )
        if beat_index % dj_format.beats_per_bar:
            raise ValueError(
                f"{track['artist']} — {track['title']}: intro cue resolves "
                f"to beat index {beat_index}, not beat 1 of a bar"
            )
        return _remember_cue_beat_index(
            track["track_id"],
            {
                "cue_seconds": round(float(cue_seconds), 3),
                "cue_beat_index": beat_index,
                "cue_confidence": 1.0 if explicit is not None else intro.get("confidence"),
                "cue_source": source,
                "format_intro_verified": True,
                "format_intro_reason": (
                    "human-verified 8-bar intro"
                    if explicit is not None
                    else "beatgrid + timeline show at least 8 bars of intro runway"
                ),
                **(
                    {"dj_notes": track.get("dj_notes") or ""}
                    if explicit is not None
                    else {}
                ),
            },
        )

    def guided_intro_cue(track: dict) -> dict:
        """Best analyzed bar-downbeat cue, with honest evidence provenance."""
        directive = track_directives(track)
        if directive["intro_seconds"] is not None:
            # Human verification is sufficient for the guided format too,
            # but it remains subject to beatgrid/downbeat validation.
            return strict_intro_cue(track)
        if (
            directive["landing_seconds"] is not None
            and directive["landing_beats"] is not None
            and track.get("bpm")
        ):
            # verse_landing pre-roll: start early so the lyric hits when the
            # fader completes. Guided still requires bar 1, so snap back to
            # the previous downbeat rather than starting mid-bar / mid-word.
            raw_cue = max(
                0.0,
                directive["landing_seconds"]
                - directive["landing_beats"] * 60.0 / float(track["bpm"]),
            )
            grid = phrase_lookup.get(track["track_id"]) or beat_phase_lookup.get(
                track["track_id"]
            )
            if not grid or not grid.get("bpm") or grid.get("first_beat_seconds") is None:
                raise ValueError(
                    f"{track['artist']} — {track['title']}: guided verse "
                    "landing needs an analyzed beatgrid"
                )
            first = usable_first_beat_seconds(grid["first_beat_seconds"])
            raw_index = (raw_cue - first) / (60.0 / float(grid["bpm"]))
            beat_index = max(0, int(raw_index))
            beat_index -= beat_index % dj_format.beats_per_bar
            cue_seconds = seconds_for_beat(
                track,
                beat_index,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            )
            return _remember_cue_beat_index(
                track["track_id"],
                {
                    "cue_seconds": round(float(cue_seconds), 3),
                    "cue_beat_index": beat_index,
                    "landing_seconds": directive["landing_seconds"],
                    "landing_beats": directive["landing_beats"],
                    "cue_confidence": 1.0,
                    "cue_source": "guided_human_landing_downbeat",
                    "format_intro_verified": False,
                    "format_intro_reason": (
                        "verse landing snapped back to beat 1 of the bar; "
                        "not a verified 8-bar intro"
                    ),
                    "dj_notes": track.get("dj_notes") or "",
                },
            )
        if directive["cue_seconds"] is not None:
            cue_seconds = directive["cue_seconds"]
            beat_index = beat_index_for_seconds(
                track,
                cue_seconds,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            )
            if beat_index % dj_format.beats_per_bar:
                raise ValueError(
                    f"{track['artist']} — {track['title']}: cue_seconds "
                    f"resolves to beat index {beat_index}, not beat 1"
                )
            return _remember_cue_beat_index(
                track["track_id"],
                {
                    "cue_seconds": round(float(cue_seconds), 3),
                    "cue_beat_index": beat_index,
                    "cue_confidence": 1.0,
                    "cue_source": "guided_human_downbeat",
                    "format_intro_verified": False,
                    "format_intro_reason": (
                        "human cue is on beat 1 but is not annotated as a "
                        "verified 8-bar intro"
                    ),
                    "dj_notes": track.get("dj_notes") or "",
                },
            )

        phrase = phrase_lookup.get(track["track_id"]) or {}
        intro = phrase.get("intro") or {}
        if intro.get("cue_seconds") is not None:
            cue_seconds = float(intro["cue_seconds"])
            beat_index = (
                int(intro["beat_index"])
                if intro.get("beat_index") is not None
                else beat_index_for_seconds(
                    track,
                    cue_seconds,
                    phrase_lookup=phrase_lookup,
                    beat_phase_lookup=beat_phase_lookup,
                )
            )
            source = "guided_phrase_intro_downbeat"
            reason = (
                "analyzed intro-region downbeat; 8-bar intro structure is "
                "not human-verified"
            )
        elif phrase.get("cue_seconds") is not None:
            cue_seconds = float(phrase["cue_seconds"])
            beat_index = (
                int(phrase["beat_index"])
                if phrase.get("beat_index") is not None
                else beat_index_for_seconds(
                    track,
                    cue_seconds,
                    phrase_lookup=phrase_lookup,
                    beat_phase_lookup=beat_phase_lookup,
                )
            )
            source = "guided_analyzed_downbeat"
            reason = "analyzed bar downbeat; no verified 8-bar intro"
        else:
            phase = beat_phase_lookup.get(track["track_id"]) or {}
            if phase.get("first_beat_seconds") is None:
                raise ValueError(
                    f"{track['artist']} — {track['title']}: guided DJ format "
                    "still needs a beatgrid to guarantee beat 1; run Analyze "
                    "& enrich missing or remove this track"
                )
            cue_seconds = float(phase["first_beat_seconds"])
            beat_index = 0
            source = "guided_first_beat"
            reason = "first analyzed beat; no verified 8-bar intro"

        duration = track.get("duration_seconds") or phrase.get("duration")
        raw_cue = float(cue_seconds)
        cue_seconds = seekable_cue_seconds(raw_cue, duration)
        if cue_seconds == 0.0 and abs(raw_cue) > 1e-6:
            beat_index = 0
            source = f"{source}+sanitized"

        if beat_index % dj_format.beats_per_bar:
            # Move forward to the next bar downbeat rather than accepting an
            # arbitrary beat. The beatgrid remains the authority.
            beat_index += dj_format.beats_per_bar - (
                beat_index % dj_format.beats_per_bar
            )
            cue_seconds = seconds_for_beat(
                track,
                beat_index,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            )
        return _remember_cue_beat_index(
            track["track_id"],
            {
                "cue_seconds": round(float(cue_seconds), 3),
                "cue_beat_index": beat_index,
                "cue_confidence": intro.get("confidence"),
                "cue_source": source,
                "format_intro_verified": False,
                "format_intro_reason": reason,
            },
        )

    def cue_fields(track: dict, fallback_fraction: float, slot: int = 0) -> dict:
        if dj_format.planner == "hiphop_rnb_8bar":
            return (
                strict_intro_cue(track)
                if slot > 0
                else guided_intro_cue(track)
            )
        if dj_format.planner == "hiphop_rnb_guided" and slot > 0:
            return guided_intro_cue(track)
        directive = track_directives(track)
        if (
            directive["pickup_beats"]
            and track.get("bpm")
        ):
            pickup = max(1, int(directive["pickup_beats"]))
            period = 60.0 / float(track["bpm"])
            landing = pickup * period
            return _remember_cue_beat_index(track["track_id"], {
                "cue_seconds": 0.0,
                "landing_seconds": round(landing, 3),
                "landing_beats": pickup,
                "pickup_beats": pickup,
                "cue_confidence": 1.0,
                "cue_source": "dj_notes_pickup",
                "dj_notes": track.get("dj_notes") or "",
            })
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
                return _remember_cue_beat_index(track["track_id"], {
                    "cue_seconds": round(snapped if did_snap else raw, 3),
                    "cue_source": (
                        "fraction_fallback+lyric_snap"
                        if did_snap
                        else "fraction_fallback"
                    ),
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
        duration = track.get("duration_seconds") or phrase.get("duration")
        raw_cue = float(pick["cue_seconds"])
        cue_seconds = seekable_cue_seconds(raw_cue, duration)
        sanitized = cue_seconds == 0.0 and abs(raw_cue) > 1e-6
        if sanitized:
            source = f"{source}+sanitized"
        cue_seconds, did_snap = snap_to_lyric_line(
            cue_seconds, track["track_id"], lyric_line_lookup
        )
        if did_snap:
            source = f"{source}+lyric_snap"
        # phrase_body + lyric-line snap still lands mid-verse (~40s). If
        # lyrics prove that, start from 0:00 (iconic intro) or pre-roll
        # onto the verse. Human cue_seconds already returned above.
        segments = lyric_segment_lookup.get(track["track_id"]) or []
        if segments:
            grid = phrase or beat_phase_lookup.get(track["track_id"]) or {}
            first_beat = 0.0
            if grid.get("first_beat_seconds") is not None:
                first_beat = float(usable_first_beat_seconds(grid["first_beat_seconds"]))
            decision = respect_verse_entry(
                cue_seconds,
                segments,
                first_beat=first_beat,
                bpm=track.get("bpm"),
                title=str(track.get("title") or ""),
                path=str(track.get("track_id") or ""),
            )
            if not decision.legal:
                cue_seconds = decision.cue_seconds
                source = f"{source}+verse_guard_{decision.source}"
        return _remember_cue_beat_index(track["track_id"], {
            "cue_seconds": cue_seconds,
            "cue_beat_index": 0 if sanitized else pick.get("beat_index"),
            "cue_confidence": 0.0 if sanitized else pick.get("confidence"),
            "cue_source": source,
        })

    def format_min_ride_beats(ride_phrases: int) -> int:
        """Beats a DJ-format ride must cover before an exit may be chosen.

        The format decides *where* a transition may land (a verified bar
        downbeat); the mix profile still decides *how long* a song plays.
        Selecting a format used to silently override the profile, because
        the exit anchors search from the current beat and therefore always
        returned the next phrase boundary — often only a few beats away.
        """
        return max(0, ride_phrases - 1) * dj_format.phrase_beats

    def strict_exit_anchor(
        track: dict,
        *,
        directive: dict,
        recipe: str,
        after_beat: int,
    ) -> tuple[int, float, str]:
        """Find the verified beat-1 hook/chorus where a format transition starts."""
        if recipe == "acapella_hook_swap":
            seconds = directive["hook_acapella_seconds"]
            if seconds is None:
                raise ValueError(
                    f"{track['artist']} — {track['title']}: "
                    "acapella_hook_swap requires a human-verified "
                    "hook_acapella_seconds=<seconds> DJ note"
                )
            beat_index = beat_index_for_seconds(
                track,
                seconds,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            )
            source = "dj_notes_hook_acapella"
        elif directive["chorus_seconds"] is not None:
            seconds = directive["chorus_seconds"]
            beat_index = beat_index_for_seconds(
                track,
                seconds,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            )
            source = "dj_notes_chorus"
        else:
            candidates: list[tuple[int, float]] = []
            timeline = lyric_segment_lookup.get(track["track_id"]) or []
            for segment_index, segment in enumerate(timeline):
                if segment.get("kind") != "chorus" or segment.get("beat_index") is None:
                    continue
                start_beat = int(segment["beat_index"])
                if start_beat <= after_beat:
                    continue
                next_segment = (
                    timeline[segment_index + 1]
                    if segment_index + 1 < len(timeline)
                    else None
                )
                if next_segment and next_segment.get("beat_index") is not None:
                    end_beat = int(next_segment["beat_index"])
                else:
                    end_seconds = segment.get("end")
                    if end_seconds is None:
                        continue
                    # The last lyric timestamp is not guaranteed to be on a
                    # beat. Round it only for phrase-length evidence; the
                    # START anchor remains subject to strict beat validation.
                    grid = phrase_lookup.get(track["track_id"]) or (
                        beat_phase_lookup.get(track["track_id"]) or {}
                    )
                    if not grid.get("bpm") or grid.get("first_beat_seconds") is None:
                        continue
                    end_beat = round(
                        (float(end_seconds) - float(grid["first_beat_seconds"]))
                        / (60.0 / float(grid["bpm"]))
                    )
                if end_beat - start_beat < dj_format.phrase_beats:
                    continue
                start_seconds = (
                    float(segment["bar_start"])
                    if segment.get("bar_start") is not None
                    else seconds_for_beat(
                        track,
                        start_beat,
                        phrase_lookup=phrase_lookup,
                        beat_phase_lookup=beat_phase_lookup,
                    )
                )
                candidates.append((start_beat, start_seconds))
            if not candidates:
                raise ValueError(
                    f"{track['artist']} — {track['title']}: cannot prove an "
                    f"{dj_format.phrase_bars}-bar chorus after the current "
                    "play position; add a verified chorus_seconds=<seconds> "
                    "DJ note"
                )
            beat_index, seconds = min(candidates)
            source = "lyric_timeline_chorus"

        if beat_index <= after_beat:
            raise ValueError(
                f"{track['artist']} — {track['title']}: format exit at beat "
                f"{beat_index} is not after the current beat {after_beat}"
            )
        if beat_index % dj_format.beats_per_bar:
            raise ValueError(
                f"{track['artist']} — {track['title']}: format exit resolves "
                f"to beat index {beat_index}, not beat 1 of a bar"
            )
        return beat_index, round(float(seconds), 3), source

    def strict_intro_loop_point(track: dict, directive: dict) -> tuple[int, float, str]:
        explicit = directive["intro_loop_seconds"]
        phrase = phrase_lookup.get(track["track_id"]) or {}
        intro = phrase.get("intro") or {}
        if explicit is not None:
            seconds = explicit
            beat_index = beat_index_for_seconds(
                track,
                seconds,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            )
            source = "dj_notes_intro_loop"
        elif intro.get("cue_seconds") is not None:
            seconds = float(intro["cue_seconds"])
            beat_index = (
                int(intro["beat_index"])
                if intro.get("beat_index") is not None
                else beat_index_for_seconds(
                    track,
                    seconds,
                    phrase_lookup=phrase_lookup,
                    beat_phase_lookup=beat_phase_lookup,
                )
            )
            source = "phrase_intro_loop"
        else:
            raise ValueError(
                f"{track['artist']} — {track['title']}: "
                "intro_loop_under_entry requires intro_loop_seconds=<seconds>"
            )
        if beat_index % dj_format.beats_per_bar:
            raise ValueError(
                f"{track['artist']} — {track['title']}: intro loop resolves "
                f"to beat index {beat_index}, not beat 1 of a bar"
            )
        return beat_index, round(float(seconds), 3), source

    def guided_exit_anchor(
        track: dict,
        *,
        directive: dict,
        recipe: str,
        after_beat: int,
    ) -> tuple[int, float, str, bool, str | None]:
        """Prefer a strict exit, then fall back without hiding why."""
        try:
            beat_index, seconds, source = strict_exit_anchor(
                track,
                directive=directive,
                recipe=recipe,
                after_beat=after_beat,
            )
            return beat_index, seconds, source, True, None
        except ValueError as strict_error:
            reason = str(strict_error)

        # A shorter/unverified detected chorus is still a musically useful
        # downbeat in guided mode; it just cannot carry the expert-certified
        # 8-bar claim.
        chorus_candidates = [
            (
                int(segment["beat_index"]),
                (
                    float(segment["bar_start"])
                    if segment.get("bar_start") is not None
                    else seconds_for_beat(
                        track,
                        int(segment["beat_index"]),
                        phrase_lookup=phrase_lookup,
                        beat_phase_lookup=beat_phase_lookup,
                    )
                ),
            )
            for segment in (lyric_segment_lookup.get(track["track_id"]) or [])
            if (
                segment.get("kind") == "chorus"
                and segment.get("beat_index") is not None
                and int(segment["beat_index"]) > after_beat
                and int(segment["beat_index"]) % dj_format.beats_per_bar == 0
            )
        ]
        if chorus_candidates:
            beat_index, seconds = min(chorus_candidates)
            return (
                beat_index,
                round(seconds, 3),
                "guided_detected_chorus_downbeat",
                False,
                reason,
            )

        target = (
            (after_beat // dj_format.phrase_beats) + 1
        ) * dj_format.phrase_beats
        return (
            target,
            seconds_for_beat(
                track,
                target,
                phrase_lookup=phrase_lookup,
                beat_phase_lookup=beat_phase_lookup,
            ),
            "guided_next_32_beat_boundary",
            False,
            reason,
        )

    # Instrument reset
    first_cue = cue_fields(selected[0], 0.08, 0)
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
            **first_cue,
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
                **first_cue,
                **(
                    {"juggle_chops": opener_directive["juggle_chops"]}
                    if opener_directive["juggle_chops"] is not None
                    else {}
                ),
                **(
                    {"juggle_hold_beats": opener_directive["juggle_hold_beats"]}
                    if opener_directive["juggle_hold_beats"] is not None
                    else {}
                ),
                "detail": (
                    "Beat-juggle repeated cue drops between two copies, then land clean."
                    if opener_directive["opener_style"] == "juggle_intro"
                    else "Tease the iconic opening, rewind, then drop clean."
                ),
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
    # Hard-cut budget for the whole mix; see the enforcement block below.
    hard_cuts_used = 0
    previous_was_hard_cut = False
    skip_outgoing_body = False
    bed_live_label = None
    bed_live_track = None

    for index in range(len(selected) - 1):
        outgoing = selected[index]
        incoming = selected[index + 1]
        out_deck = live_deck
        in_deck = 2 if live_deck == 1 else 1
        if skip_outgoing_body:
            # Previous incoming was a vocals-only layer. The instrumental bed
            # is still the live deck; this outgoing acapella must not play dry.
            bed = bed_live_track or outgoing
            incoming_directive = track_directives(incoming)
            if incoming_directive["entry_style"] == "vocal_over_bed":
                # Another dry vocal on the same still-playing bed.
                aff = affinity_lookup.get(
                    tuple(sorted((bed["track_id"], incoming["track_id"])))
                )
                tech = pick_technique(
                    bed, incoming, aff, avoid_silence=profile.avoid_silence
                )
                layer_beats = (
                    incoming_directive["ride_beats"]
                    or incoming_directive["landing_beats"]
                    or 96
                )
                tech.update(
                    technique="vocal_over_bed",
                    transition_beats=max(16, int(layer_beats)),
                    moves=["sync", "vocal_over_bed"],
                    showcase_move="vocal_over_bed",
                    keep_outgoing_live=True,
                    bed_track_id=bed["track_id"],
                    vocal_track_id=incoming["track_id"],
                    notes=(
                        "Human DJ note: keep the outgoing instrumental bed playing. "
                        "Start the vocals-only track on the other deck, beat-matched, "
                        "crossfader center. Do not ride the acapella dry. After the "
                        "layer, fade the vocal out and keep the bed."
                    ),
                )
                loop_beats = incoming_directive.get("bed_loop_beats")
                if loop_beats:
                    tech["bed_loop_beats"] = int(loop_beats)
                    tech["moves"] = ["sync", "vocal_over_bed", "bed_loop"]
                if incoming_directive["play_bpm"] is not None:
                    tech["incoming_bpm_target"] = incoming_directive["play_bpm"]
                events.append(
                    {
                        "op": "load",
                        "deck": in_deck,
                        "track_id": incoming["track_id"],
                        "artist": incoming["artist"],
                        "title": incoming["title"],
                        **cue_fields(incoming, 0.12, index + 1),
                    }
                )
                events.append(
                    {
                        "op": "transition",
                        "from_deck": out_deck,
                        "to_deck": in_deck,
                        "from_track": bed_live_label
                        or f"{bed['artist']} — {bed['title']}",
                        "to_track": f"{incoming['artist']} — {incoming['title']}",
                        **tech,
                    }
                )
                segments.append(
                    {
                        "index": index,
                        "from": bed_live_label or f"{bed['artist']} — {bed['title']}",
                        "to": f"{incoming['artist']} — {incoming['title']}",
                        "technique": tech["technique"],
                        "beats": tech["transition_beats"],
                        "score": tech["score"],
                        "showcase_move": tech["showcase_move"],
                    }
                )
                skip_outgoing_body = True
                previous_fade_beats = 0
                continue
            skip_outgoing_body = False
            aff = affinity_lookup.get(tuple(sorted((bed["track_id"], incoming["track_id"]))))
            tech = pick_technique(bed, incoming, aff, avoid_silence=profile.avoid_silence)
            tech.setdefault("showcase_move", "bass_swap")
            if incoming_directive["play_bpm"] is not None:
                tech["incoming_bpm_target"] = incoming_directive["play_bpm"]
            override_beats = transition_beats_by_pair.get(
                (bed["track_id"], incoming["track_id"])
            )
            if override_beats is not None:
                tech["transition_beats"] = max(1, int(override_beats))
            # Vocal deck is free after the layer. Load the next full song
            # there before handing off from the still-playing bed.
            events.append(
                {
                    "op": "load",
                    "deck": in_deck,
                    "track_id": incoming["track_id"],
                    "artist": incoming["artist"],
                    "title": incoming["title"],
                    **cue_fields(incoming, 0.12, index + 1),
                }
            )
            if index + 2 < len(selected):
                nxt = selected[index + 2]
                events.append(
                    {
                        "op": "preload_after_transition",
                        "deck": out_deck,
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
                    "from_track": bed_live_label or f"{bed['artist']} — {bed['title']}",
                    "to_track": f"{incoming['artist']} — {incoming['title']}",
                    **tech,
                    "notes": (
                        (tech.get("notes") or "")
                        + " Bed stays live after the vocal layer; this handoff leaves the acapella."
                    ).strip(),
                }
            )
            segments.append(
                {
                    "index": index,
                    "from": bed_live_label or f"{bed['artist']} — {bed['title']}",
                    "to": f"{incoming['artist']} — {incoming['title']}",
                    "technique": tech["technique"],
                    "beats": tech["transition_beats"],
                    "score": tech["score"],
                    "showcase_move": tech["showcase_move"],
                }
            )
            bed_live_label = None
            bed_live_track = None
            live_deck = in_deck
            previous_fade_beats = tech["transition_beats"]
            continue
        aff = affinity_lookup.get(tuple(sorted((outgoing["track_id"], incoming["track_id"]))))
        tech = pick_technique(outgoing, incoming, aff, avoid_silence=profile.avoid_silence)
        incoming_directive = track_directives(incoming)

        # "Use sparingly" has to be enforced, not just written in the recipe's
        # own notes (Ernest, 2026-08-03, after hearing two brake-and-drop cuts
        # land back to back -- "it's almost lazy. Use sparingly really means
        # use sparingly"). A hard cut stops the music dead; one per mix can be
        # a deliberate statement, two is a habit, and two in a row reads as the
        # planner giving up on beatmatching. Profiles with avoid_silence=True
        # never reach this because pick_technique won't propose the recipe at
        # all -- this is the backstop for every other profile.
        if tech["technique"] == "half_time_or_cut":
            reason = (
                "back-to-back hard cut" if previous_was_hard_cut
                else ("mix already spent its one hard cut" if hard_cuts_used else "")
            )
            if reason:
                tech.update(
                    technique="tempo_gap_blend",
                    # Same downgrade shape the smooth-opening path already
                    # uses; "sync" stays out for the reason documented on the
                    # other tempo_gap_blend definition.
                    moves=[
                        "rate_nudge_in", "filter_sweep_out",
                        "crossfade", "filter_reset", "eq_restore",
                    ],
                    notes=(
                        "Extreme tempo gap, but a hard cut was declined here "
                        f"({reason}) — rate-nudge into a longer EQ/filter "
                        "blend instead. At most one hard cut per mix, never "
                        "two in a row."
                    ),
                )
                print(
                    f"  [hard-cut budget] {outgoing['artist']} — {outgoing['title']} -> "
                    f"{incoming['artist']} — {incoming['title']}: downgraded "
                    f"half_time_or_cut to tempo_gap_blend ({reason})"
                )
            else:
                hard_cuts_used += 1
        previous_was_hard_cut = tech["technique"] == "half_time_or_cut"

        # Compatibility chooses the base recipe; the profile controls how
        # often we show off and how long the landing takes.
        if profile.transition_scale != 1.0:
            scaled = tech["transition_beats"] * profile.transition_scale
            tech["transition_beats"] = max(4, int(round(scaled / 4)) * 4)
        flourish = "bass_swap"
        if profile.flourish_every and index % profile.flourish_every == 0 and not incoming_directive["no_flourish"]:
            # Rotation includes the Rust slip gestures (stutter/censor);
            # the runner degrades them to plain blends when the clawdj
            # binary is missing, so plans stay portable.
            rotation = (
                "bass_swap",
                "stutter_fill",
                "loop_roll",
                "censor_fill",
                "transformer_cut",
            )
            flourish = rotation[(index // profile.flourish_every) % len(rotation)]
        if flourish == "loop_roll":
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
                    "optional_loop_roll_out",
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
                    "Human DJ note: use a gentle blend with both decks at one "
                    "true synced tempo; do not hold a midpoint bridge BPM."
                ),
            )
        elif incoming_directive["entry_style"] == "halftime_blend":
            tech.update(
                technique="halftime_backbeat_blend",
                transition_beats=max(24, tech["transition_beats"]),
                moves=["sync", "eq_dip_out_mid", "crossfade", "eq_restore"],
                showcase_move="halftime_backbeat_blend",
                notes=(
                    "Human DJ note: both tracks expose a fast subdivision "
                    "grid, but the groove reads in half-time. Their pinned "
                    "cues/exit align the prominent snare backbeats before "
                    "Mixxx phase-syncs the otherwise near-identical tempos."
                ),
            )
        elif incoming_directive["entry_style"] == "vocal_over_bed":
            layer_beats = incoming_directive["ride_beats"] or incoming_directive["landing_beats"] or 96
            tech.update(
                technique="vocal_over_bed",
                transition_beats=max(16, int(layer_beats)),
                moves=["sync", "vocal_over_bed"],
                showcase_move="vocal_over_bed",
                keep_outgoing_live=True,
                bed_track_id=outgoing["track_id"],
                vocal_track_id=incoming["track_id"],
                notes=(
                    "Human DJ note: keep the outgoing instrumental bed playing. "
                    "Start the vocals-only track on the other deck, beat-matched, "
                    "crossfader center. Do not ride the acapella dry. After the "
                    "layer, fade the vocal out and keep the bed."
                ),
            )
            loop_beats = incoming_directive.get("bed_loop_beats")
            if loop_beats:
                tech["bed_loop_beats"] = int(loop_beats)
                tech["moves"] = ["sync", "vocal_over_bed", "bed_loop"]
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
        elif incoming_directive["pickup_beats"] and incoming.get("bpm"):
            pickup = max(1, int(incoming_directive["pickup_beats"]))
            landing = pickup * 60.0 / float(incoming["bpm"])
            tech.update(
                technique="pickup_on_one_blend",
                transition_beats=max(int(tech["transition_beats"]), pickup),
                landing_seconds=round(landing, 3),
                landing_tolerance_seconds=1.0,
                moves=[
                    "sync", "eq_dip_out_mid", "crossfade", "eq_restore",
                ],
                showcase_move="pickup_on_one",
                notes=(
                    "Remix Report: start the incoming pickup early so the "
                    f"real downbeat (beat {pickup}) lands on 1. Wrong: treat "
                    "the brake/vocal pickup as beat 1."
                ),
            )
        if incoming_directive["play_bpm"] is not None:
            tech["incoming_bpm_target"] = incoming_directive["play_bpm"]
        elif incoming_directive["keep_blend_tempo"]:
            tech["keep_blend_tempo"] = True
        if incoming_directive["settle_bpm"] is not None and incoming.get("bpm"):
            # Enter matched to the outgoing deck (ordinary sync, so the
            # overlap stays drift-free), then glide to this tempo instead of
            # all the way home. Meaningless alongside a play_bpm hold, which
            # skips the settle entirely -- play_bpm wins and this is dropped.
            if tech.get("incoming_bpm_target") is None and not tech.get("keep_blend_tempo"):
                tech["incoming_settle_bpm"] = incoming_directive["settle_bpm"]
                tech["incoming_native_bpm"] = float(incoming["bpm"])

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
        elif directive["exit_style"] == "tempo_ramp_blend":
            exit_bpm = directive["exit_bpm"] or incoming.get("bpm")
            tech.update(
                technique="tempo_ramp_blend",
                transition_beats=16,
                moves=[
                    "sync", "eq_dip_out_mid", "filter_sweep_out",
                    "crossfade", "filter_reset", "eq_restore",
                ],
                showcase_move="tempo_ramp_blend",
                notes=(
                    "Human DJ note: gradually raise the outgoing track to "
                    f"{exit_bpm:.2f} BPM before the phrase boundary, then "
                    "phase-sync the incoming track at its native tempo for "
                    "a normal EQ/filter blend."
                ),
            )
        elif directive["exit_style"] == "filter_drop":
            tech.update(
                technique="filter_drop_exit",
                transition_beats=4,
                moves=["filter_drop_exit"],
                showcase_move="filter_drop",
                notes=(
                    "Human DJ note: remove the outgoing percussion with a "
                    "short low-pass sweep, then drop the incoming track clean "
                    "on the phrase boundary at its native tempo."
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
            # 1024: a 168 BPM double-time grid (Wanna Get To Know) needs ~640
            # beats to cover 4 minutes. 512 cut 50's verse off.
            ride_beats = max(0, min(1024, directive["ride_beats"]))

        # Remix Report: start an 8-bar intro on the downbeat of an 8-bar
        # chorus. 10-bar: wait 2 bars, then intro. 6-bar: skip 2 bars of
        # the incoming intro. Only the 4–12 bar "tricky" range; 24/40-bar
        # hits mix out at 8 (ep.096).
        chorus_bars = directive.get("chorus_bars")
        if chorus_bars and 4 <= int(chorus_bars) <= 12:
            wait_bars = max(0, int(chorus_bars) - 8)
            skip_intro_bars = max(0, 8 - int(chorus_bars))
            if wait_bars:
                ride_beats += wait_bars * 4
                tech["outgoing_chorus_bars"] = int(chorus_bars)
                extra = (
                    f" Remix Report: {chorus_bars}-bar chorus — wait "
                    f"{wait_bars} bars, then start the 8-bar intro."
                )
                tech["notes"] = (tech.get("notes") or "") + extra
            if skip_intro_bars and incoming.get("bpm"):
                extra_s = skip_intro_bars * 4 * 60.0 / float(incoming["bpm"])
                for ev in reversed(events):
                    if (
                        ev.get("op") in {"load", "preload_after_transition"}
                        and ev.get("track_id") == incoming["track_id"]
                    ):
                        ev["cue_seconds"] = round(
                            float(ev.get("cue_seconds") or 0.0) + extra_s, 4
                        )
                        ev["chorus_intro_skip_bars"] = skip_intro_bars
                        src = str(ev.get("cue_source") or "analyzed")
                        if not src.endswith("+chorus_intro_skip"):
                            ev["cue_source"] = f"{src}+chorus_intro_skip"
                        break
                tech["outgoing_chorus_bars"] = int(chorus_bars)
                extra = (
                    f" Remix Report: {chorus_bars}-bar chorus — skip "
                    f"{skip_intro_bars} bars of the incoming 8-bar intro."
                )
                tech["notes"] = (tech.get("notes") or "") + extra

        if dj_format.planner == "hiphop_rnb_8bar":
            recipe = (
                directive["format_recipe"]
                or (
                    "acapella_hook_swap"
                    if directive["hook_acapella_seconds"] is not None
                    else dj_format.default_recipe
                )
            )
            if recipe not in dj_format.recipes:
                raise ValueError(
                    f"{outgoing['artist']} — {outgoing['title']}: unsupported "
                    f"format_recipe={recipe!s}; choose from "
                    f"{', '.join(dj_format.recipes)}"
                )
            outgoing_entry_beat = cue_beat_index_cache.get(outgoing["track_id"])
            if outgoing_entry_beat is None:
                raise ValueError(
                    f"{outgoing['artist']} — {outgoing['title']}: could not "
                    "resolve its current cue onto the beatgrid"
                )
            current_beat = outgoing_entry_beat + elapsed_in_phrase
            # Give the song the profile's ride length BEFORE looking for an
            # exit, mirroring the default path's `next_boundary +=
            # (ride_phrases - 1) * phrase_beats`. Without this the anchor
            # returns the very next phrase boundary, so a cue landing late in
            # a phrase rides only a handful of beats and mix-to-listen's 2-4
            # phrases are silently discarded on every format transition.
            exit_search_from = current_beat + format_min_ride_beats(ride_phrases)
            exit_beat, exit_seconds, exit_source = strict_exit_anchor(
                outgoing,
                directive=directive,
                recipe=recipe,
                after_beat=exit_search_from,
            )
            # play_body waits N beat ticks and perform_transition anchors on
            # the next one, hence the -1. Both the exit and every incoming
            # cue are separately validated as bar downbeats.
            ride_beats = exit_beat - current_beat - 1
            format_moves = ["sync", "crossfade"]
            tech.update(
                technique=f"dj_format_{recipe}",
                transition_beats=dj_format.phrase_beats,
                moves=format_moves,
                showcase_move=recipe,
                notes=(
                    f"Strict {dj_format.label}: Song A exits at "
                    f"{exit_source} beat 1; Song B enters on beat 1 of its "
                    f"{dj_format.phrase_bars}-bar intro."
                ),
                dj_format=dj_format.name,
                format_recipe=recipe,
                format_exit_beat_index=exit_beat,
                format_exit_seconds=exit_seconds,
                format_exit_source=exit_source,
                format_entry_beat_index=cue_beat_index_cache.get(
                    incoming["track_id"]
                ),
                format_entry_source="8_bar_intro",
                format_phrase_bars=dj_format.phrase_bars,
                format_compliance="expert_recipe",
                format_reason="strict 8-bar intro + chorus/hook evidence",
            )
            if recipe == "intro_loop_under_entry":
                loop_beat, loop_seconds, loop_source = strict_intro_loop_point(
                    outgoing, directive
                )
                tech["moves"] = [
                    "outgoing_intro_loop_8_bars",
                    "sync",
                    "crossfade",
                ]
                tech.update(
                    outgoing_loop_beat_index=loop_beat,
                    outgoing_loop_seconds=loop_seconds,
                    outgoing_loop_source=loop_source,
                    outgoing_loop_beats=dj_format.phrase_beats,
                )
        elif dj_format.planner == "hiphop_rnb_guided":
            recipe = (
                directive["format_recipe"]
                or (
                    "acapella_hook_swap"
                    if directive["hook_acapella_seconds"] is not None
                    else dj_format.default_recipe
                )
            )
            if recipe not in dj_format.recipes:
                raise ValueError(
                    f"{outgoing['artist']} — {outgoing['title']}: unsupported "
                    f"format_recipe={recipe!s}; choose from "
                    f"{', '.join(dj_format.recipes)}"
                )
            outgoing_entry_beat = cue_beat_index_cache.get(outgoing["track_id"])
            incoming_entry_beat = cue_beat_index_cache.get(incoming["track_id"])
            grid_fallback_reason = None
            if outgoing_entry_beat is None or incoming_entry_beat is None:
                # Guided, not strict: one off-grid opener (trust_cue_seconds
                # at file head) must not fail a 148-track mix. Label fallback.
                grid_fallback_reason = (
                    f"{outgoing['artist']} — {outgoing['title']} → "
                    f"{incoming['artist']} — {incoming['title']}: "
                    "cues not both on analyzed beatgrids; "
                    "phrase-aligned fallback"
                )
                outgoing_entry_beat = (
                    0 if outgoing_entry_beat is None else outgoing_entry_beat
                )
                incoming_entry_beat = (
                    0 if incoming_entry_beat is None else incoming_entry_beat
                )
            if incoming_entry_beat % dj_format.beats_per_bar:
                incoming_entry_beat += dj_format.beats_per_bar - (
                    incoming_entry_beat % dj_format.beats_per_bar
                )
            current_beat = outgoing_entry_beat + elapsed_in_phrase
            # See the strict path above: search for the exit only after the
            # profile's ride length has actually been played.
            exit_search_from = current_beat + format_min_ride_beats(ride_phrases)
            (
                exit_beat,
                exit_seconds,
                exit_source,
                strict_exit,
                fallback_reason,
            ) = guided_exit_anchor(
                outgoing,
                directive=directive,
                recipe=recipe,
                after_beat=exit_search_from,
            )
            ride_beats = exit_beat - current_beat - 1
            entry_evidence = format_cue_evidence_cache.get(
                incoming["track_id"]
            ) or {}
            intro_verified = bool(entry_evidence.get("verified"))
            expert_recipe = (
                strict_exit and intro_verified and not grid_fallback_reason
            )
            loop_fields: dict = {}
            if expert_recipe and recipe == "intro_loop_under_entry":
                try:
                    (
                        loop_beat,
                        loop_seconds,
                        loop_source,
                    ) = strict_intro_loop_point(outgoing, directive)
                    loop_fields = {
                        "outgoing_loop_beat_index": loop_beat,
                        "outgoing_loop_seconds": loop_seconds,
                        "outgoing_loop_source": loop_source,
                        "outgoing_loop_beats": dj_format.phrase_beats,
                    }
                except ValueError as loop_error:
                    expert_recipe = False
                    fallback_reason = str(loop_error)

            if expert_recipe:
                moves = ["sync", "crossfade"]
                if recipe == "intro_loop_under_entry":
                    moves.insert(0, "outgoing_intro_loop_8_bars")
                tech.update(
                    technique=f"dj_format_{recipe}",
                    transition_beats=dj_format.phrase_beats,
                    moves=moves,
                    showcase_move=recipe,
                    notes=(
                        f"Guided format found complete strict evidence: "
                        f"Song A exits at {exit_source} beat 1; Song B "
                        f"enters on verified beat 1 of its "
                        f"{dj_format.phrase_bars}-bar intro."
                    ),
                    format_recipe=recipe,
                    format_compliance="expert_recipe",
                    format_reason=(
                        "verified 8-bar intro + chorus/hook evidence"
                    ),
                    **loop_fields,
                )
            else:
                reasons = [
                    part
                    for part in (
                        grid_fallback_reason,
                        fallback_reason,
                        (
                            entry_evidence.get("reason")
                            if not intro_verified
                            else None
                        ),
                    )
                    if part
                ]
                tech.update(
                    format_recipe="phrase_aligned_fallback",
                    format_requested_recipe=recipe,
                    format_compliance="guided_fallback",
                    format_reason="; ".join(reasons)
                    or "strict 8-bar evidence incomplete",
                )
                tech["notes"] += (
                    " Guided format: transition and incoming cue remain on "
                    "beat 1, but incomplete 8-bar evidence makes this an "
                    "explicit fallback rather than an expert-certified recipe."
                )
            tech.update(
                dj_format=dj_format.name,
                format_exit_beat_index=exit_beat,
                format_exit_seconds=exit_seconds,
                format_exit_source=exit_source,
                format_entry_beat_index=incoming_entry_beat,
                format_entry_source=entry_evidence.get("source"),
                format_phrase_bars=dj_format.phrase_bars,
            )

        # Format chooses WHERE a transition may land (bar 1). trust_ride_beats
        # is the human how-long lock and outranks the format's next-chorus
        # exit arithmetic. Same contract as format_min_ride_beats / DJ_STYLE_GUIDE.
        if directive["trust_ride_beats"] and directive["ride_beats"] is not None:
            ride_beats = max(0, min(1024, int(directive["ride_beats"])))

        # Human pair beat overrides must win before phase/anchor math and before
        # previous_fade_beats is advanced. Post-build patching of transition
        # events alone left phase_anchor assuming the default ~24-beat fade
        # while the runner executed the overridden 64-beat blend (audible
        # one-count lineage defects, 2026-08-04).
        override_beats = transition_beats_by_pair.get(
            (outgoing["track_id"], incoming["track_id"])
        )
        if override_beats is not None:
            tech["transition_beats"] = max(1, int(override_beats))

        # mix-to-listen: the whole outgoing blend must sit after the verse,
        # not start in a hook and then eat the next rap. Showcase profiles
        # may still cut for a transition trick.
        listen_mode = profile.name == "mix-to-listen" or profile.flourish_every == 0
        if (
            listen_mode
            and not directive["trust_ride_beats"]
            and outgoing.get("bpm")
        ):
            outgoing_cue = float(
                cue_fields(outgoing, 0.1, index).get("cue_seconds") or 0.0
            )
            ride_beats, verse_reason = respect_verse_exit(
                outgoing_cue,
                ride_beats,
                float(outgoing["bpm"]),
                lyric_segment_lookup.get(outgoing["track_id"]) or [],
                blend_beats=int(tech.get("transition_beats") or 32),
                title=str(outgoing.get("title") or ""),
                path=str(outgoing.get("track_id") or ""),
            )
            if verse_reason != "unchanged":
                print(
                    f"  [verse] {outgoing['artist']} — {outgoing['title']}: {verse_reason}"
                )

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
        #
        # Hard rule for every format: when both sides have usable snare-phase
        # reads, 2-and-4 must land together. Low-confidence snare reads are
        # NOT trusted (Tell Me / Risin instrumental style false parity); in
        # that case keep bar-count alignment only so cues still share 1-2-3-4.
        outgoing_phase = beat_phase_lookup.get(outgoing["track_id"])
        incoming_phase = beat_phase_lookup.get(incoming["track_id"])
        outgoing_entry_beat = cue_beat_index_cache.get(outgoing["track_id"])
        incoming_entry_beat = cue_beat_index_cache.get(incoming["track_id"])
        min_snare_confidence = 0.15
        if (
            legacy_parity and not directive["trust_ride_beats"]
            and outgoing_phase and incoming_phase
            and outgoing_entry_beat is not None and incoming_entry_beat is not None
        ):
            # The executor counts ``ride_beats`` edges, then the transition
            # waits for the NEXT edge. The audible anchor is therefore N+1.
            # Evaluating N here made corrections one count early.
            anchor = outgoing_entry_beat + previous_fade_beats + ride_beats + 1
            out_conf = float(outgoing_phase.get("confidence") or 0.0)
            in_conf = float(incoming_phase.get("confidence") or 0.0)
            if out_conf >= min_snare_confidence and in_conf >= min_snare_confidence:
                shift = count_shift_beats(
                    outgoing_snare_parity=outgoing_phase["snare_parity"],
                    outgoing_anchor_beat_index=anchor,
                    incoming_snare_parity=incoming_phase["snare_parity"],
                    incoming_cue_beat_index=incoming_entry_beat,
                )
                reason = "snare parity + bar count"
            else:
                bar_shift = (incoming_entry_beat - anchor) % 4
                shift = bar_shift if bar_shift <= 2 else bar_shift - 4
                reason = (
                    f"bar count only (weak snare conf "
                    f"{out_conf:.3f}/{in_conf:.3f})"
                )
            if shift:
                print(
                    f"  [beat-phase] {outgoing['artist']} — {outgoing['title']} -> "
                    f"{incoming['artist']} — {incoming['title']}: nudging ride_beats "
                    f"{ride_beats} -> {ride_beats + shift} to match {reason}"
                )
                ride_beats += shift

        # Compatibility for legacy direct callers only. New compositions use
        # measured cue-preserving entrances, not blind one-beat jumps.
        align_dir = int(incoming_directive.get("snare_align") or 0)
        if legacy_parity and align_dir and "sync" in (tech.get("moves") or []):
            move = "snare_align" if align_dir > 0 else "snare_align_back"
            moves = list(tech.get("moves") or [])
            if "snare_align" not in moves and "snare_align_back" not in moves:
                moves.insert(moves.index("sync") + 1, move)
                tech["moves"] = moves
                print(
                    f"  [beat-phase] {outgoing['artist']} — {outgoing['title']} -> "
                    f"{incoming['artist']} — {incoming['title']}: {move} after sync"
                )

        # Play body of outgoing track
        body_event = {
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
        if directive["trust_ride_beats"]:
            body_event["trust_ride_beats"] = True
        skip_from = directive.get("skip_from_seconds")
        skip_to = directive.get("skip_to_seconds")
        if (
            skip_from is not None
            and skip_to is not None
            and outgoing.get("bpm")
            and float(skip_to) > float(skip_from)
        ):
            period = 60.0 / float(outgoing["bpm"])
            cue_s = float(outgoing.get("cue_seconds") or 0.0)
            # play_body starts after the incoming blend, so those beats have
            # already elapsed on this deck. Counting skip_after from cue
            # fired the Diddy jump 32 beats late (into the verse).
            skip_after = max(0, round((float(skip_from) - cue_s) / period))
            skip_after = max(0, skip_after - int(previous_fade_beats or 0))
            skip_beats = max(4, round((float(skip_to) - float(skip_from)) / period))
            skip_beats -= skip_beats % 4
            if skip_beats > 0 and skip_after < int(body_event["beats"]):
                body_event["skip_after_beats"] = skip_after
                body_event["skip_beats"] = skip_beats
                body_event["skip_from_seconds"] = round(float(skip_from), 3)
                body_event["skip_to_seconds"] = round(float(skip_to), 3)
        # Loading the next track happens synchronously while this outgoing
        # track keeps playing. That variable delay means the live body
        # counter may begin on a different grid beat than cue arithmetic
        # assumed. Persist the intended absolute bar position so hands can
        # re-check the first beat they actually count and correct load
        # jitter without discarding the planned 1-2-3-4 relationship.
        #
        # trust_ride_beats still emits phase_anchor: the human lock blocks
        # planner auto-nudges of ride_beats, but the listener-approved count
        # defines a planned anchor that runtime must preserve when preload
        # timing shifts the first counted edge. Omitting the anchor (2026-08-04)
        # left approved 279/103/111 rides free to land one count off under
        # ordinary load delay.
        outgoing_grid = outgoing_phase or phrase_lookup.get(outgoing["track_id"])
        if (
            outgoing_entry_beat is not None
            and outgoing_grid
            and outgoing_grid.get("bpm")
            and outgoing_grid.get("first_beat_seconds") is not None
        ):
            planned_anchor_beat = (
                outgoing_entry_beat + previous_fade_beats + ride_beats + 1
            )
            body_event["phase_anchor"] = {
                "grid_bpm": float(outgoing_grid["bpm"]),
                "first_beat_seconds": usable_first_beat_seconds(
                    outgoing_grid["first_beat_seconds"]
                ),
                "planned_anchor_beat_index": planned_anchor_beat,
                "target_beat_mod4": planned_anchor_beat % 4,
                "target_beat_parity": planned_anchor_beat % 2,
            }
        if directive["exit_bpm"] is not None:
            body_event["exit_bpm_target"] = directive["exit_bpm"]
            body_event["tempo_ramp_beats"] = max(
                4,
                min(ride_beats, directive["tempo_ramp_beats"] or 16),
            )
            body_event["native_bpm"] = outgoing.get("bpm")
        events.append(body_event)

        # Prefetch next-next track onto the deck this transition will free.
        # vocal_over_bed keeps the bed live and still needs the vocal on the
        # incoming deck, so do not preload over it — the skip path loads the
        # following song after the layer.
        if index + 2 < len(selected) and not (
            tech.get("keep_outgoing_live") or tech.get("technique") == "vocal_over_bed"
        ):
            nxt = selected[index + 2]
            events.append(
                {
                    "op": "preload_after_transition",
                    "deck": out_deck,
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
                        "dj_format": tech["dj_format"],
                        "format_recipe": tech["format_recipe"],
                        "format_exit_seconds": tech["format_exit_seconds"],
                        "format_compliance": tech.get("format_compliance"),
                        "format_reason": tech.get("format_reason"),
                    }
                    if "dj_format" in tech
                    else {}
                ),
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
        if tech.get("keep_outgoing_live") or tech.get("technique") == "vocal_over_bed":
            skip_outgoing_body = True
            previous_fade_beats = 0
            bed_live_label = f"{outgoing['artist']} — {outgoing['title']}"
            bed_live_track = outgoing
        else:
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
        "dj_format": format_provenance(dj_format),
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
    dj_format_name: str = "none",
    mix_brief: str = "",
    order_engine: str = "none",
    tracks: int | None = None,
    seconds_per_track: float | None = None,
    phrase_analysis: Path = DEFAULT_PHRASES,
    phrase_beats: int | None = None,
    out: Path = DEFAULT_PLAN,
    ask=None,
    control_port: int | None = None,
    dj_notes_lookup: dict[str, str] | None = None,
    fixed_groups: list[list[str]] | None = None,
    transition_beats_by_pair: dict[tuple[str, str], int] | None = None,
    prepare_backbeat: bool = True,
) -> dict:
    """Build a mix plan from the finalized playlist and write it to disk.

    Same logic as the CLI entrypoint so the playlist editor and
    `python -m brain.build_mix_plan` stay in lockstep. `tracks=None` means
    "use every analyzed song in the playlist" (the editor and CLI default);
    short demos opt into a smaller set with ``--tracks``.

    `order_engine`: optional NemoClaw/H Company interpretation turns a brief
    into constraints. Deterministic local mix-quality ordering runs in every
    mode, including no model and an empty brief.
    """
    from brain.dj_formats import get_format
    from brain.mix_profiles import PROFILES, apply_brief, profile_provenance

    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile {profile_name!r}; choose from {sorted(PROFILES)}")
    dj_format = get_format(dj_format_name)
    if (
        dj_format.planner
        and phrase_beats is not None
        and phrase_beats != dj_format.phrase_beats
    ):
        raise ValueError(
            f"{dj_format.label} requires {dj_format.phrase_beats}-beat "
            f"phrases; --phrase-beats={phrase_beats} conflicts"
        )
    if not playlist.exists():
        raise FileNotFoundError(
            f"missing {playlist} — finalize a set first (playlist editor → Finalize for Mixxx)"
        )

    profile, brief_notes = apply_brief(PROFILES[profile_name], mix_brief)
    rows = json.loads(playlist.read_text())
    dj_notes = load_dj_notes_lookup() if dj_notes_lookup is None else dj_notes_lookup
    for row in rows:
        row["dj_notes"] = dj_notes.get(row.get("track_id"), row.get("dj_notes") or "")
    analyzed = [t for t in rows if t.get("bpm")]
    pool = analyzed if len(analyzed) >= 2 else rows
    if len(pool) < 2:
        raise ValueError("need at least 2 tracks with BPM in the finalized playlist")

    order_notes: list[str] = []
    order_constraints: dict | None = None
    from brain.mix_order_brief import order_from_brief

    try:
        pool, order_notes, order_constraints = order_from_brief(
            pool, mix_brief, engine=order_engine, ask=ask
        )
    except Exception as error:
        # Model interpretation is optional. Preserve the complete pool and
        # fall back to the exact same local optimizer used by Feel-only mode.
        pool, order_notes, order_constraints = order_from_brief(
            pool, "", engine="none"
        )
        order_notes.append(
            f"{order_engine} constraint interpretation failed; used local ordering: {error}"
        )

    if fixed_groups:
        # Bunch activation is a hard structural constraint, independent of
        # whether an LLM interpreted the optional natural-language brief.
        from brain.order_constraints import assert_intact

        ordered_ids = [row["track_id"] for row in pool]
        by_id = {row["track_id"]: row for row in pool}
        for group in fixed_groups:
            present = [track_id for track_id in group if track_id in by_id]
            if len(present) < 2:
                continue
            first = min(ordered_ids.index(track_id) for track_id in present)
            ordered_ids = [track_id for track_id in ordered_ids if track_id not in set(present)]
            ordered_ids[first:first] = present
        assert_intact(ordered_ids, fixed_groups)
        pool = [by_id[track_id] for track_id in ordered_ids]
        if tracks is not None:
            count_floor = min(tracks, len(pool))
            for group in fixed_groups:
                positions = [ordered_ids.index(track_id) for track_id in group if track_id in by_id]
                if positions and min(positions) < count_floor <= max(positions):
                    count_floor = max(positions) + 1
            tracks = count_floor
        order_notes.append(f"honored {len(fixed_groups)} active ordered bunch(es)")

    from brain.stems import apply_vocal_layers, assert_vocals_layered

    pool, layer_notes = apply_vocal_layers(pool)
    order_notes.extend(layer_notes)

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
        lyric_segment_lookup=fill_segment_lookup(pool, load_lyric_segment_lookup()),
        beat_phase_lookup=load_beat_phase_lookup(),
        phrase_beats=(
            dj_format.phrase_beats
            if dj_format.planner
            else (phrase_beats if phrase_beats is not None else profile.phrase_beats)
        ),
        profile=profile,
        dj_format=dj_format,
        provenance=provenance,
        transition_beats_by_pair=transition_beats_by_pair,
        legacy_parity=False,
    )
    if control_port is not None:
        plan.setdefault("runtime", {})["mixxx_control_port"] = int(control_port)
    assert_vocals_layered(plan, {row["track_id"]: row.get("dj_notes") or "" for row in pool})
    if prepare_backbeat:
        from brain.rhythm import prepare_plan
        prepare_plan(plan)
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_name(f".{out.name}.tmp")
    temporary.write_text(json.dumps(plan, indent=2) + "\n")
    temporary.replace(out)
    return plan


def plan_summary(plan: dict, *, plan_path: Path | None = None) -> dict:
    """Dry-run-style summary for the UI — no Mixxx connection required."""
    segments = plan.get("segments") or []
    events = plan.get("events") or []
    techniques: dict[str, int] = {}
    format_compliance: dict[str, int] = {}
    for seg in segments:
        name = seg.get("technique") or "unknown"
        techniques[name] = techniques.get(name, 0) + 1
        compliance = seg.get("format_compliance")
        if compliance:
            format_compliance[compliance] = (
                format_compliance.get(compliance, 0) + 1
            )
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
        "dj_format": plan.get("dj_format") or {"name": "none"},
        "order_engine": profile.get("order_engine"),
        "order_notes": profile.get("order_notes") or [],
        "techniques": techniques,
        "format_compliance": format_compliance,
        "backbeat": plan.get("backbeat"),
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
        "mixxx_control_port": (
            (plan.get("runtime") or {}).get("mixxx_control_port")
        ),
    }


def main() -> None:
    from brain.dj_formats import FORMATS
    from brain.mix_profiles import PROFILES

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan",
        dest="plan_slug",
        help="build the named workspace plan using only its PlanPaths artifacts",
    )
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--tracks", type=int, default=None, help="optional explicit subset size; default uses the complete pool")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="dj-showcase",
        help="how the set should feel; explicit flags below still win",
    )
    parser.add_argument(
        "--dj-format",
        choices=sorted(FORMATS),
        default="none",
        help="optional transition grammar, independent of the mix-feel profile",
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
             "via NemoClaw or H-agent (all choices use local mix-quality ordering)",
    )
    parser.add_argument("--seconds-per-track", type=float, default=None)
    parser.add_argument("--phrase-analysis", type=Path, default=DEFAULT_PHRASES)
    parser.add_argument("--phrase-beats", type=int, default=None, choices=(16, 32, 48, 64))
    parser.add_argument("--out", type=Path, default=DEFAULT_PLAN)
    parser.add_argument(
        "--control-api-port",
        type=int,
        default=(
            int(os.environ["CLAWDJ_MIXXX_CONTROL_PORT"])
            if os.environ.get("CLAWDJ_MIXXX_CONTROL_PORT")
            else None
        ),
        help="preserve the effective Mixxx control port in the plan for later live execution",
    )
    args = parser.parse_args()

    try:
        if args.plan_slug:
            from brain.plan_mix_build import build

            plan = build(
                args.plan_slug,
                profile=args.profile,
                dj_format=args.dj_format,
                mix_brief=args.mix_brief,
                order_engine=args.order_engine,
                tracks=args.tracks,
                seconds_per_track=args.seconds_per_track,
                phrase_analysis=args.phrase_analysis,
                phrase_beats=args.phrase_beats,
                control_port=args.control_api_port,
            )
        else:
            plan = compose_mix_plan(
                playlist=args.playlist,
                profile_name=args.profile,
                dj_format_name=args.dj_format,
                mix_brief=args.mix_brief,
                order_engine=args.order_engine,
                tracks=args.tracks,
                seconds_per_track=args.seconds_per_track,
                phrase_analysis=args.phrase_analysis,
                phrase_beats=args.phrase_beats,
                out=args.out,
                control_port=args.control_api_port,
            )
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"mix plan build stopped: {error}") from None
    profile = plan.get("profile") or {}
    dj_format = plan.get("dj_format") or {}
    print(f"profile: {profile.get('name')} — {(profile.get('values') or {}).get('description', '')}")
    print(
        f"DJ format: {dj_format.get('name')} — "
        f"{dj_format.get('description', '')}"
    )
    for note in profile.get("brief_adjustments") or []:
        print(f"  brief adjustment: {note}")
    for note in profile.get("order_notes") or []:
        print(f"  order: {note}")
    destination = (
        __import__("brain.plan_mix_build", fromlist=["mix_plan_path"]).mix_plan_path(args.plan_slug)
        if args.plan_slug else args.out
    )
    print(f"mix plan: {plan['track_count']} tracks -> {destination}")
    for seg in plan["segments"]:
        compliance = (
            f" [{seg['format_compliance']}]"
            if seg.get("format_compliance")
            else ""
        )
        print(
            f"  {seg['index']+1:02d}. [{seg['technique']:22}] {seg['beats']:2} beats  "
            f"{seg['from']} → {seg['to']}  (score {seg['score']})"
            f"{compliance}"
        )
    print("\nMixxx instrument controls used are listed in plan['instrument_map'].")
    print("Run: uv run python -m hands.run_mix_plan --dry-run")
    port_note = (plan.get("runtime") or {}).get("mixxx_control_port")
    print(
        "Live: uv run python -m hands.run_mix_plan"
        + (f"   # preserved Mixxx port {port_note}" if port_note else "")
    )


if __name__ == "__main__":
    main()
