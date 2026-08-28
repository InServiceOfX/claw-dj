"""Focused tempfile coverage for multi-plan foundation modules 1-15."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from brain import (
    bunch_store,
    library_index,
    order_constraints,
    plan_bunch_activation,
    plan_context,
    plan_journal,
    plan_migration,
    plan_mix_build,
    plan_mix_envelope,
    plan_notes,
    plan_paths,
    plan_revision,
    plan_staleness,
    plan_store,
    transition_overrides,
)
from brain.plan_types import Author, PlanPaths, PlanStatus, TransitionOverride, header_safe, slugify, validate_slug


class PlanFoundationTest(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plans = self.root / "data" / "plans"
        self.db = self.root / "data" / "library.sqlite3"
        self.patches = [
            patch.object(plan_paths, "DEFAULT_PLANS_DIR", self.plans),
            patch.object(bunch_store, "DEFAULT_INDEX", self.db),
            patch.object(plan_notes, "DEFAULT_INDEX", self.db),
            patch.object(library_index, "DEFAULT_INDEX", self.db),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def _plan(self, name="First Plan"):
        return plan_store.create(name)

    def _track(self, track_id, note="global", available=1):
        with library_index.connect(self.db) as db:
            db.execute(
                "INSERT INTO tracks(track_id,root,size_bytes,mtime_ns,title,artist,dj_notes,first_seen_at,last_seen_at,available,tag_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (track_id, "/music", 1, 1, track_id, "Artist", note, 1.0, 1.0, available, "ok"),
            )
            db.commit()

    def test_01_plan_types_are_strict_and_safe(self):
        self.assertEqual([item.value for item in PlanStatus], ["wip", "ready", "archived"])
        self.assertEqual(len(fields(PlanPaths)), 10)
        self.assertEqual(slugify("Active"), "active-2")
        with self.assertRaises(ValueError):
            validate_slug("../escape")
        self.assertEqual(header_safe("safe\r\nInjected"), "safeInjected")

    def test_02_paths_scan_directories_without_registry_and_guard_traversal(self):
        meta = self._plan()
        self.assertEqual(plan_paths.list_slugs(), [meta.slug])
        self.assertEqual(plan_paths.resolve(meta.slug).root, (self.plans / meta.slug).resolve())
        self.assertFalse((self.plans / "index.json").exists())
        with self.assertRaises(ValueError):
            plan_paths.resolve("../escape")

    def test_03_revision_is_content_based_atomic_and_rejects_stale_base(self):
        meta = self._plan()
        path = plan_paths.resolve(meta.slug).selection
        original = plan_revision.file_rev(path)
        new = plan_revision.write_checked(path, {"version": 1, "track_ids": ["a"]}, original)
        self.assertNotEqual(new, original)
        with self.assertRaises(plan_revision.StalePlanError) as caught:
            plan_revision.write_checked(path, {"track_ids": ["b"]}, original)
        self.assertEqual(caught.exception.payload()["current_rev"], new)

    def test_04_journal_is_append_only_filterable_and_tolerates_truncated_tail(self):
        meta = self._plan()
        plan_journal.append(meta.slug, "cli", "edit", {"x": 1}, "a", "b", author="llm")
        with plan_paths.resolve(meta.slug).journal.open("ab") as stream:
            stream.write(b'{"truncated"')
        rows = plan_journal.read(meta.slug, actor="cli", author="llm")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["author"], "llm")

    def test_05_store_lifecycle_switches_without_destroying_other_plans(self):
        first = self._plan("Notorious BIG Tribute")
        second = self._plan("2001 Expanded")
        plan_store.set_active(first.slug)
        plan_store.set_active(second.slug)
        self.assertTrue(plan_paths.resolve(first.slug).plan_json.exists())
        old_slug = first.slug
        renamed = plan_store.rename(first.slug, "BIG Tribute Revised", plan_revision.file_rev(plan_paths.resolve(first.slug).plan_json))
        self.assertEqual(renamed.slug, old_slug)
        ready = plan_store.set_status(first.slug, PlanStatus.READY, plan_revision.file_rev(plan_paths.resolve(first.slug).plan_json))
        self.assertEqual(ready.status, PlanStatus.READY)
        plan_store.delete(first.slug)
        self.assertTrue((self.plans / ".trash" / first.slug / "tombstone.json").exists())

    def test_06_context_refreshes_disk_truth_without_cached_singleton(self):
        meta = self._plan()
        plan_store.set_active(meta.slug)
        first = plan_context.for_request({}, {})
        selection = first.paths.selection
        plan_revision.write_checked(selection, {"version": 1, "track_ids": ["external"]}, plan_revision.file_rev(selection))
        refreshed = plan_context.for_request({}, {})
        self.assertNotEqual(first.rev.token, refreshed.rev.token)

    def test_07_bunch_store_keeps_exact_order_and_allows_library_overlap(self):
        one = bunch_store.create("one", ["a", "b", "c"], True, "human", "works")
        two = bunch_store.create("two", ["b", "d"], True, "human", "also works")
        self.assertEqual(bunch_store.get(one.bunch_id).track_ids, ("a", "b", "c"))
        self.assertEqual({b.bunch_id for b in bunch_store.list_for_track("b")}, {one.bunch_id, two.bunch_id})
        result = bunch_store.update_members(two.bunch_id, ["b"])
        self.assertTrue(result.auto_archived)

    def test_08_activation_enforces_disjoint_membership_and_disable_is_unbunch(self):
        meta = self._plan()
        one = bunch_store.create("one", ["a", "b"], True, "human", "")
        two = bunch_store.create("two", ["b", "c"], True, "human", "")
        path = plan_paths.resolve(meta.slug).bunches
        plan_bunch_activation.activate(meta.slug, one.bunch_id, base_rev=plan_revision.file_rev(path))
        with self.assertRaises(plan_bunch_activation.OverlapConflict):
            plan_bunch_activation.activate(meta.slug, two.bunch_id, base_rev=plan_revision.file_rev(path))
        plan_bunch_activation.deactivate(meta.slug, one.bunch_id, base_rev=plan_revision.file_rev(path))
        plan_bunch_activation.activate(meta.slug, two.bunch_id, base_rev=plan_revision.file_rev(path))
        self.assertEqual([x["bunch_id"] for x in plan_bunch_activation.list_active(meta.slug)], [two.bunch_id])

    def test_09_plan_notes_overlay_and_clear_never_overwrite_global(self):
        meta = self._plan()
        self._track("/music/a.mp3", "global human note")
        path = plan_paths.resolve(meta.slug).notes
        plan_notes.set_override(meta.slug, "/music/a.mp3", "plan note", Author.LLM, plan_revision.file_rev(path))
        self.assertEqual(plan_notes.get_effective(meta.slug, ["/music/a.mp3"])[0].layer, "plan")
        effective = plan_notes.clear_override(meta.slug, "/music/a.mp3", plan_revision.file_rev(path))
        self.assertEqual((effective.layer, effective.note), ("global", "global human note"))
        with library_index.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT dj_notes FROM tracks").fetchone()[0], "global human note")

    def test_10_transition_overrides_are_pair_keyed_sparse_and_reactivate(self):
        meta = self._plan()
        path = plan_paths.resolve(meta.slug).transitions
        override = TransitionOverride("a", "b", technique="cut", beats=None, author=Author.LLM)
        transition_overrides.upsert(meta.slug, override, plan_revision.file_rev(path))
        merged = transition_overrides.merge([{"from_track_id": "a", "to_track_id": "b", "technique": "blend", "beats": 16}], transition_overrides.load(meta.slug))
        self.assertEqual((merged[0]["technique"], merged[0]["beats"]), ("cut", 16))
        self.assertEqual(transition_overrides.reconcile(["a", "x", "b"], transition_overrides.load(meta.slug))[0].state, "orphaned")
        self.assertEqual(transition_overrides.reconcile(["a", "b"], transition_overrides.load(meta.slug))[0].state, "active")

    def test_11_order_constraint_contraction_expands_every_track_once(self):
        rows = [{"track_id": item, "bpm": 90} for item in ["a", "x", "b", "c", "z"]]
        contracted, table = order_constraints.contract(rows, [["a", "b", "c"]])
        ids = [row["track_id"] for row in contracted]
        expanded = order_constraints.expand(list(reversed(ids)), table)
        self.assertCountEqual(expanded, ["a", "x", "b", "c", "z"])
        self.assertEqual(len(expanded), len(set(expanded)))
        order_constraints.assert_intact(expanded, [["a", "b", "c"]])
        self.assertEqual(order_constraints.merge_groups([("a", "b"), ("b", "c")]), [["a", "b", "c"]])

        from brain.mix_order_brief import apply_constraints
        brief_rows = [{"track_id": item, "artist": item, "title": item, "bpm": 90, "key": "Am"} for item in ["a", "x", "b", "c", "z"]]
        ordered, _ = apply_constraints(brief_rows, {"adjacent": [("t000", "t002"), ("t002", "t003")], "adjacent_ordered": True})
        ordered_ids = [row["track_id"] for row in ordered]
        order_constraints.assert_intact(ordered_ids, [["a", "b", "c"]])

    def test_12_envelope_accepts_v2_and_preserves_all_existing_event_ops(self):
        meta = self._plan()
        paths = plan_paths.resolve(meta.slug)
        ops = ["load", "start", "play_body", "transition", "preload", "opener_effect", "finale", "stop_all", "gesture"]
        source = {"version": 2, "events": [{"op": op} for op in ops], "segments": []}
        paths.mix_plan.write_text(json.dumps(source))
        self.assertEqual(plan_mix_envelope.read_tolerant(paths.mix_plan)["version"], 2)
        decorated = plan_mix_envelope.decorate(source, meta.slug, paths)
        self.assertEqual([e["op"] for e in decorated["events"]], ops)
        self.assertEqual((decorated["version"], decorated["plan_slug"]), (3, meta.slug))

    def test_13_plan_build_uses_plan_paths_v3_overrides_bunch_and_port(self):
        meta = self._plan()
        paths = plan_paths.resolve(meta.slug)
        rows = [{"track_id": "a", "artist": "A", "title": "A", "bpm": 90, "key": "Am"}, {"track_id": "b", "artist": "B", "title": "B", "bpm": 91, "key": "Am"}]
        paths.playlist.write_text(json.dumps(rows))
        bunch = bunch_store.create("pair", ["a", "b"], True, "human", "")
        plan_bunch_activation.activate(meta.slug, bunch.bunch_id, base_rev=plan_revision.file_rev(paths.bunches))
        transition_overrides.upsert(meta.slug, TransitionOverride("a", "b", technique="cut", author=Author.HUMAN), plan_revision.file_rev(paths.transitions))
        captured = {}
        def fake_compose(**kwargs):
            captured.update(kwargs)
            return {"version": 2, "track_count": 2, "tracks": rows, "segments": [{"technique": "blend", "beats": 16}], "events": [{"op": "load"}, {"op": "transition", "technique": "blend", "transition_beats": 16}], "runtime": {"mixxx_control_port": kwargs["control_port"]}}
        with patch.object(plan_mix_build, "compose_mix_plan", fake_compose):
            result = plan_mix_build.build(meta.slug, control_api_port=10001)
        self.assertEqual(captured["playlist"], paths.playlist)
        self.assertEqual(captured["fixed_groups"], [["a", "b"]])
        self.assertEqual(result["segments"][0]["technique"], "cut")
        self.assertEqual(result["events"][1]["technique"], "cut")
        self.assertEqual((result["version"], result["runtime"]["mixxx_control_port"]), (3, 10001))

    def test_13b_real_plan_build_preserves_complete_pool_and_atomic_bunch(self):
        meta = self._plan("Real Build")
        paths = plan_paths.resolve(meta.slug)
        rows = [
            {"track_id": item, "artist": item.upper(), "title": item, "bpm": bpm, "key": "Am"}
            for item, bpm in [("a", 120), ("b", 91), ("c", 140), ("d", 90)]
        ]
        paths.playlist.write_text(json.dumps(rows))
        bunch = bunch_store.create("exact triple", ["d", "b", "c"], True, "human", "")
        plan_bunch_activation.activate(meta.slug, bunch.bunch_id, base_rev=plan_revision.file_rev(paths.bunches))
        result = plan_mix_build.build(meta.slug, profile="mix-to-listen", control_port=10002)
        order = [track["track_id"] for track in result["tracks"]]
        self.assertCountEqual(order, [row["track_id"] for row in rows])
        self.assertEqual(len(order), len(set(order)))
        order_constraints.assert_intact(order, [["d", "b", "c"]])
        self.assertTrue(result["bunches"][0]["honored"])

    def test_13c_plan_build_rejects_a_solo_acapella_body(self):
        meta = self._plan("Stem Safety")
        paths = plan_paths.resolve(meta.slug)
        vocal_id = "/music/get-up-acapella.mp3"
        bed_id = "/music/compatible-instrumental.mp3"
        rows = [
            {"track_id": bed_id, "artist": "Artist", "title": "Compatible (Instrumental)", "bpm": 92, "key": "F#m"},
            {"track_id": vocal_id, "artist": "Artist", "title": "Get Up (Acapella)", "bpm": 184, "key": "F#m"},
        ]
        for row in rows:
            self._track(row["track_id"], note="")
        paths.playlist.write_text(json.dumps(rows))

        def fake_compose(**kwargs):
            return {
                "version": 2,
                "track_count": 2,
                "tracks": rows,
                "segments": [{"technique": "smooth_blend", "beats": 32}],
                "events": [
                    {"op": "transition", "from_track": "Artist — Compatible (Instrumental)", "to_track": "Artist — Get Up (Acapella)"},
                    {"op": "play_body", "track": "Artist — Get Up (Acapella)", "beats": 129},
                ],
                "runtime": {"mixxx_control_port": kwargs.get("control_port", 9995)},
            }

        with patch.object(plan_mix_build, "compose_mix_plan", fake_compose):
            with self.assertRaisesRegex(ValueError, "vocals-only.*Get Up.*vocal_over_bed"):
                plan_mix_build.build(meta.slug)

    def test_13d_vocals_only_validator_rejects_short_dry_break_allows_showcase_and_layer(self):
        track_id = "/music/get-up-acapella.mp3"
        plan = {
            "tracks": [{"track_id": track_id, "artist": "Artist", "title": "Get Up (Acapella)"}],
            "events": [{"op": "play_body", "track": "Artist — Get Up (Acapella)", "beats": 32}],
        }
        with self.assertRaisesRegex(ValueError, "solo play_body"):
            plan_mix_build._validate_vocals_only_playback(plan, {})
        plan_mix_build._validate_vocals_only_playback(
            plan, {track_id: "showcase_acapella; ride_beats=32; trust_ride_beats"}
        )
        layered = {
            "tracks": [
                {"track_id": "/music/bed.mp3", "artist": "Artist", "title": "Outta Control - Instrumental"},
                {"track_id": track_id, "artist": "Artist", "title": "Get Up (Acapella)"},
            ],
            "events": [
                {
                    "op": "transition",
                    "technique": "vocal_over_bed",
                    "moves": ["sync", "vocal_over_bed"],
                    "keep_outgoing_live": True,
                    "vocal_track_id": track_id,
                    "bed_track_id": "/music/bed.mp3",
                }
            ],
        }
        plan_mix_build._validate_vocals_only_playback(layered, {})
        over_full_mix = {
            "tracks": [
                {"track_id": "/music/best-friend.mp3", "artist": "50 Cent", "title": "Best Friend"},
                {"track_id": track_id, "artist": "Artist", "title": "Get Up (Acapella)"},
            ],
            "events": [
                {
                    "op": "transition",
                    "technique": "vocal_over_bed",
                    "moves": ["sync", "vocal_over_bed"],
                    "keep_outgoing_live": True,
                    "vocal_track_id": track_id,
                    "bed_track_id": "/music/best-friend.mp3",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "instrumental-only bed"):
            plan_mix_build._validate_vocals_only_playback(over_full_mix, {})
        no_keep = {
            "tracks": layered["tracks"],
            "events": [
                {
                    "op": "transition",
                    "technique": "vocal_over_bed",
                    "moves": ["sync", "vocal_over_bed"],
                    "vocal_track_id": track_id,
                    "bed_track_id": "/music/bed.mp3",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "keep the instrumental bed"):
            plan_mix_build._validate_vocals_only_playback(no_keep, {})

    def test_14_staleness_detects_note_transition_and_pure_order_changes(self):
        meta = self._plan()
        paths = plan_paths.resolve(meta.slug)
        paths.mix_plan.write_text(json.dumps(plan_mix_envelope.decorate({"version": 2, "events": []}, meta.slug, paths)))
        self.assertFalse(plan_staleness.is_stale(meta.slug)["stale"])
        for path in (paths.notes, paths.transitions, paths.playlist):
            original = json.loads(path.read_text())
            changed = ({**original, "changed": path.name} if isinstance(original, dict) else list(reversed(original)))
            if changed == original:
                changed = original + [{"track_id": "changed"}]
            plan_revision.write_checked(path, changed, plan_revision.file_rev(path))
            status = plan_staleness.is_stale(meta.slug)
            self.assertTrue(status["stale"])
            self.assertIn(path.stem if path.stem != "playlist" else "playlist", status["changed_inputs"])
            paths.mix_plan.write_text(json.dumps(plan_mix_envelope.decorate({"version": 2, "events": []}, meta.slug, paths)))

    def test_15_migration_is_idempotent_dry_run_safe_and_non_destructive(self):
        legacy = plan_paths.legacy_paths()
        legacy.selection.parent.mkdir(parents=True, exist_ok=True)
        legacy.selection.write_text(json.dumps({"track_ids": ["a"]}))
        legacy.playlist.write_text(json.dumps([{"track_id": "a"}]))
        before = legacy.selection.read_bytes()
        dry = plan_migration.migrate(dry_run=True)
        self.assertEqual(dry["status"], "planned")
        self.assertFalse(self.plans.exists())
        first = plan_migration.migrate()
        second = plan_migration.migrate()
        self.assertEqual((first["status"], second["status"]), ("migrated", "already_migrated"))
        self.assertEqual(legacy.selection.read_bytes(), before)
        self.assertTrue(plan_paths.resolve().selection.exists())
