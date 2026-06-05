from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from typer.testing import CliRunner

from apps.client.__main__ import app
from temporal_demo.activities.agent_activities import decide_next_action
from temporal_demo.workflows.agent_loop import AgentLoopInput
from temporal_demo.workflows.menu_rollout import MenuRolloutInput


ROOT = Path(__file__).resolve().parents[1]


class Path2ExampleTests(unittest.TestCase):
    def test_cli_exposes_all_three_example_families(self) -> None:
        result = CliRunner().invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("start-order", result.stdout)
        self.assertIn("start-menu", result.stdout)
        self.assertIn("start-agent", result.stdout)

    def test_walkthroughs_exist_with_expansion_ideas(self) -> None:
        for filename in [
            "ORDER_FULFILLMENT_WALKTHROUGH.md",
            "MENU_ROLLOUT_WALKTHROUGH.md",
            "AGENT_LOOP_WALKTHROUGH.md",
        ]:
            body = (ROOT / "docs" / filename).read_text(encoding="utf-8")
            self.assertIn("## Run It", body)
            self.assertIn("## What To Look For", body)
            self.assertIn("## Expansion Ideas", body)

    def test_example_inputs_have_simple_defaults(self) -> None:
        menu_input = MenuRolloutInput(menu_id="menu-1", version="v1", channels=["stores"])
        agent_input = AgentLoopInput(goal="Investigate an issue")

        self.assertEqual(menu_input.approval_timeout_seconds, 300)
        self.assertEqual(agent_input.min_steps, 3)
        self.assertEqual(agent_input.max_steps, 10)

    def test_agent_decision_activity_can_complete_from_recorded_state(self) -> None:
        decision = asyncio.run(
            decide_next_action(
                goal="Investigate an issue",
                completed_steps=3,
                previous_results=["tool result"],
                target_steps=3,
                min_steps=3,
                max_steps=10,
            )
        )

        self.assertTrue(decision.done)
        self.assertIn("Satisfied after 3 tool calls", decision.final_answer)


if __name__ == "__main__":
    unittest.main()
