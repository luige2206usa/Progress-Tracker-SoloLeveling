from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app import coach, db


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """A new empty temporary database for each test that asks for it."""
    monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "test.db"))
    monkeypatch.setattr(db, "TOTAL_CLASSES", 5)
    db.create_tables()


class FakeClient:
    """Pretends to be the Anthropic client so tests never call the real API."""

    def __init__(self):
        self.last_request = None
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(text="Keep leveling, Hunter.")]
        )


def test_progress_text_includes_logged_data(fresh_db):
    db.add_athletic_skill("2026-10-01", None, 225.0, None, None)
    db.add_golf_round("2026-10-01", "Course A", 18, 95, None)

    text = coach.build_progress_text()

    assert "Deadlift: best 225 lbs" in text
    assert "best 95" in text
    assert "Vertical jump: no data yet." in text


def test_coach_message_uses_the_client(fresh_db):
    db.add_athletic_skill("2026-10-01", None, 225.0, None, None)
    client = FakeClient()

    message = coach.get_coach_message(client=client)

    assert message == "Keep leveling, Hunter."
    assert client.last_request["model"] == coach.MODEL
    assert "Deadlift" in client.last_request["messages"][0]["content"]


def test_missing_api_key_raises_coach_error(fresh_db, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(coach.CoachError):
        coach.get_coach_message()


def test_coach_messages_are_saved_newest_first(fresh_db):
    db.add_coach_message("2026-10-01", "First message")
    db.add_coach_message("2026-10-08", "Second message")

    rows = db.get_recent_coach_messages()

    assert rows[0] == ("2026-10-08", "Second message")
    assert rows[1] == ("2026-10-01", "First message")


class ThinkingThenTextClient:
    """Fake client whose answer starts with a thinking block, like the real one did."""

    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="planning the reply"),
                SimpleNamespace(type="text", text="Level up, Hunter."),
            ]
        )


def test_coach_skips_thinking_blocks(fresh_db):
    message = coach.get_coach_message(client=ThinkingThenTextClient())

    assert message == "Level up, Hunter."


class FailingClient:
    """Fake client whose request always raises the error you give it."""

    def __init__(self, error):
        def fail(**kwargs):
            raise error

        self.messages = SimpleNamespace(create=fail)


def make_request():
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def test_coach_reports_connection_problems(fresh_db):
    error = anthropic.APIConnectionError(request=make_request())

    with pytest.raises(coach.CoachError, match="internet"):
        coach.get_coach_message(client=FailingClient(error))


def test_coach_reports_a_rejected_key(fresh_db):
    response = httpx.Response(401, request=make_request())
    error = anthropic.AuthenticationError("bad key", response=response, body=None)

    with pytest.raises(coach.CoachError, match="key was rejected"):
        coach.get_coach_message(client=FailingClient(error))


def test_coach_rejects_a_reply_with_no_text(fresh_db):
    class ThinkingOnlyClient:
        def __init__(self):
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(type="thinking", thinking="hmm")]
            )

    with pytest.raises(coach.CoachError, match="no text"):
        coach.get_coach_message(client=ThinkingOnlyClient())