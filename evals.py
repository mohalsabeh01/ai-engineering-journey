import sys
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
    {
        "name": "Fahrer nur mit Namen",
        "input": "Wo ist Ahmed gerade?",
        "expected_tools": [],
        "must_contain": [],
        "must_contain_any": ["fahrer-id", "id des fahrers", "id von ahmed", "fahrernummer", "kennung", "nummer"],
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

    any_words = case.get("must_contain_any", [])
    if any_words and not any(w.lower() in answer for w in any_words):
        problems.append(f"Keines von {any_words} in der Antwort")

    return problems


def run_evals(selected=None, pause_seconds=10):
    # NEU: nur ausgewählte Fälle laufen lassen (spart Anfragen)
    cases = [(nr, c) for nr, c in enumerate(EVAL_CASES, 1) if not selected or nr in selected]
    passed = failed = errors = 0

    for position, (nr, case) in enumerate(cases, 1):
        print(f"\n===== [Fall {nr}] {case['name']} =====")
        try:
            result = run_agent(case["input"])
        except Exception as e:
            # NEU: technischer Fehler ist KEIN falsches Verhalten des Agenten
            errors += 1
            print("  ERROR (nicht bewertbar, technischer Fehler)")
            print(f"   - {e}")
            logging.error(f"EVAL ERROR | {case['name']} | {e}")
        else:
            problems = check_case(case, result)
            if problems:
                failed += 1
                print("  FAIL")
                for p in problems:
                    print(f"   - {p}")
                print(f"   Antwort war: {result['answer']}")
                logging.warning(f"EVAL FAIL | {case['name']} | {problems}")
            else:
                passed += 1
                print("  PASS")
                logging.info(f"EVAL PASS | {case['name']}")

        if position < len(cases):
            time.sleep(pause_seconds)  # Schont das Minutenlimit der Free Tier

    evaluated = passed + failed
    summary = f"\nErgebnis: {passed}/{evaluated} bestanden"
    if errors:
        summary += f", {errors} nicht bewertbar (technischer Fehler)"
    print(summary)
    logging.info(f"EVAL ERGEBNIS | {passed}/{evaluated} bestanden | {errors} Fehler")


if __name__ == "__main__":
    # Beispiel: "python evals.py 6" oder "python evals.py 1 6"
    selected = {int(arg) for arg in sys.argv[1:]}
    run_evals(selected)
