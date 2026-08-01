"""Structural ordered-group constraints for mix ordering."""
from __future__ import annotations

from dataclasses import replace

from brain import bunch_store, plan_bunch_activation
from brain.plan_types import OrderConstraints


class ConstraintViolation(ValueError):
    pass


def from_activations(slug: str) -> OrderConstraints:
    groups, regions, notes = [], [], []
    for item in plan_bunch_activation.list_active(slug):
        try:
            bunch = bunch_store.get(item["bunch_id"])
        except KeyError:
            continue
        members = tuple(item.get("track_ids") or bunch.track_ids)
        if bunch.archived or len(members) < 2:
            continue
        groups.append(members)
        if item.get("region"):
            regions.append({"ids": list(members), "where": item["region"]})
        notes.append(f"active bunch: {bunch.label}")
    return OrderConstraints(groups=tuple(groups), regions=tuple(regions), notes=tuple(notes))


def merge_groups(pairs: list[tuple[str, str]]) -> list[list[str]]:
    groups: list[list[str]] = []
    for left, right in pairs:
        matches = [g for g in groups if left in g or right in g]
        if not matches:
            groups.append([left, right])
            continue
        merged = []
        for group in matches:
            for value in group:
                if value not in merged:
                    merged.append(value)
            groups.remove(group)
        for value in (left, right):
            if value not in merged:
                merged.append(value)
        groups.append(merged)
    return groups


def contract(rows: list[dict], groups: list[list[str]]) -> tuple[list[dict], dict]:
    by_id = {row["track_id"]: row for row in rows}
    claimed: set[str] = set()
    table = {}
    replacements = {}
    for index, group in enumerate(groups):
        present = [track_id for track_id in group if track_id in by_id]
        if len(present) < 2:
            continue
        overlap = claimed.intersection(present)
        if overlap:
            raise ConstraintViolation(f"overlapping groups: {sorted(overlap)}")
        claimed.update(present)
        pseudo = f"__bunch__{index}"
        head, tail = by_id[present[0]], by_id[present[-1]]
        row = dict(head)
        row["track_id"] = pseudo
        row["_bunch_entry"] = head
        row["_bunch_exit"] = tail
        table[pseudo] = present
        replacements[present[0]] = row
    result = []
    for row in rows:
        track_id = row["track_id"]
        if track_id in replacements:
            result.append(replacements[track_id])
        elif track_id not in claimed:
            result.append(row)
    return result, table


def expand(order: list[str], table: dict) -> list[str]:
    result = []
    for track_id in order:
        if track_id.startswith("__bunch__") and track_id not in table:
            raise ConstraintViolation(f"unknown pseudo id: {track_id}")
        result.extend(table.get(track_id, [track_id]))
    return result


def assert_intact(order: list[str], groups) -> None:
    if len(order) != len(set(order)):
        raise ConstraintViolation("order contains duplicate tracks")
    for group in groups:
        present = [item for item in group if item in order]
        if len(present) < 2:
            continue
        start = order.index(present[0])
        if order[start:start + len(present)] != present:
            raise ConstraintViolation(f"ordered bunch is not intact: {present}")
