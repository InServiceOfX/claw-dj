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
    """Choose how to play Mixxx between two tracks — instrument vocabulary."""
    bpm_s, bpm_r = bpm_compatibility(left.get("bpm"), right.get("bpm"))
    key_s, key_r = key_compatibility(left.get("key"), right.get("key"))
    reasons = [r for r in (bpm_r, key_r) if r]
    lineage = bool(affinity and any("lineage" in r.lower() or "sample" in r.lower() for r in affinity.get("reasons", [])))
    lyric = float((affinity or {}).get("lyric_score") or 0)
    chroma = float((affinity or {}).get("chroma_score") or 0)
    score = float((affinity or {}).get("score") or (0.45 * bpm_s + 0.35 * key_s))

    # Technique selection — map musical situation → Mixxx knobs/moves.
    if lineage or lyric > 0.2:
        technique = "sample_callback_blend"
        beats = 24
        notes = "Hold the shared sample/hook in the blend; EQ-swap lows so the sample bed stays continuous."
        moves = ["eq_kill_out_low", "eq_boost_in_mid", "sync", "long_crossfade", "filter_open_in"]
    elif bpm_s >= 0.9 and key_s >= 0.85:
        technique = "smooth_blend"
        beats = 16
        notes = "Near-identical tempo + friendly key — classic long crossfade with light EQ."
        moves = ["sync", "eq_dip_out_mid", "crossfade", "eq_restore"]
    elif bpm_s >= 0.9 and key_s < 0.5:
        technique = "key_clash_cut"
        beats = 8
        notes = "Tempo works; key is rough — short cut + high-pass filter sweep to mask clash."
        moves = ["sync", "filter_sweep_out", "quick_crossfade", "filter_reset"]
    elif bpm_s < 0.5:
        technique = "half_time_or_cut"
        beats = 4
        notes = "Tempo gap large — try half/double feel or a hard cut on the phrase."
        moves = ["rate_nudge_in", "hard_cut", "optional_loop_roll_out"]
    elif chroma > 0.7:
        technique = "chroma_matched_blend"
        beats = 16
        notes = "Chromagram similar (tonal bed) — trust a longer EQ blend even if keys differ slightly."
        moves = ["sync", "eq_kill_out_high", "crossfade", "eq_restore"]
    else:
        technique = "standard_blend"
        beats = 12
        notes = "Default instrument path: sync, mid scoop, crossfade."
        moves = ["sync", "eq_dip_out_mid", "crossfade"]

    # Showcase spice every few transitions when compatibility is high.
    if score >= 0.75 and technique in {"smooth_blend", "sample_callback_blend", "chroma_matched_blend"}:
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
            flourish = ("bass_swap", "scratch_preview", "loop_roll", "transformer_cut")[
                (index // profile.flourish_every) % 4
            ]
        if flourish == "scratch_preview" and tech["score"] >= 0.7:
            tech["moves"].insert(0, "optional_scratch_in")
        elif flourish == "loop_roll":
            tech["moves"].insert(0, "optional_loop_roll_out")
        elif flourish == "transformer_cut":
            tech["moves"].insert(0, "optional_transformer_cuts")
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


def main() -> None:
    from brain.mix_profiles import PROFILES, apply_brief, profile_provenance

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
        help="free-text mix description mapped onto the profile "
             "(e.g. 'smooth, longer blends, no tricks')",
    )
    parser.add_argument("--seconds-per-track", type=float, default=None)
    parser.add_argument("--phrase-analysis", type=Path, default=DEFAULT_PHRASES)
    parser.add_argument("--phrase-beats", type=int, default=None, choices=(16, 32, 48, 64))
    parser.add_argument("--out", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()

    profile, brief_notes = apply_brief(PROFILES[args.profile], args.mix_brief)
    print(f"profile: {profile.name} — {profile.description}")
    for note in brief_notes:
        print(f"  brief adjustment: {note}")

    tracks = json.loads(args.playlist.read_text())
    # Prefer analyzed tracks for a live mix
    analyzed = [t for t in tracks if t.get("bpm")]
    pool = analyzed if len(analyzed) >= 2 else tracks
    affinity = load_affinity_lookup()
    phrases = load_phrase_lookup(args.phrase_analysis)
    plan = build_plan(
        pool,
        count=min(args.tracks, len(pool)),
        seconds_per_track=args.seconds_per_track if args.seconds_per_track is not None else profile.seconds_per_track,
        affinity_lookup=affinity,
        phrase_lookup=phrases,
        phrase_beats=args.phrase_beats if args.phrase_beats is not None else profile.phrase_beats,
        profile=profile,
        provenance=profile_provenance(profile, args.mix_brief, brief_notes),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2) + "\n")
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
