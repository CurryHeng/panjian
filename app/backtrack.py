from copy import deepcopy
from statistics import mean


def apply_backtrack(plan, frames, enabled=True):
    result = deepcopy(plan)
    result['clips_before_backtrack'] = deepcopy(plan['clips'])
    result['start_backtrack'] = dict(enabled=enabled, lookback_seconds=5, minimum_seconds=2, sample_fps=2)
    reasons = {p['clip_id']: p['reasons'] for p in plan['clip_provenance']}
    adjustments, items = [], []
    for c in result['clips']:
        old = c['start']; why = set(reasons[c['id']]); valley = old
        decision = 'disabled' if not enabled else 'tail_only'
        if enabled and 'model' in why:
            k = int(old*2)
            options = [(mean([frames[i][1],frames[i+1][1]]),i) for i in range(max(1,k-10),min(k-1,len(frames)-1))]
            if options: valley = min(options,key=lambda v:(v[0],-v[1]))[1]/2
            decision = 'below_minimum'
            if old-valley >= 2:
                c['start'] = valley
                c['notes'] += f'；按运动线索向前保留{old-valley:g}秒（非动作识别结论）'
                why.add('selective_start_backtrack'); decision = 'applied'
        adjustments.append(dict(original_clip_id=c['id'],original_start=old,suggested_start=valley,final_start=c['start'],decision=decision))
        items.append((c,why,[c['id']]))
    merged = []
    preserved_gaps = []
    for c,why,ids in sorted(items,key=lambda x:x[0]['start']):
        if not merged or c['start'] >= merged[-1][0]['end'] + 1:
            merged.append((c,why,ids))
            continue
        prev, pwhy, pids = merged[-1]
        if c['start'] > prev['end']:
            preserved_gaps.append(dict(clip_id=prev['id'], start=prev['end'], end=c['start']))
            pwhy.add('short_gap_preserved')
            prev['notes'] += '；保留不足1秒的片段间原画面'
        prev['end'] = max(prev['end'], c['end'])
        prev['notes'] += '；合并：' + c['notes']
        pwhy.update(why)
        pids.extend(ids)
    result['preserved_gaps'] = preserved_gaps
    result['boundary_policy'] = 'clamp_then_merge_overlaps_and_gaps_under_one_second'
    result['clips'] = [x[0] for x in merged]
    result['clip_provenance'] = [dict(clip_id=c['id'],reasons=sorted(why),original_clip_ids=ids) for c,why,ids in merged]
    result['start_adjustments'] = adjustments
    if enabled: result.update(schema_version=3,strategy='person_motion_windows_v4_tail_backtrack')
    return result
