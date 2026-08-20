from psl.admission.engine import AdmissionResult, VERDICTS, decide_verdict


def test_xwoba_like_result_is_projection():
    res = AdmissionResult(
        player_type="hitter",
        feature="xwoba",
        family="expected",
        target="y_woba",
        role="skill",
        process=True,
        oos_rmse_delta=-0.0012,
        baseline_rmse=0.036,
        oos_rmse_ci_low=-0.0014,
        oos_rmse_ci_high=-0.0007,
        folds_improved=1.0,
        n_folds=7,
        coverage=1.0,
        missing_systematic=False,
        nested_rmse_delta=-0.0003,
        coef_sign_changes=0,
        extra={"in_baseline": False},
        subgroup={"age_prime": {"ok": True, "n": 1000, "rmse_delta": -0.001}},
    )
    verdict, _ = decide_verdict(res)
    assert verdict == "Projection"


def test_limited_coverage_can_be_augmented():
    res = AdmissionResult(
        player_type="pitcher",
        feature="stuff_plus",
        family="process",
        target="y_fip",
        role="skill",
        process=True,
        oos_rmse_delta=-0.002,
        baseline_rmse=0.05,
        oos_rmse_ci_low=-0.003,
        oos_rmse_ci_high=-0.001,
        folds_improved=1.0,
        n_folds=4,
        coverage=0.28,
        missing_systematic=True,
        extra={"in_baseline": False},
    )
    verdict, _ = decide_verdict(res)
    assert verdict == "Augmented Projection"


def test_insufficient_evidence_is_first_class():
    assert "Insufficient Evidence" in VERDICTS
    assert "Insufficient Evidence" != "Exclude"


def test_one_fold_sparse_coverage_is_insufficient_evidence():
    res = AdmissionResult(
        player_type="pitcher",
        feature="stuff_plus",
        family="stuff",
        target="y_fip",
        role="skill",
        process=True,
        oos_rmse_delta=-0.00038,
        baseline_rmse=0.043,
        oos_rmse_ci_low=-0.0010,
        oos_rmse_ci_high=0.00013,
        folds_improved=1.0,
        n_folds=1,
        coverage=509 / 2682,
        missing_systematic=True,
        extra={"in_baseline": False},
    )
    verdict, rationale = decide_verdict(res)
    assert verdict == "Insufficient Evidence"
    assert "not proof" in rationale.lower() or "not an Exclude" in rationale


def test_extension_one_fold_is_not_augmented_projection():
    res = AdmissionResult(
        player_type="pitcher",
        feature="extension",
        family="release",
        target="y_fip",
        role="skill",
        process=True,
        oos_rmse_delta=-0.00072,
        baseline_rmse=0.043,
        oos_rmse_ci_low=-0.0016,
        oos_rmse_ci_high=-0.00001,
        folds_improved=1.0,
        n_folds=1,
        coverage=509 / 2682,
        missing_systematic=True,
        extra={"in_baseline": False},
    )
    verdict, _ = decide_verdict(res)
    assert verdict == "Insufficient Evidence"
    assert verdict != "Augmented Projection"
    assert verdict != "Diagnostic"


def test_process_metric_with_full_windows_can_be_diagnostic():
    res = AdmissionResult(
        player_type="hitter",
        feature="o_swing_pct",
        family="plate_discipline",
        target="y_woba",
        role="skill",
        process=True,
        oos_rmse_delta=-0.00007,
        baseline_rmse=0.035,
        oos_rmse_ci_low=-0.0002,
        oos_rmse_ci_high=0.0001,
        folds_improved=0.4,
        n_folds=7,
        coverage=1.0,
        extra={"in_baseline": False},
    )
    verdict, _ = decide_verdict(res)
    assert verdict == "Diagnostic"
