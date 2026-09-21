"""Shared preflight for native performance and optional offline export (stdlib only)."""
from pathlib import Path
import hashlib
from shared.performance import source_paths


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def check_sources(p, source_map=None):
    paths=source_paths(p,source_map)
    for tid,expected in p.get('source_sha256',{}).items():
        if tid not in paths or sha(paths[tid])!=expected:
            raise ValueError(f'Source changed since analysis: {tid}')
    return paths


def current_limits(plan):
    """Recheck global hard notes as well as the explicit portable constraints."""
    import re
    from hands.source_cutoffs import library_notes
    ids={c['track_id'] for c in plan['performance']['clips']}
    if plan['performance'].get('loop'):ids.add(plan['performance']['loop']['track_id'])
    result={}
    for tid,note in library_notes(ids).items():
        def value(key):
            matches=re.findall(r'\b'+key+r'\s*=\s*(\d+(?:\.\d+)?)',note,re.I)
            return float(matches[-1]) if matches else None
        rule={}
        for key,target in [('mandatory_start_seconds','min'),('mandatory_end_seconds','max')]:
            v=value(key)
            if v is not None:rule[target]=v
        a,b=value('skip_from_seconds'),value('skip_to_seconds')
        if re.search(r'\bmandatory_skip\b',note,re.I) and a is not None and b is not None:
            rule['exclude']=[[a,b]]
        result[tid]=rule
    return result


def validate_current(plan):
    from shared.performance import validate_artifact
    validate_artifact(plan,current_limits(plan))
    slug=plan.get('plan_slug')
    if slug and plan.get('source_revs'):
        from brain.plan_revision import plan_rev
        from brain.plan_paths import PlanNotFound, resolve
        try: current=plan_rev(resolve(slug)).files
        except PlanNotFound: pass  # Portable standalone plan; explicit constraints still checked.
        else:
            if plan['source_revs'] != current:raise ValueError('Named plan inputs changed; review and compile the performance before playback/rendering')
