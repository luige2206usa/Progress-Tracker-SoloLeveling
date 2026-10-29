from app.db import get_connection

# How much XP each activity is worth.
XP_GOLF_ROUND = 10
XP_CLIMB = 5
XP_CLIMB_SENT_BONUS = 5
XP_ATHLETIC_ENTRY = 10
XP_CLASS = 100
XP_PER_LEVEL = 100

# (minimum level, rank letter), like hunter ranks in Solo Leveling
RANKS = [(1, "E"), (5, "D"), (10, "C"), (20, "B"), (30, "A"), (40, "S")]


def _count(sql):
    """Run a COUNT query and return the number."""
    conn = get_connection()
    number = conn.execute(sql).fetchone()[0]
    conn.close()
    return number


def total_xp():
    """Add up XP from everything you've logged."""
    golf = _count("SELECT COUNT(*) FROM golf_rounds")
    climbs = _count("SELECT COUNT(*) FROM climbs")
    sent = _count("SELECT COUNT(*) FROM climbs WHERE sent = 1")
    athletic = _count("SELECT COUNT(*) FROM athletic_skills")
    classes = _count("SELECT COUNT(*) FROM software_development_progress")

    return (
        golf * XP_GOLF_ROUND
        + climbs * XP_CLIMB
        + sent * XP_CLIMB_SENT_BONUS
        + athletic * XP_ATHLETIC_ENTRY
        + classes * XP_CLASS
    )


def level_from_xp(xp):
    """Every XP_PER_LEVEL points is one level. Everyone starts at level 1."""
    return xp // XP_PER_LEVEL + 1


def rank_for_level(level):
    """Return the highest rank whose minimum level you've reached."""
    rank = RANKS[0][1]
    for minimum_level, letter in RANKS:
        if level >= minimum_level:
            rank = letter
    return rank


def player_status():
    """Return your current XP, level, rank, and XP needed for the next level."""
    xp = total_xp()
    level = level_from_xp(xp)
    return {
        "xp": xp,
        "level": level,
        "rank": rank_for_level(level),
        "xp_to_next": XP_PER_LEVEL - xp % XP_PER_LEVEL,
    }