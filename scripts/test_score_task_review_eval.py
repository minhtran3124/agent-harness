from score_task_review_eval import labels


def test_labels_tolerate_markdown_emphasis():
    assert {"spec_fail", "quality_fix"} <= labels(["**spec_verdict: fail**\n**quality_verdict: needs_fixes**"])


def test_labels_preserve_unknown():
    assert "cannot_verify" in labels(["spec_verdict: cannot_verify"])
