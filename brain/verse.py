"""Respect verse start/stop when picking a mix-in cue or a mix-out ride.

Canonical logic lives in `core-rust/clawdj/src/verse.rs` (`clawdj verse cue`).
This module is the in-process planner copy so mix builds do not spawn cargo.
Keep the tests in lockstep with the Rust unit tests.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

START_TOLERANCE_SECONDS = 2.0
INTRO_BEFORE_VERSE_SECONDS = 8.0
DEFAULT_BLEND_BEATS = 32
# Detector sometimes labels a whole cut as one "verse". Real rap/sung
# verses are ~16–24 bars. Do not auto-extend into that garbage.
MAX_VERSE_SECONDS = 80.0


@dataclass(frozen=True)
class LyricSegment:
    kind: str
    start: float
    end: float


@dataclass
class VerseCueDecision:
    legal: bool
    placement: str
    cue_seconds: float
    reason: str
    source: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _segments(raw: Iterable[dict[str, Any] | LyricSegment]) -> list[LyricSegment]:
    out: list[LyricSegment] = []
    for item in raw or []:
        if isinstance(item, LyricSegment):
            out.append(item)
            continue
        kind = str(item.get("kind") or "")
        try:
            start = float(item.get("start"))
            end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        if kind:
            out.append(LyricSegment(kind=kind, start=start, end=end))
    return out


def _is_verse(kind: str) -> bool:
    return kind.casefold() == "verse"


def _is_chorus(kind: str) -> bool:
    return kind.casefold() in {"chorus", "hook"}


def _containing(cue: float, segments: list[LyricSegment]) -> LyricSegment | None:
    # A boundary timestamp belongs to the segment that *starts* there
    # (chorus end 27.75 / verse start 27.75 is the verse).
    for segment in segments:
        if abs(segment.start - cue) <= 1e-9:
            return segment
    for segment in segments:
        if cue + 1e-9 > segment.start and cue < segment.end - 1e-9:
            return segment
    for segment in segments:
        if cue + 1e-9 >= segment.start and cue <= segment.end + 1e-9:
            return segment
    return None


def classify_cue(cue: float, segments: Iterable[dict[str, Any] | LyricSegment]) -> str:
    """Where a cue sits: intro / verse_start / mid_verse / chorus / mid_chorus / unknown."""
    items = _segments(segments)
    if not items:
        return "unknown"
    if cue <= START_TOLERANCE_SECONDS:
        first = min(items, key=lambda item: item.start)
        if first.start >= INTRO_BEFORE_VERSE_SECONDS or cue + START_TOLERANCE_SECONDS < first.start:
            return "intro"
    hit = _containing(cue, items)
    if hit is None:
        first_start = min(item.start for item in items)
        if cue + START_TOLERANCE_SECONDS < first_start:
            return "intro"
        return "unknown"
    into = cue - hit.start
    if _is_verse(hit.kind):
        return "verse_start" if into <= START_TOLERANCE_SECONDS else "mid_verse"
    if _is_chorus(hit.kind):
        return "chorus" if into <= START_TOLERANCE_SECONDS else "mid_chorus"
    if cue <= START_TOLERANCE_SECONDS:
        return "intro"
    return "unknown"


def has_vocal_verses(title: str = "", path: str = "") -> bool:
    """False for instrumental-only / no-vocal beds — no artist verse exists."""
    from brain.stems import classify_stem

    return classify_stem(title or "", path or "") != "instrumental_only"


def _has_intro_before(verse: LyricSegment, items: list[LyricSegment]) -> bool:
    return verse.start >= INTRO_BEFORE_VERSE_SECONDS or any(
        item.end <= verse.start + 1e-9 and item.start < verse.start for item in items
    )


def verse_cut_by_window(
    start: float,
    end: float,
    segments: Iterable[dict[str, Any] | LyricSegment],
) -> LyricSegment | None:
    """First real verse whose interior is eaten by [start, end]."""
    items = _segments(segments)
    for item in items:
        if not _is_verse(item.kind):
            continue
        if (item.end - item.start) > MAX_VERSE_SECONDS:
            continue
        overlap_lo = max(start, item.start + START_TOLERANCE_SECONDS)
        overlap_hi = min(end, item.end)
        if overlap_hi > overlap_lo + 1e-9:
            return item
    return None


def respect_verse_entry(
    proposed_cue: float,
    segments: Iterable[dict[str, Any] | LyricSegment],
    *,
    first_beat: float = 0.0,
    bpm: float | None = None,
    blend_beats: int = DEFAULT_BLEND_BEATS,
    title: str = "",
    path: str = "",
) -> VerseCueDecision:
    """Rewrite a cue that is mid-verse, or whose incoming blend *finishes* mid-verse."""
    del first_beat  # reserved: Mixxx first-beat offset is not a mid-verse landing
    if title or path:
        if not has_vocal_verses(title, path):
            return VerseCueDecision(
                legal=True,
                placement="unknown",
                cue_seconds=max(0.0, float(proposed_cue)),
                reason="instrumental / no vocals — verse boundaries do not apply",
                source="unchanged",
            )
    items = _segments(segments)
    placement = classify_cue(proposed_cue, items)
    period = 60.0 / bpm if bpm and bpm > 0 else None
    fader_at = (
        float(proposed_cue) + max(1, int(blend_beats)) * period if period else float(proposed_cue)
    )
    if float(proposed_cue) <= START_TOLERANCE_SECONDS:
        return VerseCueDecision(
            legal=True,
            placement=placement if placement != "unknown" else "intro",
            cue_seconds=max(0.0, float(proposed_cue)),
            reason="starting from the top is a legal mix-in",
            source="unchanged",
        )
    cut = verse_cut_by_window(float(proposed_cue), fader_at, items)
    if cut is None and placement != "mid_verse":
        return VerseCueDecision(
            legal=True,
            placement=placement,
            cue_seconds=max(0.0, float(proposed_cue)),
            reason=f"{placement} is a legal mix-in",
            source="unchanged",
        )
    verse = cut or _containing(proposed_cue, items)
    if verse is None or not _is_verse(verse.kind):
        return VerseCueDecision(
            legal=True,
            placement=placement,
            cue_seconds=max(0.0, float(proposed_cue)),
            reason="mid-verse but no containing verse segment",
            source="unchanged",
        )
    if _has_intro_before(verse, items):
        return VerseCueDecision(
            legal=False,
            placement="mid_verse",
            cue_seconds=0.0,
            reason=(
                f"incoming blend from {proposed_cue:.2f}s finishes inside verse "
                f"{verse.start:.2f}–{verse.end:.2f}; start from 0:00 so the blend "
                "covers the intro and the verse starts after the fader"
            ),
            source="intro_top",
        )
    preroll = (max(1, int(blend_beats)) * period) if period else 0.0
    cue = max(0.0, verse.start - preroll)
    return VerseCueDecision(
        legal=False,
        placement="mid_verse",
        cue_seconds=cue,
        reason=(
            f"incoming blend from {proposed_cue:.2f}s finishes inside verse "
            f"{verse.start:.2f}–{verse.end:.2f}; pre-roll onto verse start"
        ),
        source="verse_preroll",
    )


def respect_verse_exit(
    cue_seconds: float,
    ride_beats: int,
    bpm: float,
    segments: Iterable[dict[str, Any] | LyricSegment],
    *,
    blend_beats: int = DEFAULT_BLEND_BEATS,
    title: str = "",
    path: str = "",
) -> tuple[int, str]:
    """Extend a ride so the whole outgoing blend sits after the current verse."""
    if title or path:
        if not has_vocal_verses(title, path):
            return int(ride_beats), "unchanged"
    items = _segments(segments)
    if not items or bpm <= 0:
        return int(ride_beats), "unchanged"
    period = 60.0 / bpm
    fade_at = float(cue_seconds) + int(ride_beats) * period
    fade_done = fade_at + max(1, int(blend_beats)) * period
    verse = verse_cut_by_window(fade_at, fade_done, items)
    if verse is None:
        return int(ride_beats), "unchanged"
    needed = max(0, int((verse.end - float(cue_seconds)) / period + 0.999))
    if needed <= int(ride_beats):
        return int(ride_beats), "unchanged"
    capped = min(needed, int(ride_beats) + 128)
    return capped, (
        f"blend {fade_at:.2f}–{fade_done:.2f}s eats verse {verse.start:.2f}–{verse.end:.2f}; "
        f"extend ride {int(ride_beats)} -> {capped} so the fade starts at the verse end"
    )


@dataclass
class VerseViolation:
    track: str
    side: str
    at_seconds: float
    placement: str
    reason: str


def audit_mix_plan(
    plan: dict[str, Any],
    segments_by_id: dict[str, list[dict[str, Any]]],
) -> list[VerseViolation]:
    """Report mix-to-listen verse cuts. Deterministic; no subagent."""
    by_id = {str(row.get("track_id")): row for row in plan.get("tracks") or []}
    bodies = {
        str(event.get("track") or ""): event
        for event in plan.get("events") or []
        if event.get("op") == "play_body"
    }
    transitions = [event for event in plan.get("events") or [] if event.get("op") == "transition"]
    violations: list[VerseViolation] = []
    for event in transitions:
        to_label = str(event.get("to_track") or "")
        from_label = str(event.get("from_track") or "")
        blend = int(event.get("transition_beats") or DEFAULT_BLEND_BEATS)
        incoming = next(
            (
                row
                for row in by_id.values()
                if f"{row.get('artist')} — {row.get('title')}" == to_label
            ),
            None,
        )
        outgoing = next(
            (
                row
                for row in by_id.values()
                if f"{row.get('artist')} — {row.get('title')}" == from_label
            ),
            None,
        )
        if incoming and event.get("technique") != "vocal_over_bed":
            if not has_vocal_verses(
                str(incoming.get("title") or ""),
                str(incoming.get("track_id") or ""),
            ):
                incoming = None
        if incoming and event.get("technique") != "vocal_over_bed":
            segs = segments_by_id.get(str(incoming.get("track_id"))) or []
            cue = float(incoming.get("cue_seconds") or 0.0)
            bpm = float(incoming.get("bpm") or 0.0)
            period = 60.0 / bpm if bpm > 0 else 0.0
            fader_at = cue + blend * period
            # Cue 0 is a legal iconic intro even if the detector labeled the
            # first shouts as "verse".
            cut = (
                None
                if cue <= START_TOLERANCE_SECONDS
                else verse_cut_by_window(cue, fader_at, segs)
            )
            if cut is not None:
                violations.append(
                    VerseViolation(
                        track=to_label,
                        side="entry",
                        at_seconds=round(fader_at, 2),
                        placement="mid_verse",
                        reason=(
                            f"cue {cue:.2f}s + {blend}-beat blend finishes at "
                            f"{fader_at:.2f}s inside verse {cut.start:.2f}–{cut.end:.2f}"
                        ),
                    )
                )
        if outgoing and not has_vocal_verses(
            str(outgoing.get("title") or ""),
            str(outgoing.get("track_id") or ""),
        ):
            outgoing = None
        if outgoing:
            segs = segments_by_id.get(str(outgoing.get("track_id"))) or []
            body = bodies.get(from_label) or {}
            if body.get("trust_ride_beats"):
                continue
            cue = float(outgoing.get("cue_seconds") or 0.0)
            bpm = float(outgoing.get("bpm") or 0.0)
            ride = int(body.get("beats") or 0)
            if bpm <= 0 or ride <= 0:
                continue
            period = 60.0 / bpm
            fade_at = cue + ride * period
            fade_done = fade_at + blend * period
            cut = verse_cut_by_window(fade_at, fade_done, segs)
            if cut is not None:
                violations.append(
                    VerseViolation(
                        track=from_label,
                        side="exit",
                        at_seconds=round(fade_at, 2),
                        placement="mid_verse",
                        reason=(
                            f"blend {fade_at:.2f}–{fade_done:.2f}s eats verse "
                            f"{cut.start:.2f}–{cut.end:.2f}"
                        ),
                    )
                )
    return violations


def segments_from_lyrics_json(artist: str, title: str) -> list[dict[str, Any]]:
    """Verse/chorus map from the on-disk LRCLIB cache when sqlite is empty."""
    from brain.lyric_timeline import detect_segments, parse_lrc
    from brain.lyrics import LYRICS_DIR, cache_key

    path = LYRICS_DIR / f"{cache_key(artist, title)}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    lrc = data.get("synced_lyrics") or data.get("syncedLyrics") or data.get("lrc") or ""
    if not lrc:
        return []
    return [
        {"kind": item.kind, "start": item.start, "end": item.end, "first_line": item.first_line}
        for item in detect_segments(parse_lrc(lrc))
    ]


def fill_segment_lookup(
    tracks: list[dict[str, Any]], lookup: dict[str, list[dict[str, Any]]]
) -> dict[str, list[dict[str, Any]]]:
    """Sqlite segments win; lyrics JSON fills gaps so verse_guard actually runs."""
    filled = dict(lookup)
    for row in tracks:
        track_id = str(row.get("track_id") or "")
        if not track_id:
            continue
        if not has_vocal_verses(str(row.get("title") or ""), track_id):
            filled.pop(track_id, None)
            continue
        if filled.get(track_id):
            continue
        extra = segments_from_lyrics_json(str(row.get("artist") or ""), str(row.get("title") or ""))
        if extra:
            filled[track_id] = extra
    return filled
