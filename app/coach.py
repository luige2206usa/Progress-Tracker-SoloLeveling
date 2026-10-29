import os

import anthropic
from dotenv import load_dotenv

from app.db import get_progress
from app.leveling import player_status
from app.stats import athletic_summary, golf_summary, climb_summary

# Read the .env file once, when this file is first loaded.
load_dotenv()

# Model names change over time. If this one stops working, check the
# model list in the Anthropic docs. A smaller model costs less.
MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 2000

SYSTEM_PROMPT = (
    "You are 'the System' from a Solo Leveling style progress tracker, "
    "speaking to a hunter who is leveling up in real life. "
    "Write a short coach message of at most 150 words. "
    "Mention specific numbers from the data, celebrate real improvements, "
    "point out any plateau honestly, and end with two concrete goals for "
    "the next week. Be motivating but not cheesy. "
    "Lower golf scores are better. Do not judge whether body weight going "
    "up or down is good or bad, since the hunter's goal is unknown; only "
    "mention it as a number. Never invent data that wasn't provided."
)

LIFTS = [
    ("jump_height", "Vertical jump", "in"),
    ("deadlift_weight", "Deadlift", "lbs"),
    ("upperbody_weight", "Upper body lift", "lbs"),
]


class CoachError(Exception):
    """Raised when the coach can't produce a message."""


def build_progress_text():
    """Turn your saved data into plain text the coach can read."""
    status = player_status()
    lines = [
        f"Hunter status: rank {status['rank']}, level {status['level']}, "
        f"{status['xp']} XP."
    ]

    for column, label, unit in LIFTS:
        summary = athletic_summary(column)
        if summary is None:
            lines.append(f"{label}: no data yet.")
        else:
            lines.append(
                f"{label}: best {summary['best']:g} {unit}, "
                f"latest {summary['latest']:g} {unit}, "
                f"change since first entry {summary['change']:+g} {unit} "
                f"({summary['entries']} entries)."
            )

    body = athletic_summary("body_weight")
    if body is None:
        lines.append("Body weight: no data yet.")
    else:
        lines.append(
            f"Body weight: latest {body['latest']:g} lbs, "
            f"change since first entry {body['change']:+g} lbs."
        )

    golf = golf_summary()
    if golf is None:
        lines.append("Golf (18 holes): no rounds yet.")
    else:
        lines.append(
            f"Golf (18 holes, lower is better): {golf['rounds']} rounds, "
            f"best {golf['best']}, average {golf['average']}, "
            f"latest {golf['latest']}, "
            f"change since first round {golf['change']:+d}."
        )

    climbs = climb_summary()
    if climbs is None:
        lines.append("Climbing: no climbs yet.")
    else:
        lines.append(
            f"Climbing: {climbs['climbs']} climbs, {climbs['sent']} sent "
            f"({climbs['send_rate']}%), hardest send "
            f"{climbs['hardest'] or 'none yet'}."
        )

    taken, left = get_progress()
    lines.append(f"Software degree: {taken} classes completed, {left} left.")

    return "\n".join(lines)


def get_coach_message(client=None):
    """Ask Claude for a coach message based on your progress.
    Pass in a `client` only in tests; normally we create the real one."""
    progress = build_progress_text()

    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise CoachError(
                "No API key found. Add ANTHROPIC_API_KEY to your .env file."
            )
        client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Here is my current progress:\n\n" + progress,
                }
            ],
        )
    except anthropic.AuthenticationError:
        raise CoachError("The API key was rejected. Check it in your .env file.")
    except anthropic.APIConnectionError:
        raise CoachError("Could not reach the API. Check your internet connection.")
    except anthropic.APIError as error:
        raise CoachError(f"The API returned an error: {error}")

    parts = [
        block.text
        for block in response.content
        if getattr(block, "type", "text") == "text"
    ]
    message = "".join(parts).strip()
    if not message:
        raise CoachError("The coach returned no text. Please try again.")
    return message