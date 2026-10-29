import pytest

from app import db, stats, leveling


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """A new empty temporary database for each test that asks for it."""
    monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "test.db"))
    monkeypatch.setattr(db, "TOTAL_CLASSES", 5)
    db.create_tables()


def test_grade_value_reads_v_grades():
    assert stats.grade_value("V4") == 4
    assert stats.grade_value(" v10 ") == 10


def test_grade_value_ignores_other_scales():
    assert stats.grade_value("5.10a") is None


def test_athletic_summary_with_no_data(fresh_db):
    assert stats.athletic_summary("deadlift_weight") is None


def test_athletic_summary_best_and_change(fresh_db):
    db.add_athletic_skill("2026-09-01", None, 200.0, None, None)
    db.add_athletic_skill("2026-10-01", None, 225.0, None, None)
    db.add_athletic_skill("2026-10-02", 28.0, None, None, None)  # no deadlift

    summary = stats.athletic_summary("deadlift_weight")

    assert summary["best"] == 225.0
    assert summary["first"] == 200.0
    assert summary["latest"] == 225.0
    assert summary["change"] == 25.0
    assert summary["entries"] == 2


def test_athletic_summary_rejects_unknown_column(fresh_db):
    with pytest.raises(ValueError):
        stats.athletic_summary("date; DROP TABLE athletic_skills")


def test_golf_summary_ignores_nine_hole_rounds(fresh_db):
    db.add_golf_round("2026-09-01", "Course A", 18, 100, None)
    db.add_golf_round("2026-10-01", "Course A", 18, 95, None)
    db.add_golf_round("2026-10-02", "Course B", 9, 50, None)

    summary = stats.golf_summary()

    assert summary["rounds"] == 2
    assert summary["best"] == 95
    assert summary["average"] == 97.5
    assert summary["latest"] == 95
    assert summary["change"] == -5


def test_climb_summary(fresh_db):
    db.add_climb("2026-10-01", "Gym", "V3", 1, 2)
    db.add_climb("2026-10-02", "Gym", "V5", 0, 4)
    db.add_climb("2026-10-03", "Gym", "V4", 1, 1)

    summary = stats.climb_summary()

    assert summary["climbs"] == 3
    assert summary["sent"] == 2
    assert summary["send_rate"] == 67
    assert summary["hardest"] == "V4"


def test_level_and_rank_math():
    assert leveling.level_from_xp(0) == 1
    assert leveling.level_from_xp(99) == 1
    assert leveling.level_from_xp(100) == 2
    assert leveling.rank_for_level(1) == "E"
    assert leveling.rank_for_level(5) == "D"
    assert leveling.rank_for_level(45) == "S"


def test_total_xp_adds_up(fresh_db):
    db.add_golf_round("2026-10-01", "Course A", 18, 95, None)
    db.add_completed_class("2026-10-01", "Introduction to AI")

    assert leveling.total_xp() == leveling.XP_GOLF_ROUND + leveling.XP_CLASS