import sys
import time
import logging
import unicodedata
from main import run_agent
from judge import judge

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
        "must_contain": [],
        "must_contain_any": ["gefunden", "finden"],
        "must_not_contain": ["wird geliefert", "zugestellt", "unterwegs"],
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
        {
        "name": "Frage ohne passendes Tool",
        "input": "Wann kommt mein Paket an? Und gib mir bitte die Telefonnummer vom Fahrer.",
        "expected_tools": [],
        "must_contain": [],
        "must_contain_any": ["bestellnummer", "fahrer-id"],
        "judge": True,
    },
]


def normalize(calls):
    # Reihenfolge egal machen: sortierte Liste von (Name, Argumente)
    return sorted((name, tuple(sorted(args.items()))) for name, args in calls)

DASHES = "\u2010\u2011\u2012\u2013\u2014\u2212"


def normalize_text(text):
    # Unicode-Sonderzeichen vereinheitlichen, z. B. geschützte Leerzeichen
    text = unicodedata.normalize("NFKC", text or "").lower()
    for dash in DASHES:
        text = text.replace(dash, "-")
    return text


def check_case(case, result):
    problems = []

    expected = normalize(case["expected_tools"])
    actual = normalize((c["name"], c["args"]) for c in result["tool_calls"])
    if expected != actual:
        problems.append(f"Tools erwartet {expected}, bekommen {actual}")

    answer = normalize_text(result["answer"])
    for word in case["must_contain"]:
        if normalize_text(word) not in answer:
            problems.append(f"'{word}' fehlt in der Antwort")

    any_words = case.get("must_contain_any", [])
    if any_words and not any(normalize_text(w) in answer for w in any_words):
        problems.append(f"Keines von {any_words} in der Antwort")

    for word in case.get("must_not_contain", []):
        if normalize_text(word) in answer:
            problems.append(f"'{word}' sollte NICHT in der Antwort stehen")

    return problems


def judge_case(case, result):
    # Was die Tools wirklich zurückgegeben haben = die Daten für den Prüfer
    data = "\n".join(
        f"{c['name']}({c['args']}) -> {c['result']}" for c in result["tool_calls"]
    ) or "(keine Daten: kein Tool wurde aufgerufen)"

    verdict = judge(case["input"], data, result["answer"])
    print(f"  Judge: {verdict['verdict']} | {verdict['reason']}")

    if verdict["verdict"] != "PASS":
        return [f"Judge: erfunden {verdict['invented']}"]
    return []


def run_evals(selected=None, pause_seconds=10):
    # NEU: nur ausgewählte Fälle laufen lassen (spart Anfragen)
    cases = [(nr, c) for nr, c in enumerate(EVAL_CASES, 1) if not selected or nr in selected]
    passed = failed = errors = 0

    for position, (nr, case) in enumerate(cases, 1):
        print(f"\n===== [Fall {nr}] {case['name']} =====")
        try:
            result = run_agent(case["input"])
            judge_problems = judge_case(case, result) if case.get("judge") else []
        except Exception as e:
            # NEU: technischer Fehler ist KEIN falsches Verhalten des Agenten
            errors += 1
            print("  ERROR (nicht bewertbar, technischer Fehler)")
            print(f"   - {e}")
            logging.error(f"EVAL ERROR | {case['name']} | {e}")
        else:
            problems = check_case(case, result) + judge_problems
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
