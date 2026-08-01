"""Offline harness-facing CLI for multi-plan workspaces."""
from __future__ import annotations

import argparse
import json
import sys

from brain import plan_journal, plan_mix_build, plan_paths, plan_staleness, plan_store, transition_overrides
from brain.api import api_bunch_item, api_bunches_collection, api_plan_bunches, api_plan_notes, api_plan_order, api_plan_tracks, api_plan_transitions
from brain.api.common import ApiError, meta_dict, rev, snapshot
from brain.plan_revision import StalePlanError


class _App:
    mix_state = {"running": 0}


def _active(args):
    if getattr(args, "plan", None):
        return args.plan
    meta = plan_store.get_active()
    if meta is None:
        raise ApiError(404, "active_plan_not_found", "no active plan")
    return meta.slug


def _base(args, slug):
    value = getattr(args, "base_rev", None)
    if value:
        return value
    if getattr(args, "force", False):
        return rev(slug)
    raise ApiError(400, "base_rev_required", "--base-rev or --force is required")


def _call(module, slug, body, method="POST", params=None):
    handler_params = params or {"slug": slug}
    result = module.handle(_App(), handler_params, method, body, {})
    return result[0]


def cmd_list(args):
    status = args.status
    metas = plan_store.list(status=status) if status else [item for item in plan_store.list() if item.status.value != "archived"]
    return {"plans": [meta_dict(item) for item in metas]}


def cmd_new(args):
    meta = plan_store.create(args.display_name)
    if args.activate:
        plan_store.set_active(meta.slug)
    return meta_dict(meta)


def cmd_switch(args):
    return meta_dict(plan_store.set_active(args.slug))


def cmd_show(args):
    return snapshot(_active(args))


def cmd_tracks(args):
    slug = _active(args)
    key = "add" if args.command == "add" else "remove"
    return _call(api_plan_tracks, slug, {key: args.track_ids, "base_rev": _base(args, slug)})


def cmd_move(args):
    slug = _active(args)
    body = {"base_rev": _base(args, slug)}
    if args.bunch:
        body.update(move_bunch=args.bunch, to_index=args.to_index)
    else:
        current = [row["track_id"] for row in snapshot(slug)["tracks"]]
        if args.track not in current:
            raise ApiError(404, "track_not_found", f"track not found: {args.track}")
        current.remove(args.track)
        current.insert(max(0, min(args.to_index, len(current))), args.track)
        body["track_ids"] = current
    return _call(api_plan_order, slug, body)


def cmd_note(args):
    slug = _active(args)
    return _call(api_plan_notes, slug, {"track_id": args.track_id, "note": args.text, "clear": args.clear, "author": args.author, "base_rev": _base(args, slug)})


def cmd_transition(args):
    slug = _active(args)
    if args.transition_command == "get":
        item = next((item for item in transition_overrides.load(slug) if (item.from_track_id, item.to_track_id) == (args.from_id, args.to_id)), None)
        return {"segment": None if item is None else api_plan_transitions._segment(slug, args.from_id, args.to_id), "rev": rev(slug)}
    body = {"from_track_id": args.from_id, "to_track_id": args.to_id, "base_rev": _base(args, slug), "clear": args.transition_command == "clear"}
    if args.transition_command == "set":
        for name in ("technique", "beats", "showcase_move", "note", "author"):
            value = getattr(args, name)
            if value is not None:
                body[name] = value
        if args.effects is not None:
            body["effects"] = json.loads(args.effects)
    return _call(api_plan_transitions, slug, body)


def cmd_mark(args):
    slug = _active(args)
    from brain.api import api_plan_detail
    return _call(api_plan_detail, slug, {"status": args.status_value, "base_rev": _base(args, slug)})


def cmd_bunch(args):
    if args.bunch_command == "list":
        return api_bunches_collection.handle(_App(), {}, "GET", {}, {})[0]
    if args.bunch_command == "new":
        created = api_bunches_collection.handle(_App(), {}, "POST", {"label": args.label, "track_ids": args.tracks, "ordered": args.ordered}, {})[0]
        if args.activate:
            slug = _active(args)
            activation = _call(api_plan_bunches, slug, {"bunch_id": created["bunch_id"], "enabled": True, "base_rev": _base(args, slug)})
            created["activation"] = activation
        return created
    if args.bunch_command == "archive":
        return api_bunch_item.handle(_App(), {"bunch_id": args.bunch_id}, "POST", {"action": "archive"}, {})[0]
    slug = _active(args)
    return _call(api_plan_bunches, slug, {"bunch_id": args.bunch_id, "enabled": args.bunch_command == "activate", "base_rev": _base(args, slug)})


def cmd_build(args):
    slug = _active(args)
    return plan_mix_build.build(slug, profile=args.profile, dj_format=args.dj_format)


def cmd_log(args):
    slug = _active(args)
    return {"entries": plan_journal.read(slug, args.limit, actor=args.actor, author=args.author)}


def cmd_status(args):
    slug = _active(args)
    return {"slug": slug, **plan_staleness.is_stale(slug), "rev": rev(slug)}


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    item = commands.add_parser("list"); item.add_argument("--status", choices=("wip", "ready", "archived")); item.add_argument("--json", action="store_true"); item.set_defaults(func=cmd_list)
    item = commands.add_parser("new"); item.add_argument("display_name"); item.add_argument("--activate", action="store_true"); item.set_defaults(func=cmd_new)
    item = commands.add_parser("switch"); item.add_argument("slug"); item.set_defaults(func=cmd_switch)
    item = commands.add_parser("show"); _plan_json(item); item.set_defaults(func=cmd_show)
    for name in ("add", "remove"):
        item = commands.add_parser(name); item.add_argument("track_ids", nargs="+"); _mutation(item); item.set_defaults(func=cmd_tracks)
    item = commands.add_parser("move"); item.add_argument("--track"); item.add_argument("--bunch"); item.add_argument("--to-index", type=int, required=True); _mutation(item); item.set_defaults(func=cmd_move)
    item = commands.add_parser("note"); item.add_argument("track_id"); item.add_argument("text", nargs="?", default=""); item.add_argument("--author", choices=("human", "agent", "llm"), default="human"); item.add_argument("--clear", action="store_true"); _mutation(item); item.set_defaults(func=cmd_note)
    item = commands.add_parser("transition"); nested = item.add_subparsers(dest="transition_command", required=True)
    for name in ("get", "set", "clear"):
        sub = nested.add_parser(name); sub.add_argument("--from", dest="from_id", required=True); sub.add_argument("--to", dest="to_id", required=True); sub.add_argument("--plan")
        if name != "get": sub.add_argument("--base-rev"); sub.add_argument("--force", action="store_true")
        if name == "set":
            sub.add_argument("--technique"); sub.add_argument("--beats", type=int); sub.add_argument("--showcase-move", dest="showcase_move"); sub.add_argument("--effects"); sub.add_argument("--note"); sub.add_argument("--author", choices=("human", "agent", "llm"), default="human")
        sub.set_defaults(func=cmd_transition)
    item = commands.add_parser("mark"); item.add_argument("status_value", choices=("wip", "ready", "archived")); _mutation(item); item.set_defaults(func=cmd_mark)
    item = commands.add_parser("bunch"); nested = item.add_subparsers(dest="bunch_command", required=True)
    sub = nested.add_parser("list"); sub.set_defaults(func=cmd_bunch)
    sub = nested.add_parser("new"); sub.add_argument("--label", required=True); sub.add_argument("--tracks", nargs="+", required=True); sub.add_argument("--ordered", action=argparse.BooleanOptionalAction, default=True); sub.add_argument("--activate", action="store_true"); _mutation(sub); sub.set_defaults(func=cmd_bunch)
    for name in ("activate", "deactivate"):
        sub = nested.add_parser(name); sub.add_argument("--bunch-id", required=True); _mutation(sub); sub.set_defaults(func=cmd_bunch)
    sub = nested.add_parser("archive"); sub.add_argument("--bunch-id", required=True); sub.set_defaults(func=cmd_bunch)
    item = commands.add_parser("build"); item.add_argument("--plan"); item.add_argument("--profile", default="dj-showcase"); item.add_argument("--dj-format", default="none"); item.set_defaults(func=cmd_build)
    item = commands.add_parser("log"); item.add_argument("--plan"); item.add_argument("--limit", type=int, default=50); item.add_argument("--actor"); item.add_argument("--author"); item.set_defaults(func=cmd_log)
    item = commands.add_parser("status"); _plan_json(item); item.set_defaults(func=cmd_status)
    return root


def _mutation(item):
    item.add_argument("--plan"); item.add_argument("--base-rev"); item.add_argument("--force", action="store_true")


def _plan_json(item):
    item.add_argument("--plan"); item.add_argument("--json", action="store_true")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        payload = args.func(args)
    except ApiError as error:
        print(json.dumps(error.payload), file=sys.stderr)
        return 1
    except StalePlanError as error:
        print(json.dumps({"error": "stale_plan", **error.payload()}), file=sys.stderr)
        return 1
    except (ValueError, KeyError, plan_paths.PlanNotFound) as error:
        print(json.dumps({"error": "invalid_request", "message": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
