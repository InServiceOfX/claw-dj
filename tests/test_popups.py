"""brain.popups: pop-up cards (agent facts + authors' commentary marked with their initials)."""
import json
import tempfile
import unittest
from pathlib import Path

from brain.popups import (
    Card,
    Scheduler,
    Segment,
    card_lines,
    drawtext_filters,
    is_relevant,
    load_commentary,
    load_facts,
    parse_cue_sheet,
    snippets,
    timeline,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


FACTS = [
    {"id": "joe-1", "text": "Joe is from Columbus, Georgia.", "artists": ["Joe"], "source": "Wikipedia: Joe (singer)", "verified": True},
    {"id": "mya-1", "text": "Mya trained as a tap dancer.", "artists": ["Mýa"], "source": "Wikipedia: Mýa", "verified": False},
    {"id": "ross-im", "text": "I'm Coming Out was written by Nile Rodgers and Bernard Edwards.", "artists": ["Diana Ross"],
     "titles": ["I'm Coming Out"], "source": "Wikipedia: I'm Coming Out", "verified": True},
    {"id": "gen-1", "text": "General fact one.", "artists": [], "source": "Wikipedia: Rhythm and blues", "verified": True},
    {"id": "gen-2", "text": "General fact two.", "artists": [], "source": "Wikipedia: Hip hop music", "verified": True},
]


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.facts_path = write(self.root / "facts.json", json.dumps(FACTS))
        self.com = self.root / "commentary"
        write(self.com / "ernest-yeung" / "author.json", json.dumps({"name": "Ernest Yeung", "initials": "EY"}))
        write(self.com / "ernest-yeung" / "sampling.md",
              "---\ntitle: On sampling\ntags: [Diana Ross, sampling, 90s]\n---\n\n# On sampling\n\n"
              "This paragraph is ignored because the file has pull quotes.\n\n"
              "> Sampling is a conversation across decades. A beat is a letter to the past.\n"
              "> The best flips answer the original.\n\nMore prose.\n")
        write(self.com / "ernest-yeung" / "rnb.md",
              "---\ntags: Joe, R&B\n---\n\nFirst R&B thought. Second R&B thought.\n\nAnother passage here.\n")
        write(self.com / "ernest-yeung" / "_template.md", "> never shown\n")
        write(self.com / "ernest-yeung" / "README.md", "> never shown either\n")
        write(self.com / "ernest-yeung" / "distilled.md",
              "---\ntags: [Joe]\n---\n\n- Joe kept R&B grown and sincere.\n- Untagged-feeling distillation.\n")
        write(self.com / "jane-doe" / "notes.md", "Jane's untagged thought.\n")

    def facts(self):
        return load_facts(self.facts_path)

    def threads(self):
        return load_commentary(self.com)


class LoadingTests(Fixture):
    def test_facts_have_no_initials_and_require_a_source(self) -> None:
        facts = self.facts()
        self.assertEqual({c.kind for c in facts}, {"fact"})
        self.assertTrue(all(c.initials is None for c in facts))
        bad = write(self.root / "bad.json", json.dumps([{"id": "x", "text": "No source here.", "artists": []}]))
        with self.assertRaises(ValueError):
            load_facts(bad)

    def test_commentary_always_carries_the_authors_initials(self) -> None:
        cards = [c for t in self.threads() for c in t]
        self.assertTrue(cards)
        for c in cards:
            self.assertIn(c.kind, ("quote", "distilled"))
            self.assertIsNotNone(c.initials)
        by_author = {c.author: c.initials for c in cards}
        self.assertEqual(by_author["Ernest Yeung"], "EY")
        self.assertEqual(by_author["Jane Doe"], "JD")          # initials from the folder name

    def test_templates_and_readme_never_load(self) -> None:
        texts = " ".join(c.text for t in self.threads() for c in t)
        self.assertNotIn("never shown", texts)

    def test_pull_quotes_take_precedence_and_keep_tags(self) -> None:
        sampling = [t for t in self.threads() if t[0].id.startswith("ernest-yeung/sampling")]
        self.assertEqual(len(sampling), 1)
        joined = " ".join(c.text for c in sampling[0])
        self.assertIn("conversation across decades", joined)
        self.assertNotIn("ignored", joined)
        self.assertNotIn("More prose", joined)
        self.assertIn("Diana Ross", sampling[0][0].tags)

    def test_paragraph_threads_and_distilled_bullets(self) -> None:
        rnb = [t for t in self.threads() if t[0].id.startswith("ernest-yeung/rnb")]
        self.assertEqual(len(rnb), 2)
        distilled = [c for t in self.threads() for c in t if c.kind == "distilled"]
        self.assertEqual(len(distilled), 2)
        self.assertEqual(distilled[0].text, "Joe kept R&B grown and sincere.")
        self.assertIn("Joe", distilled[0].tags)

    def test_long_passages_become_numbered_progressions(self) -> None:
        long = " ".join(f"Sentence number {i} is part of a long passage about music." for i in range(12))
        write(self.com / "ernest-yeung" / "long.md", long + "\n")
        thread = next(t for t in self.threads() if t[0].id.startswith("ernest-yeung/long"))
        self.assertGreater(len(thread), 1)
        self.assertEqual([c.part for c in thread], [(i + 1, len(thread)) for i in range(len(thread))])


class SnippetTests(unittest.TestCase):
    def test_snippets_fit_keep_order_and_lose_nothing(self) -> None:
        text = ("Short one. " * 5) + ("averyveryverylongwordthatgoeson " * 12) + "End."
        parts = snippets(text, max_chars=60)
        self.assertTrue(all(0 < len(p) <= 60 for p in parts))
        self.assertEqual(" ".join(" ".join(parts).split()), " ".join(text.split()))


class RelevanceTests(Fixture):
    def test_features_accents_and_titles(self) -> None:
        f = {c.id: c for c in self.facts()}
        self.assertTrue(is_relevant(f["joe-1"], "Joe Featuring Mariah Carey & Nas", "Love"))
        self.assertTrue(is_relevant(f["mya-1"], "Mya f/ Raekwon and Noreaga", "Ghetto Supastar"))
        self.assertTrue(is_relevant(f["mya-1"], "Mýa; Jadakiss", "x"))
        self.assertFalse(is_relevant(f["joe-1"], "Joey Bada$$", "x"))
        self.assertTrue(is_relevant(f["ross-im"], "Diana Ross & The Supremes", "I'm Coming Out"))
        self.assertFalse(is_relevant(f["ross-im"], "Diana Ross", "Upside Down"))
        self.assertFalse(is_relevant(f["gen-1"], "Joe", "x"))     # general facts are fallbacks

    def test_commentary_relevance_by_tag(self) -> None:
        sampling = next(t for t in self.threads() if t[0].id.startswith("ernest-yeung/sampling"))
        self.assertTrue(is_relevant(sampling[0], "Diana Ross", "I'm Coming Out"))
        self.assertFalse(is_relevant(sampling[0], "Joe", "x"))


class SchedulerTests(Fixture):
    def test_cadence_prefers_relevant_and_marks_commentary(self) -> None:
        s = Scheduler(self.facts(), self.threads(), commentary_every=3, seed=1)
        cards = [s.next_card("Joe", "All the Things") for _ in range(6)]
        kinds = ["commentary" if c.initials else "fact" for c in cards]
        self.assertEqual(kinds, ["fact", "fact", "commentary", "fact", "fact", "commentary"])
        self.assertEqual(cards[0].id, "joe-1")                   # relevant fact first
        self.assertTrue(is_relevant(cards[2], "Joe", "All the Things"))
        for c in cards:
            self.assertEqual(c.initials is None, c.kind == "fact")

    def test_threads_continue_in_order(self) -> None:
        long = " ".join(f"Point {i} of my argument about rhythm and blues history." for i in range(10))
        write(self.com / "ernest-yeung" / "long.md", "---\ntags: [Usher]\n---\n\n" + long + "\n")
        s = Scheduler([], self.threads(), commentary_every=1, seed=0)
        parts = [s.next_card("Usher", "x").part for _ in range(3)]
        self.assertEqual([p[0] for p in parts], [1, 2, 3])

    def test_no_repeats_until_rotation_and_verified_only(self) -> None:
        s = Scheduler(self.facts(), [], seed=3)
        ids = [s.next_card(None, None).id for _ in range(len(FACTS))]
        self.assertEqual(len(set(ids)), len(FACTS))
        v = Scheduler(self.facts(), [], verified_only=True, seed=3)
        self.assertNotIn("mya-1", [v.next_card("Mýa", "x").id for _ in range(10)])

    def test_tick_respects_interval_and_rejects_bad_timing(self) -> None:
        s = Scheduler(self.facts(), [], interval_s=60, show_s=10)
        self.assertIsNotNone(s.tick(0.0, "Joe", "x"))
        self.assertIsNone(s.tick(30.0, "Joe", "x"))
        self.assertIsNotNone(s.tick(61.0, "Joe", "x"))
        with self.assertRaises(ValueError):
            Scheduler([], [], interval_s=5, show_s=10)

    def test_same_seed_same_sequence(self) -> None:
        a = Scheduler(self.facts(), self.threads(), seed=7)
        b = Scheduler(self.facts(), self.threads(), seed=7)
        self.assertEqual([a.next_card("Joe", "x").id for _ in range(8)], [b.next_card("Joe", "x").id for _ in range(8)])


class VideoTests(Fixture):
    CUE = ('FILE "mix.wav" WAVE\n  TRACK 01 AUDIO\n    TITLE "I\'m Coming Out"\n    PERFORMER "Diana Ross"\n    INDEX 01 00:00:45\n'
           '  TRACK 02 AUDIO\n    TITLE "Mo Money Mo Problems"\n    PERFORMER "The Notorious B.I.G."\n    INDEX 01 03:08:27\n')

    def test_cue_sheet_segments(self) -> None:
        segs = parse_cue_sheet(write(self.root / "mix.cue", self.CUE), duration_s=400.0)
        self.assertEqual([s.title for s in segs], ["I'm Coming Out", "Mo Money Mo Problems"])
        self.assertAlmostEqual(segs[0].start, 0.6)
        self.assertAlmostEqual(segs[1].start, 188.36)
        self.assertAlmostEqual(segs[0].end, segs[1].start)
        self.assertEqual(segs[1].end, 400.0)

    def test_timeline_cards_stay_inside_songs_without_overlap(self) -> None:
        segs = [Segment(0.0, 100.0, "Diana Ross", "I'm Coming Out"), Segment(100.0, 130.0, "Joe", "x")]
        s = Scheduler(self.facts(), self.threads(), interval_s=30, show_s=12)
        items = timeline(segs, s, first_offset_s=5)
        self.assertTrue(items)
        for it in items:
            seg = next(g for g in segs if g.start <= it["start"] < g.end)
            self.assertLessEqual(it["end"], seg.end - 1.0 + 1e-9)
            self.assertAlmostEqual(it["end"] - it["start"], 12.0)
        for a, b in zip(items, items[1:]):
            self.assertLessEqual(a["end"], b["start"])
        self.assertEqual(items[0]["card"].id, "ross-im")         # relevant to the song playing

    def test_card_lines_attribution(self) -> None:
        fact = Card("f", "A plain fact about a record.", "fact", source="Wikipedia: X")
        quote = Card("q", "Sampling is a conversation.", "quote", initials="EY", author="Ernest Yeung", part=(1, 2))
        dist = Card("d", "Joe kept R&B grown.", "distilled", initials="EY", author="Ernest Yeung")
        self.assertFalse(any("EY" in l for l in card_lines(fact)))
        q = card_lines(quote)
        self.assertTrue(q[0].startswith("“") and "”" in q[-3] + q[-2] + q[-1])
        self.assertIn("— EY", q[-1])
        self.assertIn("1/2", " ".join(q))
        self.assertIn("in brief", " ".join(card_lines(dist)))
        self.assertNotIn("“", card_lines(dist)[0])        # a distillation is never shown as a quote

    def test_drawtext_filters_write_text_files(self) -> None:
        items = [{"start": 5.0, "end": 17.0, "card": Card("q", "Hello: world, it's 'quoted'.", "quote", initials="EY")}]
        out = self.root / "txt"
        f = drawtext_filters(items, out, "/fonts/x.ttf")
        self.assertIn("between(t,5.000,17.000)", f)
        self.assertIn("textfile=", f)
        files = list(out.glob("*.txt"))
        self.assertEqual(len(files), 1)
        self.assertIn("— EY", files[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
