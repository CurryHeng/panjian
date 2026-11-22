from app.backtrack import apply_backtrack

def plan(clips):
    return dict(clips=[dict(id=str(i),start=a,end=b,notes='') for i,(a,b) in enumerate(clips)],clip_provenance=[dict(clip_id=str(i),reasons=['model']) for i in range(len(clips))])

def test_merge_and_audit_without_input_mutation():
    p=plan([(1,5),(8,12)]); frames=[(1,10,1)]*30; frames[6]=frames[7]=(1,0,1)
    out=apply_backtrack(p,frames)
    assert [(c['start'],c['end']) for c in out['clips']]==[(1,12)]
    assert p['clips'][1]['start']==8
    assert out['start_adjustments'][1]['final_start']==3
    assert out['clip_provenance'][0]['original_clip_ids']==['0','1']

def test_disabled_short_and_tail_only():
    p=plan([(8,12)]); frames=[(1,10,1)]*30; frames[13]=frames[14]=(1,0,1)
    assert apply_backtrack(p,frames)['clips'][0]['start']==8
    frames[6]=frames[7]=(1,0,1)
    assert apply_backtrack(p,frames,False)['clips']==p['clips']
    p['clip_provenance'][0]['reasons']=['recording_habit_tail']
    assert apply_backtrack(p,frames)['clips'][0]['start']==8


def test_environment_switch_controls_build_plan(monkeypatch):
    from app import highlights
    monkeypatch.setattr(highlights, 'frame_scores', lambda source: [(0,0,0)]*60)
    monkeypatch.setenv('PANJIAN_START_BACKTRACK','0')
    off=highlights.build_plan('unused',30)
    assert off['start_backtrack']['enabled'] is False
    assert off['strategy']=='person_motion_windows_v3_tail'
    monkeypatch.delenv('PANJIAN_START_BACKTRACK')
    on=highlights.build_plan('unused',30)
    assert on['start_backtrack']['enabled'] is True
    assert on['strategy']=='person_motion_windows_v4_tail_backtrack'
