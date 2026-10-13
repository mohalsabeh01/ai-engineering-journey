from main import run_agent


def trim_history(history, max_messages=6):
    """Behält die System-Nachricht und die letzten max_messages Nachrichten.
    Der Schnitt beginnt immer bei einer user-Nachricht."""
    if history is None:
        return None

    system = history[0]
    rest = history[1:]
    if len(rest) <= max_messages:
        return history  # Noch kurz genug, nichts abschneiden

    rest = rest[-max_messages:]
    # Nicht mitten in einem Tool-Austausch beginnen
    while rest and rest[0]["role"] != "user":
        rest = rest[1:]

    hinweis = {
        "role": "system",
        "content": "Hinweis: Ältere Teile dieses Gesprächs wurden entfernt. "
                   "Du siehst nur die letzten Nachrichten. Wenn nach etwas Früherem gefragt wird, "
                   "sag ehrlich, dass du es nicht mehr weißt.",
    }
    return [system, hinweis] + rest


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
