"""The H Company computer-use agent. Drives Mixxx's actual GUI for anything
that isn't beat-critical (browse library, load a track to a deck, react to a
request) and emits shared.commands.Command objects for Hands to execute for
anything that is.

Needs HAI_API_KEY set (from platform.hcompany.ai) before this runs.
"""
from brain.library import CRATE, Energy, Track, find_next
from shared.commands import Command, LoadTrack

# TODO: swap in the real hai-agents SDK client once HAI_API_KEY is available
# and the local-desktop vs. cloud-browser environment choice is made — see
# docs/ARCHITECTURE.md. This stub only shows the decision loop shape.


class Brain:
    def __init__(self):
        self._current: Track | None = None

    def decide_next(self, requested_energy: Energy) -> Command | None:
        track = find_next(self._current, requested_energy)
        if track is None:
            return None
        self._current = track
        return LoadTrack(deck=self._next_free_deck(), track_id=track.track_id)

    def _next_free_deck(self) -> int:
        # TODO: track real deck state instead of hardcoding.
        return 2

    def load_track_via_gui(self, track: Track) -> None:
        """Visible on screen during the demo: agent searches Mixxx's
        library browser and drags the track to a deck."""
        raise NotImplementedError
