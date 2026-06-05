from __future__ import annotations

import unittest

from temporal_demo.byoc_assistant import ByocAnswers, analyze_answers


class ByocAssistantTests(unittest.TestCase):
    def test_analysis_maps_plain_answers_to_temporal_concepts(self) -> None:
        analysis = analyze_answers(
            ByocAnswers(
                process_name="Menu rollout",
                summary="Publishing starts after approval and is done when all stores receive the menu.",
                current_mechanism="cron, DB status flags, support reruns",
                pain_points="manual recovery and poor visibility",
                external_systems="menu API, store API, email",
                has_waits=True,
                has_external_events=True,
                has_retries=True,
                has_manual_recovery=True,
                needs_visibility=True,
                has_parallel_work=True,
                needs_compensation=True,
                can_run_long=True,
                adoption_concerns="ownership of workers",
            )
        )

        concepts = {finding.concept for finding in analysis.findings}
        self.assertEqual(analysis.fit_label, "strong candidate")
        self.assertIn("Workflow", concepts)
        self.assertIn("Activities", concepts)
        self.assertIn("Signals", concepts)
        self.assertIn("Timers", concepts)
        self.assertIn("Queries", concepts)
        self.assertTrue(any("MenuRolloutWorkflow" in item for item in analysis.sketch))
        self.assertTrue(any("ownership of workers" in question for question in analysis.follow_up_questions))

    def test_analysis_does_not_force_positive_fit(self) -> None:
        analysis = analyze_answers(
            ByocAnswers(
                process_name="Profile update",
                summary="User edits a profile and the request returns.",
                current_mechanism="HTTP handler",
                pain_points="none",
                external_systems="",
                has_waits=False,
                has_external_events=False,
                has_retries=False,
                has_manual_recovery=False,
                needs_visibility=False,
                has_parallel_work=False,
                needs_compensation=False,
                can_run_long=False,
                adoption_concerns="",
            )
        )

        self.assertEqual(analysis.fit_label, "weak or unclear candidate")
        self.assertLessEqual(len(analysis.findings), 1)


if __name__ == "__main__":
    unittest.main()
