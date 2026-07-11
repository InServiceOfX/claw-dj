"""Command schema Brain sends to Hands. Brain expresses intent only —
no MIDI, no timing math, no raw deck state here.
"""
from dataclasses import dataclass
from enum import Enum


class LoopAction(str, Enum):
    IN = "in"
    OUT = "out"
    TOGGLE = "toggle"


class CrossfadeCurve(str, Enum):
    LINEAR = "linear"
    SCURVE = "scurve"


@dataclass(frozen=True)
class LoadTrack:
    deck: int
    track_id: str


@dataclass(frozen=True)
class SetHotcue:
    deck: int
    slot: int
    position_beats: float


@dataclass(frozen=True)
class TriggerHotcue:
    deck: int
    slot: int


@dataclass(frozen=True)
class Loop:
    deck: int
    beats: int
    action: LoopAction = LoopAction.TOGGLE


@dataclass(frozen=True)
class BeatJump:
    deck: int
    beats: int


@dataclass(frozen=True)
class Crossfade:
    from_deck: int
    to_deck: int
    duration_ms: int
    curve: CrossfadeCurve = CrossfadeCurve.LINEAR


Command = LoadTrack | SetHotcue | TriggerHotcue | Loop | BeatJump | Crossfade
