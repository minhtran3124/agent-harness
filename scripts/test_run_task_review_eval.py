from run_task_review_eval import prompt


def test_baseline_has_two_review_calls():
    assert len(prompt("baseline", "fixture")) == 2


def test_candidate_has_one_review_call_and_evidence_boundary():
    calls = prompt("candidate", "fixture")
    assert len(calls) == 1
    assert "complete provided evidence" in calls[0]
