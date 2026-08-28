"""Vocals-only / instrumental-only stems: classify and pick a two-deck bed.

Canonical scoring lives in `core-rust/clawdj/src/stems.rs` (`clawdj stems pair`).
This module is the in-process planner copy so mix builds do not spawn cargo.
Keep the classify / pair tests in lockstep with the Rust unit tests.
"""
from __future__ import annotations

import json
import re
from typing import Any

from brain.mix_graph import bpm_compatibility, key_compatibility

VOCALS_ONLY = re.compile(
    r"(?:\bacap+ell+a?\b|\ba\s+cappella\b|\bvocals?[- ]only\b)",
    re.IGNORECASE,
)
_INSTRUMENTAL_TAG = re.compile(
    r"(\((?:instrumental|instr\.)\)|\[(?:instrumental|instr\.)\]|\s-\s*instrumental\s*$)",
    re.IGNORECASE,
)
_VERSION_STOP = {
    "instrumental",
    "acapella",
    "acappella",
    "remix",
    "version",
    "dirty",
    "clean",
    "album",
    "feat.",
    "ft.",
    "-",
}


def classify_stem(title: str, path: str = "") -> str:
    hay = f"{title} {path}".lower()
    if VOCALS_ONLY.search(hay):
        return "vocals_only"
    lower_title = title.lower()
    if _INSTRUMENTAL_TAG.search(title) or lower_title.endswith(" instrumental"):
        if "instrumental hip" in lower_title:
            return "full_mix"
        return "instrumental_only"
    if "/instrumental/" in hay:
        return "instrumental_only"
    return "full_mix"


def is_showcase_acapella(notes: str) -> bool:
    return "showcase_acapella" in (notes or "").casefold()


def is_vocal_over_bed(notes: str) -> bool:
    return "vocal_over_bed" in (notes or "").casefold()


def core_title(title: str) -> str:
    stripped = re.sub(r"\([^)]*\)", " ", title or "")
    stripped = re.sub(r"\[[^\]]*\]", " ", stripped)
    return " ".join(
        token
        for token in stripped.lower().split()
        if token and token not in _VERSION_STOP
    )


def pair_vocals(tracks: list[dict[str, Any]]) -> dict[str, Any]:
    used: set[str] = set()
    pairs: list[dict[str, Any]] = []
    claimed: set[str] = set()
    vocals = []
    for vocal_index, vocal in enumerate(tracks):
        kind = classify_stem(vocal.get("title") or "", vocal.get("track_id") or "")
        if kind != "vocals_only":
            continue
        if is_showcase_acapella(vocal.get("dj_notes") or ""):
            continue
        vocals.append((vocal_index, vocal))
    # Neighbor instrumentals first so a later vocal cannot steal this bed.
    leftover = []
    for vocal_index, vocal in vocals:
        neighbor = _neighbor_instrumental(vocal, vocal_index, tracks, used)
        if neighbor is None:
            leftover.append((vocal_index, vocal))
            continue
        used.add(neighbor["bed_id"])
        claimed.add(vocal["track_id"])
        pairs.append(neighbor)
    for vocal_index, vocal in leftover:
        best = _best_bed(vocal, vocal_index, tracks, used)
        if best is None:
            continue
        used.add(best["bed_id"])
        claimed.add(vocal["track_id"])
        pairs.append(best)
    unpaired = [
        vocal["track_id"] for _, vocal in vocals if vocal["track_id"] not in claimed
    ]
    return {"version": 1, "pairs": pairs, "unpaired_vocals": unpaired}


def apply_vocal_layers(tracks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Place each dry vocal over a bed: two decks at once, not a transition.

    Mutates a copy of `tracks`. Showcase acapellas are left sequential.
    Vocals that already declare `entry_style=vocal_over_bed` keep their note
    but are still moved so the chosen bed sits immediately before them.
    """
    report = pair_vocals(tracks)
    if report["unpaired_vocals"]:
        by_title = {row["track_id"]: row.get("title") or row["track_id"] for row in tracks}
        names = ", ".join(by_title.get(track_id, track_id) for track_id in report["unpaired_vocals"])
        raise ValueError(
            "vocals-only track(s) have no instrumental bed to layer over: "
            f"{names}. Add an instrumental-only track (or a full mix to loop), "
            "or mark a deliberate showcase_acapella exception"
        )
    notes: list[str] = []
    by_id = {row["track_id"]: dict(row) for row in tracks}
    order = [row["track_id"] for row in tracks]
    for pair in report["pairs"]:
        vocal = by_id[pair["vocal_id"]]
        bed = by_id[pair["bed_id"]]
        vocal_notes = vocal.get("dj_notes") or ""
        if not is_vocal_over_bed(vocal_notes):
            extra = (
                "Two-deck layer, not a mix transition. "
                "entry_style=vocal_over_bed; ride_beats=96; trust_ride_beats; no_flourish"
            )
            if pair["loop_bed"]:
                extra += "; bed_loop_beats=32"
            vocal["dj_notes"] = f"{vocal_notes} {extra}".strip()
        elif pair["loop_bed"] and "bed_loop_beats" not in vocal_notes:
            vocal["dj_notes"] = f"{vocal_notes}; bed_loop_beats=32"
        bed_id = pair["bed_id"]
        vocal_id = pair["vocal_id"]
        order = [item for item in order if item != bed_id]
        vocal_at = order.index(vocal_id)
        order.insert(vocal_at, bed_id)
        notes.append(
            f"layer {vocal.get('title')} over {bed.get('title')} ({pair['reason']})"
        )
    layered = [by_id[track_id] for track_id in order]
    return layered, notes


def assert_vocals_layered(plan: dict[str, Any], notes: dict[str, str] | None = None) -> None:
    """Refuse a built plan that would ride a vocals-only stem by itself.

    Canonical pattern (50centgunitera Get Up over Outta Control Instrumental):
    the instrumental bed stays live, the vocal layers on the other deck,
    `keep_outgoing_live` is set, and there is no solo `play_body` on the
    acapella. A 32-beat dry body is still only vocals.
    """
    notes = notes or {}
    tracks = list(plan.get("tracks") or [])
    by_id = {str(row.get("track_id") or ""): row for row in tracks}
    by_display = {
        f"{row.get('artist', '')} — {row.get('title')}": row for row in tracks
    }
    body_beats = {
        str(event.get("track") or ""): int(event.get("beats") or 0)
        for event in plan.get("events") or []
        if event.get("op") == "play_body"
    }
    layers: dict[str, dict[str, Any]] = {}
    for event in plan.get("events") or []:
        if event.get("technique") != "vocal_over_bed" and "vocal_over_bed" not in (
            event.get("moves") or []
        ):
            continue
        vocal_id = str(event.get("vocal_track_id") or "")
        if not vocal_id:
            incoming = by_display.get(str(event.get("to_track") or ""))
            vocal_id = str((incoming or {}).get("track_id") or "")
        if vocal_id:
            layers[vocal_id] = event
    for track in tracks:
        title = str(track.get("title") or "")
        track_id = str(track.get("track_id") or "")
        if classify_stem(title, track_id) != "vocals_only":
            continue
        note = notes.get(track_id, "") or str(track.get("dj_notes") or "")
        if is_showcase_acapella(note):
            continue
        display = f"{track.get('artist', '')} — {title}"
        solo = body_beats.get(display, 0)
        if solo > 0:
            raise ValueError(
                f"vocals-only track {display} has a solo play_body event "
                f"({solo} beats). Dry vocal is not a mix — pair it with a "
                "compatible instrumental (or a looped instrumental section) "
                "via entry_style=vocal_over_bed, or mark a deliberate "
                "showcase_acapella exception"
            )
        event = layers.get(track_id)
        if event is None:
            raise ValueError(
                f"vocals-only track {display} is not layered over a bed. "
                "Use entry_style=vocal_over_bed on a two-deck pair, or mark "
                "showcase_acapella"
            )
        if not event.get("keep_outgoing_live"):
            raise ValueError(
                f"vocals-only track {display} must keep the instrumental bed "
                "live (keep_outgoing_live). Fade the vocal out; do not stop "
                "the bed — Get Up (Acapella) over Outta Control Instrumental "
                "is the pattern"
            )
        bed_id = str(event.get("bed_track_id") or "")
        bed = by_id.get(bed_id)
        if bed is None:
            bed = by_display.get(str(event.get("from_track") or ""))
        bed_kind = classify_stem(
            str((bed or {}).get("title") or ""),
            str((bed or {}).get("track_id") or bed_id),
        )
        moves = event.get("moves") or []
        if bed_kind == "instrumental_only" or "bed_loop" in moves:
            continue
        raise ValueError(
            f"vocals-only track {display} is layered over a full mix with "
            "vocals. Use an instrumental-only bed, or loop a cued "
            "instrumental section (bed_loop_beats / bed_loop)"
        )


def _neighbor_instrumental(
    vocal: dict[str, Any],
    vocal_index: int,
    tracks: list[dict[str, Any]],
    used: set[str],
) -> dict[str, Any] | None:
    """An instrumental sitting next to the acapella is the intended bed."""
    for delta in (-1, 1):
        index = vocal_index + delta
        if index < 0 or index >= len(tracks):
            continue
        bed = tracks[index]
        if bed.get("track_id") in used:
            continue
        kind = classify_stem(bed.get("title") or "", bed.get("track_id") or "")
        if kind == "instrumental_only":
            return _score_bed(vocal, vocal_index, bed, index, kind)
    return None


def _best_bed(
    vocal: dict[str, Any],
    vocal_index: int,
    tracks: list[dict[str, Any]],
    used: set[str],
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for bed_index, bed in enumerate(tracks):
        if bed.get("track_id") == vocal.get("track_id"):
            continue
        if bed.get("track_id") in used:
            continue
        kind = classify_stem(bed.get("title") or "", bed.get("track_id") or "")
        if kind == "vocals_only":
            continue
        pair = _score_bed(vocal, vocal_index, bed, bed_index, kind)
        if best is None or pair["score"] > best["score"] or (
            pair["score"] == best["score"] and pair["bed_id"] < best["bed_id"]
        ):
            best = pair
    return best


def _score_bed(
    vocal: dict[str, Any],
    vocal_index: int,
    bed: dict[str, Any],
    bed_index: int,
    kind: str,
) -> dict[str, Any]:
    same_song = bool(core_title(vocal.get("title") or "")) and (
        core_title(vocal.get("title") or "") == core_title(bed.get("title") or "")
    )
    adjacent = abs(vocal_index - bed_index) == 1
    score = 0.0
    reasons: list[str] = []
    if kind == "instrumental_only":
        score += 3.0
        reasons.append("instrumental-only bed")
    else:
        score += 0.5
        reasons.append("full-mix looped section bed")
    bpm_score, bpm_reason = bpm_compatibility(vocal.get("bpm"), bed.get("bpm"))
    score += float(bpm_score) * 2.0
    if bpm_reason:
        reasons.append(bpm_reason)
    key_score, key_reason = key_compatibility(vocal.get("key"), bed.get("key"))
    score += float(key_score) * 2.0
    if key_reason:
        reasons.append(key_reason)
    if same_song:
        reasons.append("same-song stack (legal, not preferred)")
    elif key_score >= 0.55:
        score += 2.0
        reasons.append("different song")
    if adjacent:
        score += 1.0
        reasons.append("already adjacent")
    return {
        "vocal_id": vocal["track_id"],
        "bed_id": bed["track_id"],
        "score": score,
        "reason": "; ".join(reasons),
        "same_song": same_song,
        "bed_kind": kind,
        "loop_bed": kind == "full_mix",
    }


def dumps_pair_payload(tracks: list[dict[str, Any]]) -> str:
    """JSON array `clawdj stems pair` accepts on stdin."""
    payload = []
    for row in tracks:
        payload.append(
            {
                "track_id": row["track_id"],
                "title": row.get("title") or "",
                "artist": row.get("artist") or "",
                "bpm": row.get("bpm"),
                "key": row.get("key"),
                "path": row.get("track_id"),
                "dj_notes": row.get("dj_notes") or "",
            }
        )
    return json.dumps(payload)
