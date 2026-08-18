from score_task_review_eval import labels, record_tokens


def test_labels_tolerate_markdown_emphasis():
    assert {"spec_fail", "quality_fix"} <= labels(["**spec_verdict: fail**\n**quality_verdict: needs_fixes**"])


def test_labels_preserve_unknown():
    assert "cannot_verify" in labels(["spec_verdict: cannot_verify"])


def test_labels_do_not_credit_negated_minor():
    # A reviewer reporting *no* Minor finding must not satisfy the minor case.
    assert "minor" not in labels(["spec_verdict: pass\nquality_verdict: approved\nNo Minor findings."])


def test_labels_still_credit_a_real_minor_finding():
    assert "minor" in labels(["findings:\n- severity: Minor — nit in naming"])


def test_labels_credit_real_minor_despite_a_cooccurring_negation():
    assert "minor" in labels(["- severity: Minor — whitespace nit\nThere are no minor blockers otherwise."])


def test_labels_do_not_credit_the_word_minority():
    assert "minor" not in labels(["A minority of cases are slow. spec_verdict: pass"])


def test_record_tokens_sums_input_and_output_across_dispatches():
    record = {"usage": [{"input_tokens": 100, "output_tokens": 20}, {"input_tokens": 50, "output_tokens": 8}]}
    assert record_tokens(record) == 178


def test_record_tokens_zero_when_usage_absent():
    assert record_tokens({"case_id": "x"}) == 0


def test_record_tokens_tolerates_null_usage():
    assert record_tokens({"case_id": "x", "usage": None}) == 0
