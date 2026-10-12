from main import run_agent


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
            ergebnis = run_agent(user_input, history=history)
        except Exception as e:
            print(f"Fehler: {e} (Details in agent.log)")
            continue  # history bleibt, wie sie war

        print(f"Agent: {ergebnis['answer']}")
        history = ergebnis["messages"]  # Das Gespräch für die nächste Frage merken


if __name__ == "__main__":
    main()
