"""Tests for hands.clip — vertical short-form clip generation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hands.clip import (
    ClipConfig,
    TransitionData,
    create_synthetic_transition,
    generate_sidecar,
    load_transition_from_plan,
    render_same_beat_frame,
    render_watch_ai_frame,
    _wrap_text,
    _load_font,
    generate_clip,
    verify_output,
)

from PIL import Image, ImageDraw


class TestTransitionData(unittest.TestCase):
    def test_create_synthetic_transition(self):
        t = create_synthetic_transition()
        self.assertEqual(t.index, 1)
        self.assertEqual(t.from_artist, "Demo Artist A")
        self.assertEqual(t.to_artist, "Demo Artist B")
        self.assertEqual(t.technique, "standard_blend")
        self.assertEqual(t.transition_beats, 16)
        self.assertGreater(t.from_bpm, 0)
        self.assertGreater(t.to_bpm, 0)

    def test_load_transition_from_plan(self):
        plan = {
            "events": [
                {
                    "op": "load",
                    "deck": 1,
                    "track_id": "/music/track_a.mp3",
                    "artist": "Artist A",
                    "title": "Song A",
                    "bpm": 95.0,
                    "cue_seconds": 10.0,
                },
                {
                    "op": "load",
                    "deck": 2,
                    "track_id": "/music/track_b.mp3",
                    "artist": "Artist B",
                    "title": "Song B",
                    "bpm": 98.0,
                    "cue_seconds": 0.0,
                },
                {"op": "start", "deck": 1},
                {"op": "play_body", "deck": 1, "beats": 64, "track": "Artist A — Song A"},
                {
                    "op": "transition",
                    "from_deck": 1,
                    "to_deck": 2,
                    "from_track": "Artist A — Song A",
                    "to_track": "Artist B — Song B",
                    "technique": "standard_blend",
                    "transition_beats": 16,
                    "moves": ["sync", "crossfade"],
                },
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(plan, f)
            plan_path = Path(f.name)
        
        try:
            t = load_transition_from_plan(plan_path, 1)
            self.assertEqual(t.index, 1)
            self.assertEqual(t.from_artist, "Artist A")
            self.assertEqual(t.from_title, "Song A")
            self.assertEqual(t.to_artist, "Artist B")
            self.assertEqual(t.to_title, "Song B")
            self.assertEqual(t.technique, "standard_blend")
            self.assertEqual(t.transition_beats, 16)
            self.assertEqual(t.from_bpm, 95.0)
            self.assertEqual(t.to_bpm, 98.0)
            self.assertEqual(t.ride_beats, 64)
        finally:
            plan_path.unlink()

    def test_load_transition_index_out_of_range(self):
        plan = {"events": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(plan, f)
            plan_path = Path(f.name)
        
        try:
            with self.assertRaises(ValueError) as ctx:
                load_transition_from_plan(plan_path, 1)
            self.assertIn("No transitions", str(ctx.exception))
        finally:
            plan_path.unlink()


class TestSidecarGeneration(unittest.TestCase):
    def test_generate_sidecar_same_beat(self):
        t = create_synthetic_transition()
        config = ClipConfig(
            template="same_beat",
            duration=20.0,
            output_path="/tmp/test.mp4",
            seed=42,
        )
        sidecar = generate_sidecar(t, config, Path("/tmp/test.mp4"))
        
        self.assertIn("suggested_title", sidecar)
        self.assertIn("suggested_caption", sidecar)
        self.assertIn("suggested_hashtags", sidecar)
        self.assertIn("copyright_notice", sidecar)
        self.assertEqual(sidecar["template"], "same_beat")
        self.assertEqual(sidecar["transition_index"], 1)
        self.assertIsInstance(sidecar["suggested_hashtags"], list)
        self.assertGreater(len(sidecar["suggested_hashtags"]), 0)

    def test_generate_sidecar_watch_ai_mix(self):
        t = create_synthetic_transition()
        config = ClipConfig(
            template="watch_ai_mix",
            duration=25.0,
            output_path="/tmp/test.mp4",
            seed=123,
        )
        sidecar = generate_sidecar(t, config, Path("/tmp/test.mp4"))
        
        self.assertEqual(sidecar["template"], "watch_ai_mix")
        self.assertIn("#AIDJ", sidecar["suggested_hashtags"])

    def test_sidecar_variation_with_seed(self):
        t = create_synthetic_transition()
        config1 = ClipConfig(template="same_beat", output_path="/tmp/test.mp4", seed=1)
        config2 = ClipConfig(template="same_beat", output_path="/tmp/test.mp4", seed=2)
        
        sidecar1 = generate_sidecar(t, config1, Path("/tmp/test.mp4"))
        sidecar2 = generate_sidecar(t, config2, Path("/tmp/test.mp4"))
        
        self.assertNotEqual(
            sidecar1["suggested_title"],
            sidecar2["suggested_title"],
            "Different seeds should produce different titles"
        )


class TestTextWrapping(unittest.TestCase):
    def test_wrap_text_short(self):
        font = _load_font(32)
        lines = _wrap_text("Hello world", font, 1000)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "Hello world")

    def test_wrap_text_long(self):
        font = _load_font(32)
        text = "This is a very long text that should definitely wrap to multiple lines when given a narrow width"
        lines = _wrap_text(text, font, 200)
        self.assertGreater(len(lines), 1)

    def test_wrap_text_empty(self):
        font = _load_font(32)
        lines = _wrap_text("", font, 1000)
        self.assertEqual(lines, [""])


class TestFrameRendering(unittest.TestCase):
    def test_render_same_beat_frame_no_crash(self):
        t = create_synthetic_transition()
        config = ClipConfig(template="same_beat", output_path="/tmp/test.mp4")
        
        img = Image.new("RGB", (1080, 1920), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        render_same_beat_frame(draw, 0, 600, t, config)
        render_same_beat_frame(draw, 300, 600, t, config)
        render_same_beat_frame(draw, 599, 600, t, config)

    def test_render_watch_ai_frame_no_crash(self):
        t = create_synthetic_transition()
        config = ClipConfig(template="watch_ai_mix", output_path="/tmp/test.mp4")
        
        img = Image.new("RGB", (1080, 1920), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        render_watch_ai_frame(draw, 0, 600, t, config)
        render_watch_ai_frame(draw, 300, 600, t, config)
        render_watch_ai_frame(draw, 599, 600, t, config)

    def test_render_end_card(self):
        t = create_synthetic_transition()
        config = ClipConfig(template="same_beat", duration=20.0, output_path="/tmp/test.mp4")
        
        img = Image.new("RGB", (1080, 1920), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        total_frames = int(20.0 * 30)
        end_card_frame = total_frames - 10
        render_same_beat_frame(draw, end_card_frame, total_frames, t, config)


@unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg not available")
class TestClipGeneration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_clip_")
        self.output_path = Path(self.tmpdir) / "test_clip.mp4"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_generate_clip_same_beat(self):
        t = create_synthetic_transition()
        config = ClipConfig(
            template="same_beat",
            duration=5.0,
            output_path=str(self.output_path),
            seed=42,
        )
        
        output, sidecar = generate_clip(t, config)
        
        self.assertTrue(output.exists())
        self.assertTrue(output.with_suffix(".json").exists())
        self.assertGreater(output.stat().st_size, 0)

    def test_generate_clip_watch_ai_mix(self):
        t = create_synthetic_transition()
        config = ClipConfig(
            template="watch_ai_mix",
            duration=5.0,
            output_path=str(self.output_path),
            seed=42,
        )
        
        output, sidecar = generate_clip(t, config)
        
        self.assertTrue(output.exists())

    def test_verify_output_dimensions(self):
        t = create_synthetic_transition()
        config = ClipConfig(
            template="same_beat",
            duration=3.0,
            output_path=str(self.output_path),
        )
        
        output, _ = generate_clip(t, config)
        verification = verify_output(output, config.duration)
        
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["video"]["width"], 1080)
        self.assertEqual(verification["video"]["height"], 1920)
        self.assertEqual(verification["video"]["codec_name"], "h264")
        self.assertEqual(verification["audio"]["codec_name"], "aac")


@unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg not available")
class TestClipWithSyntheticAudio(unittest.TestCase):
    """Test clip generation with a synthetic audio fixture."""
    
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_clip_audio_")
        self.output_path = Path(self.tmpdir) / "test_clip.mp4"
        self.audio_path = Path(self.tmpdir) / "test_audio.wav"
        self._create_synthetic_audio()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_synthetic_audio(self):
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=10",
            "-ar", "48000",
            "-ac", "2",
            str(self.audio_path),
        ], check=True)

    def test_generate_clip_with_audio(self):
        t = create_synthetic_transition()
        config = ClipConfig(
            template="same_beat",
            duration=5.0,
            start_offset=2.0,
            output_path=str(self.output_path),
        )
        
        output, sidecar = generate_clip(t, config, audio_path=self.audio_path)
        
        self.assertTrue(output.exists())
        verification = verify_output(output, config.duration)
        self.assertTrue(verification["verified"])
        self.assertIn("audio", verification)
        self.assertEqual(verification["audio"]["codec_name"], "aac")


class TestCLIIntegration(unittest.TestCase):
    """Test CLI entry points."""
    
    def test_clip_module_main_help(self):
        from hands import clip
        with self.assertRaises(SystemExit) as ctx:
            clip.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    @unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg not available")
    def test_clip_module_main_synthetic(self):
        from hands import clip
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.mp4"
            result = clip.main([
                "--synthetic",
                "--template", "same_beat",
                "--duration", "3",
                "--output", str(output),
            ])
            self.assertEqual(result, 0)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
