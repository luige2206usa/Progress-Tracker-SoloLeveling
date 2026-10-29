from app.db import get_connection

# The only columns the athletic summary is allowed to read.
ATHLETIC_COLUMNS = (
    "jump_height",
    "deadlift_weight",
    "upperbody_weight",
    "body_weight",
)


def _fetch_all(sql, params=()):
    """Run a SELECT and return all rows. Used only inside this file."""
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def athletic_summary(column):
    """Summarize one athletic measurement over time.
    Returns None if nothing has been logged yet."""
    if column not in ATHLETIC_COLUMNS:
        raise ValueError(f"Unknown column: {column}")

    rows = _fetch_all(
        f"SELECT {column} FROM athletic_skills "
        f"WHERE {column} IS NOT NULL ORDER BY date, id"
    )
    values = [row[0] for row in rows]
    if not values:
        return None

    return {
        "best": max(values),
        "first": values[0],
        "latest": values[-1],
        "change": values[-1] - values[0],
        "entries": len(values),
    }


def golf_summary():
    """Summarize 18-hole rounds. Lower scores are better.
    Returns None if no 18-hole rounds are logged."""
    rows = _fetch_all(
        "SELECT score FROM golf_rounds WHERE holes = 18 ORDER BY date, id"
    )
    scores = [row[0] for row in rows]
    if not scores:
        return None

    return {
        "rounds": len(scores),
        "best": min(scores),
        "average": round(sum(scores) / len(scores), 1),
        "latest": scores[-1],
        "change": scores[-1] - scores[0],
    }


def grade_value(grade):
    """Turn a V-scale grade like 'V4' into the number 4.
    Returns None for anything we can't read, like '5.10a'."""
    text = grade.strip().upper()
    if text.startswith("V") and text[1:].isdigit():
        return int(text[1:])
    return None


def climb_summary():
    """Summarize climbing. Returns None if no climbs are logged."""
    rows = _fetch_all("SELECT grade, sent, attempts FROM climbs")
    if not rows:
        return None

    total = len(rows)
    sent_count = sum(1 for grade, sent, attempts in rows if sent == 1)

    sent_values = [
        grade_value(grade) for grade, sent, attempts in rows if sent == 1
    ]
    sent_values = [value for value in sent_values if value is not None]

    return {
        "climbs": total,
        "sent": sent_count,
        "send_rate": round(100 * sent_count / total),
        "hardest": f"V{max(sent_values)}" if sent_values else None,
    }