"""Single plan-aware entry point for mix composition."""
from __future__ import annotations

import json
import os
import tempfile

from brain import order_constraints, plan_journal, plan_notes, plan_paths, transition_overrides
from brain.build_mix_plan import compose_mix_plan
from brain.stems import assert_vocals_layered
from brain.plan_mix_envelope import decorate
from brain.plan_revision import StalePlanError, file_rev, plan_rev, write_checked


def _validate_vocals_only_playback(plan: dict, notes: dict[str, str]) -> None:
    """Refuse a built plan that would ride a vocals-only stem by itself.

    Canonical: Get Up (Acapella) over Outta Control Instrumental — two
    decks, bed stays live, no solo `play_body`. A 32-beat dry body is
    still the vocal alone. The only sequential exception is an explicit
    `showcase_acapella` note.
    """
    assert_vocals_layered(plan, notes)


def playlist_path(slug: str):
    return plan_paths.resolve(slug).playlist


def mix_plan_path(slug: str):
    return plan_paths.resolve(slug).mix_plan


def build(slug: str, *, profile=None, dj_format=None, seconds_per_track=None, **opts) -> dict:
    paths = plan_paths.resolve(slug)
    rows = json.loads(paths.playlist.read_text())
    track_ids = [row["track_id"] for row in rows]
    if len(track_ids) != len(set(track_ids)):
        raise ValueError("plan playlist contains duplicate track ids")
    notes = {item.track_id: item.note for item in plan_notes.get_effective(slug, track_ids)}
    constraints = order_constraints.from_activations(slug)
    before = file_rev(paths.mix_plan)
    inputs_before = plan_rev(paths)
    fd, temporary_name = tempfile.mkstemp(prefix=".mix-build-", suffix=".json", dir=paths.root)
    os.close(fd)
    try:
        if "control_api_port" in opts and "control_port" not in opts:
            opts["control_port"] = opts.pop("control_api_port")
        # Beat-length overrides must reach compose/build_plan so previous_fade and
        # phase_anchor arithmetic match the runner. Technique/notes can still be
        # patched onto events after the structural plan exists. Load all stored
        # pair beat lengths (not only currently-adjacent ones) so a rebuild that
        # reorders still applies the override if the pair becomes adjacent.
        beats_by_pair = {
            (item.from_track_id, item.to_track_id): int(item.beats)
            for item in transition_overrides.load(slug)
            if item.beats is not None and not item.clear.get("beats")
        }
        plan = compose_mix_plan(
            playlist=paths.playlist,
            profile_name=profile or "dj-showcase",
            dj_format_name=dj_format or "none",
            seconds_per_track=seconds_per_track,
            out=type(paths.mix_plan)(temporary_name),
            dj_notes_lookup=notes,
            fixed_groups=[list(group) for group in constraints.groups],
            transition_beats_by_pair=beats_by_pair,
            prepare_backbeat=False,
            **opts,
        )
        _validate_vocals_only_playback(plan, notes)
        built_ids = [track["track_id"] for track in plan.get("tracks", [])]
        expected = track_ids
        if opts.get("tracks") is None:
            if len(built_ids) != len(expected) or set(built_ids) != set(expected):
                raise ValueError("mix build did not preserve every included track exactly once")
        # Builder segments historically carried display labels only; pair ids
        # are added here so sparse overrides and attribution stay stable.
        for index, segment in enumerate(plan.get("segments", [])):
            if index + 1 < len(built_ids):
                segment["from_track_id"] = built_ids[index]
                segment["to_track_id"] = built_ids[index + 1]
        reconciled = transition_overrides.reconcile(built_ids, transition_overrides.load(slug))
        plan["segments"] = transition_overrides.merge(plan.get("segments", []), reconciled)
        override_by_pair = {(item.from_track_id, item.to_track_id): item for item in reconciled if item.state == "active"}
        transition_events = [event for event in plan.get("events", []) if event.get("op") == "transition"]
        for index, event in enumerate(transition_events):
            if index + 1 >= len(built_ids):
                break
            override = override_by_pair.get((built_ids[index], built_ids[index + 1]))
            if override is None:
                continue
            for field in ("technique", "showcase_move", "effects", "note"):
                value = getattr(override, field)
                if override.clear.get(field):
                    event.pop(field, None)
                elif value is not None:
                    event[field] = value
            if override.clear.get("beats"):
                event.pop("transition_beats", None)
            elif override.beats is not None:
                # Structural beats already applied inside build_plan; keep the
                # event field aligned and refuse silent drift.
                event["transition_beats"] = override.beats
            event["author"] = override.author.value if override.author else None
        # Final technique/length overrides change what audio overlaps. Analyze
        # and certify the final events, never an intermediate composition.
        from brain.rhythm import prepare_plan
        prepare_plan(plan)
        inputs_after = plan_rev(paths)
        if inputs_after.token != inputs_before.token:
            changed = [name for name, rev in inputs_before.files.items() if inputs_after.files.get(name) != rev]
            raise StalePlanError(inputs_after.token, changed_files=changed)
        plan = decorate(plan, slug, paths)
        after = write_checked(paths.mix_plan, plan, before)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    plan_journal.append(slug, "agent", "build_mix", {"track_count": plan.get("track_count")}, before, after)
    return plan
