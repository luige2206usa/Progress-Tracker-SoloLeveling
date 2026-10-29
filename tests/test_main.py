import sqlite3
from datetime import date

import pytest

import main
from app import db


def feed_inputs(monkeypatch, answers):
    """Replace input() so each call returns the next fake answer."""
    remaining = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(remaining))


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "test.db"))
    monkeypatch.setattr(db, "TOTAL_CLASSES", 5)
    db.create_tables()


# ---------- ask_int ----------

def test_ask_int_retries_until_valid(monkeypatch, capsys):
    feed_inputs(monkeypatch, ["abc", "-1", "5"])

    assert main.ask_int("Sets: ", minimum=0) == 5

    output = capsys.readouterr().out
    assert "whole number" in output
    assert "at least 0" in output


def test_ask_int_optional_blank_returns_none(monkeypatch):
    feed_inputs(monkeypatch, [""])

    assert main.ask_int("Putts: ", optional=True) is None


# ---------- ask_float ----------

def test_ask_float_rejects_below_minimum(monkeypatch, capsys):
    feed_inputs(monkeypatch, ["0", "135.5"])

    assert main.ask_float("Weight: ", minimum=1) == 135.5
    assert "at least 1" in capsys.readouterr().out


def test_ask_float_rejects_text(monkeypatch):
    feed_inputs(monkeypatch, ["heavy", "200"])

    assert main.ask_float("Weight: ") == 200.0


# ---------- ask_yes_no ----------

def test_ask_yes_no(monkeypatch):
    feed_inputs(monkeypatch, ["maybe", "Y"])
    assert main.ask_yes_no("Sent?") == 1

    feed_inputs(monkeypatch, ["no"])
    assert main.ask_yes_no("Sent?") == 0


# ---------- ask_text ----------

def test_ask_text_required_retries_on_blank(monkeypatch):
    feed_inputs(monkeypatch, ["", "  ", "Memorial Park"])

    assert main.ask_text("Course: ") == "Memorial Park"


def test_ask_text_optional_blank_returns_none(monkeypatch):
    feed_inputs(monkeypatch, [""])

    assert main.ask_text("Notes: ", optional=True) is None


# ---------- ask_date ----------

def test_ask_date_blank_means_today(monkeypatch):
    feed_inputs(monkeypatch, [""])

    assert main.ask_date() == date.today().isoformat()


def test_ask_date_rejects_invalid_then_accepts(monkeypatch, capsys):
    feed_inputs(monkeypatch, ["2026-99-99", "2026-10-27"])

    assert main.ask_date() == "2026-10-27"
    assert "not a valid date" in capsys.readouterr().out


# ---------- the menu ----------

def test_menu_exits_on_zero(fresh_db, monkeypatch, capsys):
    feed_inputs(monkeypatch, ["0"])

    main.main()

    assert "Goodbye!" in capsys.readouterr().out


def test_menu_rejects_invalid_choice(fresh_db, monkeypatch, capsys):
    feed_inputs(monkeypatch, ["9", "0"])

    main.main()

    assert "Invalid choice" in capsys.readouterr().out


# ---------- end to end ----------

def test_logging_a_golf_round_through_the_menu(fresh_db, monkeypatch):
    # Menu choice 2, then: date (blank = today), course, holes, score,
    # putts (blank = skip), then exit.
    feed_inputs(monkeypatch, ["2", "", "Test Course", "18", "95", "", "0"])

    main.main()

    conn = sqlite3.connect(db.DB_NAME)
    rows = conn.execute(
        "SELECT course, holes, score, putts FROM golf_rounds"
    ).fetchall()
    conn.close()
    assert rows == [("Test Course", 18, 95, None)]


def test_athletic_submenu_saves_only_chosen_skills(fresh_db, monkeypatch):
    # Menu 1, date blank, submenu: 2 (deadlift) = 225, 0 (save), main exit.
    feed_inputs(monkeypatch, ["1", "", "2", "225", "0", "0"])

    main.main()

    conn = sqlite3.connect(db.DB_NAME)
    rows = conn.execute(
        "SELECT jump_height, deadlift_weight, upperbody_weight, body_weight "
        "FROM athletic_skills"
    ).fetchall()
    conn.close()
    assert rows == [(None, 225.0, None, None)]

def test_logging_a_climb_through_the_menu(fresh_db, monkeypatch):
    # Menu 3, then: date (blank), location, grade, sent, attempts, exit.
    feed_inputs(monkeypatch, ["3", "", "Local Gym", "V4", "y", "2", "0"])

    main.main()

    conn = sqlite3.connect(db.DB_NAME)
    rows = conn.execute(
        "SELECT location, grade, sent, attempts FROM climbs"
    ).fetchall()
    conn.close()
    assert rows == [("Local Gym", "V4", 1, 2)]


def test_completed_class_and_duplicate_check(fresh_db, monkeypatch, capsys):
    # Log the same class twice. The second attempt must be rejected.
    feed_inputs(
        monkeypatch,
        ["4", "", "Intro to AI", "4", "", "Intro to AI", "0"],
    )

    main.main()

    output = capsys.readouterr().out
    assert "Classes completed: 1 | Classes left: 4" in output
    assert "already logged" in output
    assert db.get_progress() == (1, 4)


def test_athletic_menu_with_nothing_chosen(fresh_db, monkeypatch, capsys):
    # Menu 1, date blank, immediately choose 0 (save), then exit.
    feed_inputs(monkeypatch, ["1", "", "0", "0"])

    main.main()

    assert "Nothing to save" in capsys.readouterr().out
    conn = sqlite3.connect(db.DB_NAME)
    count = conn.execute("SELECT COUNT(*) FROM athletic_skills").fetchone()[0]
    conn.close()
    assert count == 0


def test_athletic_menu_with_every_skill(fresh_db, monkeypatch):
    feed_inputs(
        monkeypatch,
        ["1", "", "1", "28.5", "2", "225", "3", "135", "4", "175", "0", "0"],
    )

    main.main()

    conn = sqlite3.connect(db.DB_NAME)
    rows = conn.execute(
        "SELECT jump_height, deadlift_weight, upperbody_weight, body_weight "
        "FROM athletic_skills"
    ).fetchall()
    conn.close()
    assert rows == [(28.5, 225.0, 135.0, 175.0)]


def test_report_with_no_data(fresh_db, monkeypatch, capsys):
    feed_inputs(monkeypatch, ["5", "0"])

    main.main()

    output = capsys.readouterr().out
    assert "Progress Report" in output
    assert "no data yet" in output


def test_report_with_data(fresh_db, monkeypatch, capsys):
    db.add_athletic_skill("2026-09-01", None, 200.0, None, None)
    db.add_athletic_skill("2026-10-01", None, 225.0, None, None)
    db.add_golf_round("2026-10-01", "Course A", 18, 95, None)
    feed_inputs(monkeypatch, ["5", "0"])

    main.main()

    output = capsys.readouterr().out
    assert "Deadlift: best 225 lbs" in output
    assert "change +25 lbs" in output
    assert "best 95" in output


def test_coach_option_saves_and_shows_message(fresh_db, monkeypatch, capsys):
    # Replace the real coach call so the test never touches the internet.
    monkeypatch.setattr(main, "get_coach_message", lambda: "Level up, Hunter.")
    feed_inputs(monkeypatch, ["6", "7", "0"])

    main.main()

    output = capsys.readouterr().out
    assert output.count("Level up, Hunter.") == 2  # printed, then in history
    assert len(db.get_recent_coach_messages()) == 1


def test_coach_option_without_a_key_does_not_crash(fresh_db, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    feed_inputs(monkeypatch, ["6", "0"])

    main.main()

    assert "Coach unavailable" in capsys.readouterr().out