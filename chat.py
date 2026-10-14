from main import run_agent, client, MODEL, calculate_cost


def summarize(messages):
    """Fasst alte Nachrichten in wenigen Sätzen zusammen (ein zusätzlicher Aufruf ohne Tools)."""
    zeilen = []
    for m in messages:
        if m["role"] == "system":
            zeilen.append(f"Frühere Zusammenfassung: {m['content']}")
        elif m["role"] == "user":
            zeilen.append(f"Kunde: {m['content']}")
        elif m["role"] == "tool":
            zeilen.append(f"Tool-Ergebnis: {m['content']}")
        elif m["role"] == "assistant" and m.get("content"):
            zeilen.append(f"Assistent: {m['content']}")
    verlauf = "\n".join(zeilen)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "Fasse zusammen, wonach der Kunde gefragt hat, in der Reihenfolge seiner Fragen, "
                "jeweils mit dem Ergebnis. Beginne mit 'Der Kunde fragte zuerst'. "
                "Wenn eine frühere Zusammenfassung dabei ist, übernimm ihren Inhalt am Anfang. "
                "Höchstens 3 Sätze. Erfinde nichts."
            )},
            {"role": "user", "content": verlauf},
        ],
    )
    calculate_cost(response.usage)  # Tokens landen in agent.log
    return response.choices[0].message.content


def trim_history(history, max_messages=6):
    """Behält die System-Nachricht und die letzten max_messages Nachrichten.
    Der Schnitt beginnt immer bei einer user-Nachricht.
    Der abgeschnittene Teil wird zusammengefasst."""
    if history is None:
        return None

    system = history[0]
    rest = history[1:]
    if len(rest) <= max_messages:
        return history  # Noch kurz genug, nichts abschneiden

    neu = rest[-max_messages:]
    # Nicht mitten in einem Tool-Austausch beginnen
    while neu and neu[0]["role"] != "user":
        neu = neu[1:]

    alt = rest[:len(rest) - len(neu)]  # Alles, was abgeschnitten wird
    zusammenfassung = summarize(alt)

    hinweis = {
        "role": "system",
        "content": f"Zusammenfassung des früheren Gesprächs: {zusammenfassung} "
                   "Wenn nach Details gefragt wird, die nicht in der Zusammenfassung stehen, "
                   "sag ehrlich, dass du sie nicht mehr weißt.",
    }
    return [system, hinweis] + neu


def main():
    history = None  # Noch kein Gespräch
    print("Chat mit dem Lieferdienst-Agenten. 'exit' zum Beenden.")

    while True:
        user_input = input("\nDu: ").strip()

        if user_input.lower() in ("exit", "quit"):
            print("Tschüss!")
            break
        if not user_input:
            continue  # Leere Eingabe ignorieren

        try:
            ergebnis = run_agent(user_input, history=trim_history(history))
        except Exception as e:
            print(f"Fehler: {e} (Details in agent.log)")
            continue  # history bleibt, wie sie war

        print(f"Agent: {ergebnis['answer']}")
        history = ergebnis["messages"]  # Das Gespräch für die nächste Frage merken


if __name__ == "__main__":
    main()
