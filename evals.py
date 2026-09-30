import time
import logging
from main import run_agent

# Jeder Fall: Frage, erwartete Tool-Aufrufe, Schlüsselwörter in der Antwort
EVAL_CASES = [
    {
        "name": "Einzelne Bestellung",
        "input": "Wie ist der Status von Bestellung 123?",
        "expected_tools": [("get_order_status", {"order_id": "123"})],
        "must_contain": ["geliefert"],
    },
    {
        "name": "Einzelner Fahrer",
        "input": "Was weißt du über Fahrer d2?",
        "expected_tools": [("get_driver_info", {"driver_id": "d2"})],
        "must_contain": ["sara"],
    },
    {
        "name": "Unbekannte Bestellung",
        "input": "Wo ist meine Bestellung 999?",
        "expected_tools": [("get_order_status", {"order_id": "999"})],
        "must_contain": ["nicht gefunden"],
    },
    {
        "name": "Zwei Tools gleichzeitig",
        "input": "Status von Bestellung 456 und Infos zu Fahrer d1, bitte.",
        "expected_tools": [
            ("get_order_status", {"order_id": "456"}),
            ("get_driver_info", {"driver_id": "d1"}),
        ],
        "must_contain": ["zugestellt", "ahmed"],
    },
    {
        "name": "Kein Tool nötig",
        "input": "Hallo! Was kannst du für mich tun?",
        "expected_tools": [],
        "must_contain": [],
    },
]


def normalize(calls):
    # Reihenfolge egal machen: sortierte Liste von (Name, Argumente)
    return sorted((name, tuple(sorted(args.items()))) for name, args in calls)


def check_case(case, result):
    problems = []

    expected = normalize(case["expected_tools"])
    actual = normalize((c["name"], c["args"]) for c in result["tool_calls"])
    if expected != actual:
        problems.append(f"Tools erwartet {expected}, bekommen {actual}")

    answer = (result["answer"] or "").lower()
    for word in case["must_contain"]:
        if word.lower() not in answer:
            problems.append(f"'{word}' fehlt in der Antwort")

    return problems


def run_evals(pause_seconds=10):
    passed = 0
    total = len(EVAL_CASES)

    for i, case in enumerate(EVAL_CASES, 1):
        print(f"\n===== [{i}/{total}] {case['name']} =====")
        try:
            result = run_agent(case["input"])
            problems = check_case(case, result)
        except Exception as e:
            result = None
            problems = [f"Fehler beim Ausführen: {e}"]

        if problems:
            print("  FAIL")
            for p in problems:
                print(f"   - {p}")
            if result:
                print(f"   Antwort war: {result['answer']}")
            logging.warning(f"EVAL FAIL | {case['name']} | {problems}")
        else:
            print("  PASS")
            passed += 1
            logging.info(f"EVAL PASS | {case['name']}")

        if i < total:
            time.sleep(pause_seconds)  # Schont das Minutenlimit der Free Tier

    print(f"\nErgebnis: {passed}/{total} bestanden ({passed / total:.0%})")
    logging.info(f"EVAL ERGEBNIS | {passed}/{total}")


if __name__ == "__main__":
    run_evals()
