import sqlite3
from datetime import date

from app.coach import CoachError, get_coach_message
from app.db import (
    add_athletic_skill,
    add_climb,
    add_coach_message,
    add_completed_class,
    add_golf_round,
    create_tables,
    get_progress,
    get_recent_coach_messages,
)
from app.leveling import player_status
from app.stats import athletic_summary, climb_summary, golf_summary
from app.validation import is_valid_date


def ask_date():
    """Ask for a date. Pressing Enter uses today's date."""
    while True:
        text = input("Date (YYYY-MM-DD, or press Enter for today): ").strip()
        if text == "":
            return date.today().isoformat()
        if is_valid_date(text):
            return text
        print("That's not a valid date. Use the format YYYY-MM-DD, like 2026-10-27.")


def ask_text(prompt, optional=False):
    """Ask for text. If optional, pressing Enter returns None."""
    while True:
        text = input(prompt).strip()
        if text != "":
            return text
        if optional:
            return None
        print("This can't be empty. Please type something.")


def ask_int(prompt, minimum=0, optional=False):
    """Ask for a whole number that is at least `minimum`."""
    while True:
        text = input(prompt).strip()
        if text == "" and optional:
            return None
        try:
            value = int(text)
        except ValueError:
            print("Please enter a whole number, like 8.")
            continue
        if value < minimum:
            print(f"Please enter a number that is at least {minimum}.")
            continue
        return value


def ask_float(prompt, minimum=0):
    """Ask for a number that can have decimals, like 135.5."""
    while True:
        text = input(prompt).strip()
        try:
            value = float(text)
        except ValueError:
            print("Please enter a number, like 135 or 135.5.")
            continue
        if value < minimum:
            print(f"Please enter a number that is at least {minimum}.")
            continue
        return value


def ask_yes_no(prompt):
    """Ask a yes/no question. Returns 1 for yes and 0 for no."""
    while True:
        text = input(prompt + " (y/n): ").strip().lower()
        if text in ("y", "yes"):
            return 1
        if text in ("n", "no"):
            return 0
        print("Please type y or n.")


def show_athletic_menu():
    print("\n--- Athletic Skills ---")
    print("1. Vertical jump")
    print("2. Deadlift")
    print("3. Upper body lift")
    print("4. Body weight")
    print("0. Save and go back")


def log_athletic_skill():
    print("\n--- Log Athletic Skills ---")
    day = ask_date()

    # Everything starts empty. Only what you choose gets filled in.
    jump_height = None
    deadlift_weight = None
    upperbody_weight = None
    body_weight = None

    while True:
        show_athletic_menu()
        choice = input("Choose what to log: ").strip()
        if choice == "1":
            jump_height = ask_float("Vertical jump height (inches): ")
        elif choice == "2":
            deadlift_weight = ask_float("Deadlift weight (lbs): ")
        elif choice == "3":
            upperbody_weight = ask_float("Upper body lift weight (lbs): ")
        elif choice == "4":
            body_weight = ask_float("Body weight (lbs): ", minimum=1)
        elif choice == "5":
            show_report()
        elif choice == "6":
            show_coach()
        elif choice == "7":
            show_past_coach_messages()
        elif choice == "0":
            break
        else:
            print("Invalid choice. Please type a number from the menu.")

    # If you didn't enter anything, there's nothing to save.
    if all(value is None for value in
           (jump_height, deadlift_weight, upperbody_weight, body_weight)):
        print("Nothing to save.")
        return

    add_athletic_skill(day, jump_height, deadlift_weight,
                       upperbody_weight, body_weight)
    print("Athletic skills saved!")


def log_golf_round():
    print("\n--- Log Golf Round ---")
    day = ask_date()
    course = ask_text("Course name: ")
    while True:
        holes = ask_int("Holes played (9 or 18): ", minimum=1)
        if holes in (9, 18):
            break
        print("Please enter 9 or 18.")
    score = ask_int("Total score: ", minimum=1)
    putts = ask_int("Total putts (optional, press Enter to skip): ",
                    minimum=0, optional=True)
    add_golf_round(day, course, holes, score, putts)
    print("Golf round saved!")


def log_climb():
    print("\n--- Log Climb ---")
    day = ask_date()
    location = ask_text("Location (gym or crag): ")
    grade = ask_text("Grade (e.g. V4 or 5.10a): ")
    sent = ask_yes_no("Did you complete (send) it?")
    attempts = ask_int("Number of attempts: ", minimum=1)
    add_climb(day, location, grade, sent, attempts)
    print("Climb saved!")


def log_software_progress():
    print("\n--- Log Completed Class ---")
    day = ask_date()
    class_name = ask_text("Class you just completed: ")
    try:
        add_completed_class(day, class_name)
    except sqlite3.IntegrityError:
        print("That class is already logged.")
        return
    taken, left = get_progress()
    print(f"Saved! Classes completed: {taken} | Classes left: {left}")


def show_report():
    print("\n=== Progress Report ===")

    status = player_status()
    print(f"Rank {status['rank']} | Level {status['level']} | "
          f"{status['xp']} XP ({status['xp_to_next']} XP to next level)")

    print("\n-- Athletic skills --")
    lifts = [
        ("jump_height", "Vertical jump", "in"),
        ("deadlift_weight", "Deadlift", "lbs"),
        ("upperbody_weight", "Upper body lift", "lbs"),
    ]
    for column, label, unit in lifts:
        summary = athletic_summary(column)
        if summary is None:
            print(f"{label}: no data yet")
        else:
            print(f"{label}: best {summary['best']:g} {unit} | "
                  f"latest {summary['latest']:g} {unit} | "
                  f"change {summary['change']:+g} {unit}")

    body = athletic_summary("body_weight")
    if body is None:
        print("Body weight: no data yet")
    else:
        print(f"Body weight: latest {body['latest']:g} lbs | "
              f"change {body['change']:+g} lbs")

    print("\n-- Golf (18-hole rounds) --")
    golf = golf_summary()
    if golf is None:
        print("No 18-hole rounds yet")
    else:
        print(f"Rounds: {golf['rounds']} | best {golf['best']} | "
              f"average {golf['average']} | latest {golf['latest']}")
        print(f"Change since first round: {golf['change']:+d} (lower is better)")

    print("\n-- Climbing --")
    climbs = climb_summary()
    if climbs is None:
        print("No climbs yet")
    else:
        hardest = climbs["hardest"] or "none yet"
        print(f"Climbs: {climbs['climbs']} | sent {climbs['sent']} "
              f"({climbs['send_rate']}%) | hardest send: {hardest}")

    print("\n-- Software development --")
    taken, left = get_progress()
    print(f"Classes completed: {taken} | classes left: {left}")

def show_coach():
    print("\n=== Coach ===")
    print("Contacting the System...")
    try:
        message = get_coach_message()
    except CoachError as error:
        print(f"Coach unavailable: {error}")
        return
    print("\n" + message)
    add_coach_message(date.today().isoformat(), message)


def show_past_coach_messages():
    print("\n=== Past Coach Messages ===")
    rows = get_recent_coach_messages()
    if not rows:
        print("No coach messages yet.")
        return
    for day, message in rows:
        print(f"\n[{day}]\n{message}")


def show_menu():
    print("\n=== Progress Tracker ===")
    print("1. Log athletic skills")
    print("2. Log golf round")
    print("3. Log climb")
    print("4. Log software development progress")
    print("5. View progress report")
    print("6. Ask the coach")
    print("7. Past coach messages")
    print("0. Exit")


def main():
    create_tables()
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()
        if choice == "1":
            log_athletic_skill()
        elif choice == "2":
            log_golf_round()
        elif choice == "3":
            log_climb()
        elif choice == "4":
            log_software_progress()
        elif choice == "5":
            show_report()
        elif choice == "6":
            show_coach()
        elif choice == "7":
            show_past_coach_messages()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please type a number from the menu.")



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")