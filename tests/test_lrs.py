"""
Tests for the Loop Readiness Score (LRS) calculator.
"""

import sys
import json
sys.path.insert(0, "../src")

from src.utils.lrs import calculateLRS, scoreToGrade
from src.schema.types import LoopConfig


def make_config(**overrides):
    """Helper to create a minimal LoopConfig for testing."""
    base = {
        "name": "test-loop",
        "description": "A test loop for unit testing",
        "trigger": {"type": "manual"},
        "pipeline": [{"prompt": "Do something", "label": "test"}],
        "verify": {
            "maker": "maker-agent",
            "checker": "checker-agent",
            "maxRounds": 3,
            "autoRetry": True,
        },
        "budget": {
            "maxTokens": 100000,
            "maxDurationMinutes": 30,
            "maxIterations": 10,
        },
        "memory": {"store": "filesystem", "path": ".loopcode/state"},
    }
    base.update(overrides)
    return LoopConfig.parse(base)


def test_perfect_config_scores_A():
    """A loop with all best practices should score A grade."""
    config = make_config()
    lrs = calculateLRS(config)
    assert lrs.total >= 80
    assert scoreToGrade(lrs.total) in ("A", "B")


def test_no_verification_scores_lower():
    """Missing verification should significantly reduce score."""
    config = make_config()
    config_dict = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    del config_dict["verify"]
    config_no_verify = LoopConfig.parse(config_dict)

    lrs_with = calculateLRS(config)
    lrs_without = calculateLRS(config_no_verify)

    assert lrs_without.total < lrs_with.total
    assert "缺少验证机制" in str(lrs_without.issues) or "verification" in str(lrs_without.issues).lower()


def test_no_budget_scores_lower():
    """Missing budget controls should reduce score."""
    config = make_config()
    config_dict = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    config_dict["budget"] = {}
    config_no_budget = LoopConfig.parse(config_dict)

    lrs_with = calculateLRS(config)
    lrs_without = calculateLRS(config_no_budget)

    assert lrs_without.total < lrs_with.total


def test_no_description_scores_lower():
    """Missing description should reduce quantifiable_goal score."""
    config = make_config(description="")
    lrs = calculateLRS(config)
    assert lrs.dimensions["quantifiable_goal"] < 50
    assert len(lrs.issues) > 0


def test_same_maker_checker_warning():
    """Using same agent for maker and checker should raise an issue."""
    config = make_config()
    verify = config.verify
    verify.maker = ["same-agent"]
    verify.checker = ["same-agent"]
    config.verify = verify

    lrs = calculateLRS(config)
    assert lrs.dimensions["verification"] <= 50
    assert any("Maker" in issue for issue in lrs.issues)


def test_grade_boundaries():
    """Test grade boundaries."""
    assert scoreToGrade(95) == "A"
    assert scoreToGrade(85) == "B"
    assert scoreToGrade(70) == "C"
    assert scoreToGrade(55) == "D"
    assert scoreToGrade(40) == "F"


if __name__ == "__main__":
    test_perfect_config_scores_A()
    test_no_verification_scores_lower()
    test_no_budget_scores_lower()
    test_no_description_scores_lower()
    test_same_maker_checker_warning()
    test_grade_boundaries()
    print("All tests passed!")
