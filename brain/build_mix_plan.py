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
from pathlib import Path

from brain.mix_graph import bpm_compatibility, key_compatibility

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_PLAYLIST = DATA_DIR / "playlist.json"
DEFAULT_AFFINITY = DATA_DIR / "mix_affinity.json"
DEFAULT_PHRASES = DATA_DIR / "phrase_analysis.json"
DEFAULT_PLAN = DATA_DIR / "mix_plan.json"


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


def pick_technique(left: dict, right: dict, affinity: dict | None) -> dict:
    """Choose how to play Mixxx between two tracks — instrument vocabulary.

    Default bias (Ernest, hackathon set): *blend* most of the time. Abrupt
    hard cuts are rare — reserved for extreme tempo gaps with no texture
    support (a "drop" moment), not the everyday path.
    """
    bpm_s, bpm_r = bpm_compatibility(left.get("bpm"), right.get("bpm"))
    key_s, key_r = key_compatibility(left.get("key"), right.get("key"))
    reasons = [r for r in (bpm_r, key_r) if r]
    lineage = bool(affinity and any("lineage" in r.lower() or "sample" in r.lower() for r in affinity.get("reasons", [])))
    lyric = float((affinity or {}).get("lyric_score") or 0)
    chroma = float((affinity or {}).get("chroma_score") or 0)
    score = float((affinity or {}).get("score") or (0.45 * bpm_s + 0.35 * key_s))

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
    elif bpm_s >= 0.9 and key_s < 0.5:
        # Was a short cut — now a filtered blend so the key clash is masked
        # without slamming the crossfader.
        technique = "key_clash_blend"
        beats = 16
        notes = "Tempo works; key is rough — longer filter-sweep blend to mask the clash (not a hard cut)."
        moves = ["sync", "filter_sweep_out", "crossfade", "filter_reset", "eq_restore"]
    elif bpm_s < 0.35 and not lineage and chroma < 0.55:
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
        moves = ["rate_nudge_in", "sync", "filter_sweep_out", "crossfade", "filter_reset", "eq_restore"]
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

    return {
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


def build_plan(
    tracks: list[dict],
    *,
    count: int,
    seconds_per_track: float,
    affinity_lookup: dict[tuple[str, str], dict],
    phrase_lookup: dict[str, dict] | None = None,
    phrase_beats: int = 32,
    profile: "MixProfile | None" = None,
    provenance: dict | None = None,
) -> dict:
    from brain.mix_profiles import PROFILES

    profile = profile or PROFILES["dj-showcase"]
    selected = tracks[:count]
    if len(selected) < 2:
        raise SystemExit("need at least 2 tracks in the filtered playlist")

    phrase_lookup = phrase_lookup or {}
    events: list[dict] = []

    def cue_fields(track: dict, fallback_fraction: float, slot: int = 0) -> dict:
        phrase = phrase_lookup.get(track["track_id"])
        if not phrase:
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
        return {
            "cue_seconds": pick["cue_seconds"],
            "cue_beat_index": pick.get("beat_index"),
            "cue_confidence": pick.get("confidence"),
            "cue_source": source,
        }
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
    events.append(
        {
            "op": "start",
            "deck": 1,
            "detail": "Play deck 1; deck 2 cued and silent until first transition",
        }
    )

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
        tech = pick_technique(outgoing, incoming, aff)

        # Compatibility chooses the base recipe; the profile controls how
        # often we show off and how long the landing takes.
        if profile.transition_scale != 1.0:
            scaled = tech["transition_beats"] * profile.transition_scale
            tech["transition_beats"] = max(4, int(round(scaled / 4)) * 4)
        tech["moves"] = [move for move in tech["moves"] if move != "optional_scratch_in"]
        flourish = "bass_swap"
        if profile.flourish_every and index % profile.flourish_every == 0:
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
        out_phrase = phrase_lookup.get(outgoing["track_id"]) or {}
        if ride_phrases == 1 and (out_phrase.get("confidence") or 0.0) >= profile.confidence_extra_phrase:
            ride_phrases = 2
        next_boundary += (ride_phrases - 1) * phrase_beats
        ride_beats = max(0, next_boundary - elapsed_in_phrase - 1)

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
            }
        )
        live_deck = in_deck
        previous_fade_beats = tech["transition_beats"]

    events.append(
        {
            "op": "finale",
            "deck": live_deck,
            "seconds": play_s,
            "beats": max(16, phrase_beats - previous_fade_beats),
            "track": f"{selected[-1]['artist']} — {selected[-1]['title']}",
            "detail": "Ride out the last track; optional loop_roll or EQ kill for ending",
        }
    )
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
        "echo_out": "EffectUnit1 on outgoing during last 4 beats of fade",
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
