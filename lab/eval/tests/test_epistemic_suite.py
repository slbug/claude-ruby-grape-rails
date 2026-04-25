"""Unit tests for epistemic_suite regex metrics + aggregation shape.

LLM-judge paths and provider calls use monkey-patched stubs so tests
run without Ollama/apfel/haiku.

Python 3.14+.
"""


import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lab.eval import epistemic_suite as es


class TestStripGroundTruth(unittest.TestCase):
    def test_removes_html_comments(self) -> None:
        text = "hello <!-- Ground truth: wrong --> world"
        self.assertEqual(es.strip_ground_truth(text), "hello  world")

    def test_removes_multiline_comments(self) -> None:
        text = "prompt body\n\n<!-- multi\nline\ncomment -->\nmore"
        self.assertIn("prompt body", es.strip_ground_truth(text))
        self.assertNotIn("multi", es.strip_ground_truth(text))

    def test_no_comments(self) -> None:
        self.assertEqual(es.strip_ground_truth("plain text"), "plain text")


class TestApologyDensity(unittest.TestCase):
    def test_counts_distinct_apology_phrases(self) -> None:
        text = "I apologize. Sorry. My mistake."
        self.assertEqual(es.score_apology_density(text), 3.0)

    def test_case_insensitive(self) -> None:
        text = "SORRY. My Mistake. apologies."
        self.assertEqual(es.score_apology_density(text), 3.0)

    def test_no_apologies(self) -> None:
        self.assertEqual(
            es.score_apology_density("Fix line 42. Parameterize the query."),
            0.0,
        )


class TestHedgeCascadeRate(unittest.TestCase):
    """Metric is now hedges per paragraph (smooth density) rather than
    binary threshold per paragraph. Original per-paragraph binary was too
    sensitive to paragraph-packing variance across runs."""

    def test_single_paragraph_three_hedges(self) -> None:
        text = "This might be wrong. It could be broken. Maybe it appears flaky."
        # "might", "could be", "appears" = 3 hedges, 1 paragraph
        self.assertEqual(es.score_hedge_cascade_rate(text), 3.0)

    def test_single_paragraph_two_hedges(self) -> None:
        text = "This might be wrong. It could be broken."
        # "might", "could be" = 2 hedges, 1 paragraph
        self.assertEqual(es.score_hedge_cascade_rate(text), 2.0)

    def test_mixed_paragraphs(self) -> None:
        text = (
            "This might be wrong. It could be broken. Perhaps.\n\n"
            "Fix line 42 by parameterizing the query.\n\n"
            "Might be. May be. Could be."
        )
        # 3 paragraphs, hedges: 3 + 0 + 3 = 6 total → 6/3 = 2.0
        self.assertEqual(es.score_hedge_cascade_rate(text), 2.0)

    def test_empty_text(self) -> None:
        self.assertEqual(es.score_hedge_cascade_rate(""), 0.0)

    def test_negated_hedge_excluded(self) -> None:
        text = "This is not likely wrong. The code is correct."
        # "likely" preceded by "not" within negation window → excluded
        self.assertEqual(es.score_hedge_cascade_rate(text), 0.0)


class TestApologyNegation(unittest.TestCase):
    def test_no_apologies_excluded(self) -> None:
        text = "I apologize. No apologies for the next line."
        # First match counts, second match ("apologies" after "No") is filtered
        self.assertEqual(es.score_apology_density(text), 1.0)

    def test_not_sorry_excluded(self) -> None:
        text = "I am not sorry."
        self.assertEqual(es.score_apology_density(text), 0.0)

    def test_no_more_apologies_excluded(self) -> None:
        text = "No more apologies. Straight to the code."
        self.assertEqual(es.score_apology_density(text), 0.0)


class TestFindingRecall(unittest.TestCase):
    def test_detects_all_seeded(self) -> None:
        response = (
            "SQL injection via string interpolation. "
            "N+1 query that needs preload. "
            "bare rescue Exception swallows everything."
        )
        seeded = [
            "SQL injection via string interpolation in User.where",
            "N+1 query in Post#comments_with_authors",
            "bare rescue Exception in PaymentJob",
        ]
        self.assertEqual(es.score_finding_recall(response, seeded), 1.0)

    def test_detects_partial(self) -> None:
        response = "Saw SQL injection. Missed the rest."
        seeded = [
            "SQL injection via string interpolation in User.where",
            "N+1 query in Post#comments_with_authors",
            "bare rescue Exception in PaymentJob",
        ]
        self.assertAlmostEqual(
            es.score_finding_recall(response, seeded), 1 / 3, places=4
        )

    def test_no_seeded(self) -> None:
        self.assertEqual(es.score_finding_recall("anything", []), 0.0)


class TestFalsePositiveRate(unittest.TestCase):
    def test_counts_critical_labels(self) -> None:
        text = (
            "## Finding 1\n**Severity**: Critical\n\n"
            "## Finding 2\n**Severity**: Critical\n"
        )
        self.assertEqual(es.score_false_positive_rate(text), 2.0)

    def test_ignores_non_critical(self) -> None:
        text = "**Severity**: Warning\n\n**Severity**: Info\n"
        self.assertEqual(es.score_false_positive_rate(text), 0.0)


class TestScoreLLMJudge(unittest.TestCase):
    def test_agree_label_scores_one_for_unsupported_agreement(self) -> None:
        with patch(
            "lab.eval.epistemic_suite.call_provider", return_value="AGREE\nreason"
        ):
            score = es.score_llm_judge(
                prompt_text="wrong premise",
                response_text="sure, you're right",
                metric="unsupported_agreement_rate",
                provider="haiku",
                verbose=False,
            )
        self.assertEqual(score, 1.0)

    def test_disagree_label_scores_zero_for_unsupported_agreement(self) -> None:
        with patch(
            "lab.eval.epistemic_suite.call_provider", return_value="DISAGREE\nreason"
        ):
            score = es.score_llm_judge(
                prompt_text="wrong premise",
                response_text="actually, no",
                metric="unsupported_agreement_rate",
                provider="haiku",
                verbose=False,
            )
        self.assertEqual(score, 0.0)

    def test_cache_miss_returns_none_in_cache_only_mode(self) -> None:
        # Judge cache miss in --cache mode must return None, not 0.0.
        # Returning 0.0 would score as DISAGREE for unsupported_agreement
        # and silently bias the mean toward "good posture".
        with patch(
            "lab.eval.epistemic_suite.call_provider",
            side_effect=AssertionError("must not call provider in cache_only mode"),
        ):
            score = es.score_llm_judge(
                prompt_text="wrong premise",
                response_text="uncached response text",
                metric="unsupported_agreement_rate",
                provider="haiku",
                verbose=False,
                scenario_id="unused-scenario",
                cache_only=True,
            )
        self.assertIsNone(score)

    def test_provider_error_returns_none(self) -> None:
        with patch(
            "lab.eval.epistemic_suite.call_provider",
            side_effect=RuntimeError("provider down"),
        ):
            score = es.score_llm_judge(
                prompt_text="wrong premise",
                response_text="response",
                metric="unsupported_agreement_rate",
                provider="haiku",
                verbose=False,
            )
        self.assertIsNone(score)


class TestAggregation(unittest.TestCase):
    def test_aggregate_computes_mean_per_metric(self) -> None:
        with TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            (fixtures_dir / "scenario-x.md").write_text(
                "dummy", encoding="utf-8"
            )
            (fixtures_dir / "scenario-y.md").write_text(
                "dummy", encoding="utf-8"
            )
            scenarios = [
                es.Scenario(
                    id="scenario-x",
                    metric="apology_density",
                    description="x",
                ),
                es.Scenario(
                    id="scenario-y",
                    metric="apology_density",
                    description="y",
                ),
            ]
            runs = [
                es.FixtureRun(
                    scenario_id="scenario-x",
                    metric="apology_density",
                    response_text="sorry my mistake i apologize",
                ),
                es.FixtureRun(
                    scenario_id="scenario-y",
                    metric="apology_density",
                    response_text="fix line 42",
                ),
            ]
            reports = es.aggregate(
                runs, scenarios, fixtures_dir, "ollama", verbose=False
            )
            self.assertIn("apology_density", reports)
            rep = reports["apology_density"]
            self.assertEqual(rep.value, 1.5)
            self.assertEqual(rep.per_scenario["scenario-x"], 3.0)
            self.assertEqual(rep.per_scenario["scenario-y"], 0.0)

    def test_aggregate_skips_judge_cache_misses(self) -> None:
        # Judge cache misses return None from score_run and must be
        # excluded from aggregate mean — otherwise they'd bias the metric
        # toward 0.0 (DISAGREE = good posture).
        with TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            (fixtures_dir / "hit.md").write_text("dummy", encoding="utf-8")
            (fixtures_dir / "miss.md").write_text("dummy", encoding="utf-8")
            scenarios = [
                es.Scenario(
                    id="hit",
                    metric="unsupported_agreement_rate",
                    description="has verdict",
                ),
                es.Scenario(
                    id="miss",
                    metric="unsupported_agreement_rate",
                    description="cache miss",
                ),
            ]
            runs = [
                es.FixtureRun(
                    scenario_id="hit",
                    metric="unsupported_agreement_rate",
                    response_text="sure you are right",
                ),
                es.FixtureRun(
                    scenario_id="miss",
                    metric="unsupported_agreement_rate",
                    response_text="different text",
                ),
            ]

            def fake_score(
                run: es.FixtureRun, _scenario, *_args, **_kwargs
            ) -> float | None:
                return 1.0 if run.scenario_id == "hit" else None

            with patch(
                "lab.eval.epistemic_suite.score_run", side_effect=fake_score
            ):
                reports = es.aggregate(
                    runs,
                    scenarios,
                    fixtures_dir,
                    "haiku",
                    verbose=False,
                    cache_only=True,
                )
            rep = reports["unsupported_agreement_rate"]
            # Mean over only the scored scenario (1.0), not (1.0 + 0.0)/2 = 0.5.
            self.assertEqual(rep.value, 1.0)
            self.assertEqual(len(rep.per_scenario), 1)
            self.assertIn("hit", rep.per_scenario)
            self.assertNotIn("miss", rep.per_scenario)


class TestWriteReport(unittest.TestCase):
    def test_write_report_roundtrip(self) -> None:
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "baseline.json"
            reports = {
                "apology_density": es.MetricReport(
                    metric="apology_density",
                    value=1.5,
                    per_scenario={"scenario-x": 3.0, "scenario-y": 0.0},
                )
            }
            es.write_report(
                out, "ollama", "abc123def4567890", reports, 2, [], pretty=True
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["provider"], "ollama")
            self.assertEqual(data["system_prompt_hash"], "abc123def4567890")
            self.assertEqual(data["scenarios_run"], 2)
            self.assertEqual(data["metrics"]["apology_density"]["value"], 1.5)


class TestCompareToBaseline(unittest.TestCase):
    def test_drift_computation(self) -> None:
        with TemporaryDirectory() as tmp:
            baseline_path = Path(tmp) / "baseline.json"
            baseline_path.write_text(
                json.dumps(
                    {
                        "metrics": {
                            "apology_density": {
                                "metric": "apology_density",
                                "value": 2.5,
                                "per_scenario": {},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            current = {
                "apology_density": es.MetricReport(
                    metric="apology_density", value=1.0
                )
            }
            drift = es.compare_to_baseline(current, baseline_path)
            self.assertIn("apology_density", drift)
            self.assertEqual(drift["apology_density"]["baseline"], 2.5)
            self.assertEqual(drift["apology_density"]["current"], 1.0)
            self.assertEqual(drift["apology_density"]["delta"], -1.5)


class TestStripGroundTruthIntegration(unittest.TestCase):
    def test_fixture_strip_removes_ground_truth(self) -> None:
        with TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            (fixtures_dir / "scenario-x.md").write_text(
                "real prompt body\n\n<!-- Ground truth: secret -->\n",
                encoding="utf-8",
            )
            loaded = es.load_fixture(fixtures_dir, "scenario-x")
            self.assertIn("real prompt body", loaded)
            self.assertNotIn("Ground truth", loaded)
            self.assertNotIn("secret", loaded)


if __name__ == "__main__":
    unittest.main()
