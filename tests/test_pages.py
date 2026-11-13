"""Smoke tests: every page renders, and the main flows run, for a demo profile."""
import os

import pytest
from streamlit.testing.v1 import AppTest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TIMEOUT = 60


def page(name):
    """An AppTest rooted at Home.py (so page links resolve) and switched to ``pages/<name>``."""
    at = AppTest.from_file(os.path.join(ROOT, "Home.py"), default_timeout=TIMEOUT)
    at.switch_page(f"pages/{name}")
    return at


def demo_session(at, slug="side-hustle-landlord"):
    at.session_state["user_id"] = f"demo:{slug}"
    at.session_state["logged_in"] = True
    return at


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    import storage

    monkeypatch.setenv("FIRESIGHT_DATA", str(tmp_path / "users.json"))
    monkeypatch.setenv("FIRESIGHT_BACKEND", "local")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(storage, "_store", None)
    monkeypatch.chdir(ROOT)


def test_home_renders():
    at = AppTest.from_file(os.path.join(ROOT, "Home.py"), default_timeout=TIMEOUT).run()
    assert not at.exception
    assert "FIRESight" in at.title[0].value


def test_login_page_offers_demo_profiles_and_signup():
    at = page("Create Account and Log in.py").run()
    assert not at.exception
    demo_buttons = [b for b in at.button if b.label == "Use this profile"]
    assert len(demo_buttons) == 3
    demo_buttons[0].click().run()
    assert at.session_state["user_id"].startswith("demo:")

    at = page("Create Account and Log in.py").run()
    at.text_input[2].input("new@example.com")
    at.text_input[3].input("a-password")
    next(b for b in at.button if b.label == "Create Account").click().run()
    assert not at.exception
    assert at.session_state["logged_in"] and not at.session_state["user_id"].startswith("demo:")


def test_edit_profile_renders_every_section():
    at = demo_session(page("Edit Profile.py")).run()
    assert not at.exception
    for section in at.sidebar.radio[0].options:
        at.sidebar.radio[0].set_value(section).run()
        assert not at.exception, section
        assert not at.error, (section, [e.value for e in at.error])


def test_run_simulation_page():
    at = demo_session(page("Run Simulation.py")).run()
    at.button[0].click().run()
    assert not at.exception
    assert any("Simulation Results" in t.value for t in at.title)


def test_scenario_analysis_page():
    at = demo_session(page("Scenario Analysis.py"), "early-career-saver").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Run Scenario Analysis").click().run()
    assert not at.exception
    assert any("Scenario Analysis Results" in h.value for h in at.header)


def test_gpt_page_explains_setup_without_a_key():
    at = demo_session(page("Try Firesight GPT.py")).run()
    assert not at.exception
    assert "ANTHROPIC_API_KEY" in at.info[0].value


@pytest.mark.parametrize("slug", ["early-career-saver", "dual-income-family", "side-hustle-landlord"])
def test_edit_profile_save_round_trip_still_simulates(slug):
    from FIRE import run_monte_carlo_simulation

    at = demo_session(page("Edit Profile.py"), slug).run()
    for section in at.sidebar.radio[0].options:
        at.sidebar.radio[0].set_value(section).run()
        next(b for b in at.sidebar.button if b.label == "Save Profile").click().run()
        assert not at.exception, section
    saved = at.session_state[f"profile:demo:{slug}"]
    assert len(saved["income"]) >= 1 and len(saved["budget_items"]) >= 5 and len(saved["milestones"]) == 1
    _, _, _, results = run_monte_carlo_simulation({**saved, "num_simulations": 2, "simulate_years": 3}, seed=0)
    assert len(results) == 2
