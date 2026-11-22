from app.highlights import plan_from_scores


def test_padding_merge_and_source_bounds():
    # Uniform action windows abut: padding must merge, not duplicate footage.
    plan = plan_from_scores([(0.8, 10, 0.8)] * 60, 30)
    assert len(plan['candidates']) == 2
    assert len(plan['clips']) == 1
    clip = plan['clips'][0]
    assert clip['start'] == min(c['start'] for c in plan['candidates']) - 2
    assert clip['end'] == 30
    assert plan['semantic_event_verified'] is False


def test_short_source_never_extends_beyond_media():
    plan = plan_from_scores([(0.8, 10, 0.8)] * 5, 2.4)
    assert plan['clips'][0]['start'] == 0
    assert plan['clips'][0]['end'] == 2.4


def test_no_actions_still_preserves_tail_and_labels_fallback():
    plan = plan_from_scores([(0, 0, 0)] * 60, 30)
    assert [(c['start'], c['end']) for c in plan['clips']] == [(20, 30)]
    assert plan['recommendation_status'] == 'tail_only'
    assert plan['candidates'] == []
    assert plan['clip_provenance'][0]['reasons'] == ['recording_habit_tail']


def test_tail_added_without_erasing_early_action():
    scores = [(0.8, 10, 0.8)] * 12 + [(0, 0, 0)] * 108
    plan = plan_from_scores(scores, 60)
    assert [(c['start'], c['end']) for c in plan['clips']] == [(0, 8), (50, 60)]


def test_tail_merges_with_model_output_without_duplicate():
    plan = plan_from_scores([(0.8, 10, 0.8)] * 60, 30)
    assert len(plan['clips']) == 1
    assert plan['clip_provenance'][0]['reasons'] == ['model', 'recording_habit_tail']


def test_short_gap_to_tail_is_preserved():
    scores = [(0.8, 10, 0.8)] * 12
    for backtrack_enabled in (True, False):
        plan = plan_from_scores(scores, 18.62, backtrack_enabled=backtrack_enabled)
        assert [(c['start'], c['end']) for c in plan['clips']] == [(0, 18.62)]
        assert plan['clip_provenance'][0]['reasons'] == [
            'model', 'recording_habit_tail', 'short_gap_preserved',
        ]


def test_one_second_gap_remains_a_cut():
    scores = [(0.8, 10, 0.8)] * 12
    plan = plan_from_scores(scores, 19)
    assert [(c['start'], c['end']) for c in plan['clips']] == [(0, 8), (9, 19)]
