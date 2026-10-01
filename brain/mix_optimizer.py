"""Whole-set playback-order optimizer for Build mix plan.

The finalized set is an unordered pool. This module chooses the order that
blends best across the whole set, using the same pairwise compatibility graph
as `brain.mix_graph.pair_score` (BPM, key, sample lineage, genre, chroma,
same-artist) plus two things the old nearest-neighbor tour ignored:

* **Backbeat verifiability.** A blend can only be snare-matched when both
  songs have a usable snare-parity read (`SNARE_CONFIDENCE_GATE`). Each blend
  touching a weak read costs a little; a blend where BOTH sides are weak (a
  fully blind blend) costs more, so weak-read songs are kept apart.
* **Whole-order search.** Multi-start greedy construction followed by 2-opt
  and segment-move local search over a directed objective, instead of one
  greedy pass that can strand bad pairs at the end.

The result depends only on the set's contents (ties break on track_id), never
on the order songs were enabled on the Curate page.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from brain.library import Track
from brain.mix_graph import CHROMA_MATCH, genre_of, pair_score, tempo_step

UNVERIFIED_EDGE_PENALTY = 0.06
BLIND_EDGE_PENALTY = 0.10
SLOWDOWN_PENALTY = 0.03
SLOWDOWN_STREAK_PENALTY = 0.35
ENERGY_UP_BONUS = 0.05
GENRE_JUMP_COOLDOWN_PENALTY = 0.30
MAX_CONSECUTIVE_SLOWDOWNS = 2
GENRE_JUMP_COOLDOWN = 4


@dataclass(frozen=True)
class EdgeReport:
    from_id: str
    to_id: str
    score: float  # pair_score, 0..1
    backbeat: str  # "verifiable" | "one_side_unverified" | "blind"
    tempo_gap: bool
    reasons: tuple[str, ...]


class MixGraph:
    """Precomputed directed edge weights for one set of tracks."""

    def __init__(
        self,
        tracks: list[Track],
        *,
        lineage: set[tuple[str, str]] | None = None,
        chroma: dict[tuple[str, str], float] | None = None,
        snare_confidence: dict[str, float] | None = None,
        gate: float = 0.15,
    ) -> None:
        self.tracks = sorted(tracks, key=lambda t: t.track_id)
        self.index = {t.track_id: i for i, t in enumerate(self.tracks)}
        self.lineage = lineage or set()
        self.chroma = chroma or {}
        conf = snare_confidence or {}
        self.weak = [float(conf.get(t.track_id) or 0.0) < gate for t in self.tracks]
        n = len(self.tracks)
        self.edges = [[None] * n for _ in range(n)]
        self.weight = [[0.0] * n for _ in range(n)]
        self.slow = [[False] * n for _ in range(n)]
        self.jump = [[False] * n for _ in range(n)]
        for i, a in enumerate(self.tracks):
            for j, b in enumerate(self.tracks):
                if i == j:
                    continue
                edge = pair_score(a, b, lineage=self.lineage, chroma=self.chroma)
                self.edges[i][j] = edge
                w = edge.score
                step = tempo_step(a.bpm, b.bpm)
                if step is not None:
                    if 1.0 <= step <= 1.06:
                        w += ENERGY_UP_BONUS
                    elif step < 0.98:
                        w -= SLOWDOWN_PENALTY
                        self.slow[i][j] = True
                if self.weak[i] and self.weak[j]:
                    w -= BLIND_EDGE_PENALTY
                elif self.weak[i] or self.weak[j]:
                    w -= UNVERIFIED_EDGE_PENALTY
                self.weight[i][j] = w
                self.jump[i][j] = self._unbacked_jump(a, b)

    def _unbacked_jump(self, a: Track, b: Track) -> bool:
        ga, gb = genre_of(a), genre_of(b)
        if not ga or not gb or ga == gb:
            return False
        pair = tuple(sorted((a.track_id, b.track_id)))
        if pair in self.lineage:
            return False
        sim = self.chroma.get(pair)
        return not (sim is not None and sim >= CHROMA_MATCH)

    def objective(self, order: list[int]) -> float:
        total = 0.0
        slow_streak = 0
        cooldown = 0
        for a, b in zip(order, order[1:]):
            total += self.weight[a][b]
            if self.slow[a][b]:
                slow_streak += 1
                if slow_streak > MAX_CONSECUTIVE_SLOWDOWNS:
                    total -= SLOWDOWN_STREAK_PENALTY
            else:
                slow_streak = 0
            if self.jump[a][b]:
                if cooldown > 0:
                    total -= GENRE_JUMP_COOLDOWN_PENALTY
                cooldown = GENRE_JUMP_COOLDOWN
            else:
                cooldown = max(0, cooldown - 1)
        return total

    def greedy_from(self, start: int) -> list[int]:
        n = len(self.tracks)
        order = [start]
        used = {start}
        while len(order) < n:
            current = order[-1]
            best = max(
                (j for j in range(n) if j not in used),
                key=lambda j: (self.weight[current][j], -j),
            )
            order.append(best)
            used.add(best)
        return order

    def report(self, order_ids: list[str]) -> list[EdgeReport]:
        out = []
        for a_id, b_id in zip(order_ids, order_ids[1:]):
            i, j = self.index[a_id], self.index[b_id]
            edge = self.edges[i][j]
            weak = (self.weak[i], self.weak[j])
            backbeat = "blind" if all(weak) else ("one_side_unverified" if any(weak) else "verifiable")
            a, b = self.tracks[i], self.tracks[j]
            step = tempo_step(a.bpm, b.bpm)
            tempo_gap = step is None or not (0.92 <= step <= 1.08)
            out.append(EdgeReport(a_id, b_id, round(edge.score, 3), backbeat, tempo_gap, edge.reasons))
        return out


def _two_opt(graph: MixGraph, order: list[int], *, fixed_first: bool, deadline: float) -> list[int]:
    best = order
    best_score = graph.objective(order)
    lo = 1 if fixed_first else 0
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        n = len(best)
        for i in range(lo, n - 1):
            for j in range(i + 2, n + 1):
                candidate = best[:i] + best[i:j][::-1] + best[j:]
                score = graph.objective(candidate)
                if score > best_score + 1e-9:
                    best, best_score, improved = candidate, score, True
            if time.monotonic() >= deadline:
                break
        # Or-opt: move a block of 1-3 songs elsewhere.
        for size in (1, 2, 3):
            for i in range(lo, n - size + 1):
                block = best[i:i + size]
                rest = best[:i] + best[i + size:]
                for k in range(lo, len(rest) + 1):
                    if k == i:
                        continue
                    candidate = rest[:k] + block + rest[k:]
                    score = graph.objective(candidate)
                    if score > best_score + 1e-9:
                        best, best_score, improved = candidate, score, True
                        break
                if time.monotonic() >= deadline:
                    break
    return best


def optimize_order(
    graph: MixGraph,
    *,
    opener_id: str | None = None,
    time_budget_s: float = 8.0,
    starts: int = 12,
) -> list[str]:
    """Best playback order (track ids) for the graph's set."""
    n = len(graph.tracks)
    if n <= 2:
        ids = [t.track_id for t in graph.tracks]
        if opener_id in ids:
            ids.remove(opener_id)
            ids.insert(0, opener_id)
        return ids
    deadline = time.monotonic() + time_budget_s
    if opener_id is not None and opener_id in graph.index:
        start_nodes = [graph.index[opener_id]]
    else:
        # Strongest-connected songs make the best seeds; deterministic.
        strength = sorted(
            range(n), key=lambda i: (-sum(graph.weight[i][j] + graph.weight[j][i] for j in range(n) if j != i), i)
        )
        start_nodes = strength[: max(1, min(starts, n))]
    candidates = [graph.greedy_from(s) for s in start_nodes]
    candidates.sort(key=lambda o: (-graph.objective(o), o))
    best = candidates[0]
    for seed in candidates[:3]:
        if time.monotonic() >= deadline:
            break
        improved = _two_opt(graph, seed, fixed_first=opener_id is not None, deadline=deadline)
        if graph.objective(improved) > graph.objective(best) + 1e-9:
            best = improved
    return [graph.tracks[i].track_id for i in best]


def order_summary(graph: MixGraph, order_ids: list[str]) -> dict:
    """Plain numbers for provenance and the Candidate playback order list."""
    edges = graph.report(order_ids)
    return {
        "mean_score": round(sum(e.score for e in edges) / max(1, len(edges)), 3),
        "weak_pairs": sum(1 for e in edges if e.score < 0.5),
        "tempo_gaps": sum(1 for e in edges if e.tempo_gap),
        "backbeat_verifiable": sum(1 for e in edges if e.backbeat == "verifiable"),
        "backbeat_unverified": sum(1 for e in edges if e.backbeat != "verifiable"),
        "backbeat_blind": sum(1 for e in edges if e.backbeat == "blind"),
        "objective": round(graph.objective([graph.index[i] for i in order_ids]), 3),
    }
