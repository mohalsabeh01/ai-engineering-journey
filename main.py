from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

# --- Retry sichtbar machen ---
RETRY_SIGNALS = ("429", "500", "502", "503", "504")


def is_retry_signal(record):
    return any(code in record.getMessage() for code in RETRY_SIGNALS)


console = logging.StreamHandler()
console.setFormatter(logging.Formatter("[Retry] Server-Problem, neuer Versuch folgt: %(message)s"))
console.addFilter(is_retry_signal)
logging.getLogger("httpx").addHandler(console)

# --- Client mit Retry-Einstellungen ---
# Hinweis (getestet am 30.09.2026): client.interactions scheint diese
# Einstellungen zu ignorieren. Bei 429 wurde ~28s gewartet (max_delay=20),
# vermutlich folgt das SDK der Wartezeit, die der Server vorgibt.
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=3,
            initial_delay=2.0,
            max_delay=20.0,
            http_status_codes=[429, 500, 502, 503, 504],
        )
    ),
)

PRICE_PER_MILLION_INPUT = 0.075
PRICE_PER_MILLION_OUTPUT = 0.30


def calculate_cost(usage):
    output_tokens = usage.total_output_tokens + usage.total_thought_tokens
    input_cost = (usage.total_input_tokens / 1_000_000) * PRICE_PER_MILLION_INPUT
    output_cost = (output_tokens / 1_000_000) * PRICE_PER_MILLION_OUTPUT
    return input_cost + output_cost


def get_order_status(order_id: str) -> str:
    fake_orders = {"123": "Wird geliefert", "456": "Zugestellt"}
    return fake_orders.get(order_id, "Bestellung nicht gefunden")


def get_driver_info(driver_id: str) -> str:
    fake_drivers = {
        "d1": "Ahmed, Fahrzeug: Mercedes Sprinter, Status: Unterwegs",
        "d2": "Sara, Fahrzeug: VW Transporter, Status: Verfügbar",
    }
    return fake_drivers.get(driver_id, "Fahrer nicht gefunden")


order_tool = {
    "type": "function",
    "name": "get_order_status",
    "description": "Gibt den Lieferstatus einer Bestellung zurück",
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "Die Bestellnummer"}
        },
        "required": ["order_id"],
    },
}

driver_tool = {
    "type": "function",
    "name": "get_driver_info",
    "description": "Gibt Informationen über einen Fahrer zurück",
    "parameters": {
        "type": "object",
        "properties": {
            "driver_id": {"type": "string", "description": "Die Fahrer-ID"}
        },
        "required": ["driver_id"],
    },
}

available_functions = {
    "get_order_status": get_order_status,
    "get_driver_info": get_driver_info,
}

tools = [order_tool, driver_tool]

# --- Agenten-Logik ---
def run_agent(user_input, max_steps=5):
    total_cost = 0.0
    tool_calls = []  # NEU: merkt sich jeden Tool-Aufruf für Evals
    logging.info(f"Neue Anfrage: {user_input}")

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=user_input,
        tools=tools,
    )
    total_cost += calculate_cost(interaction.usage)

    steps_taken = 0
    while steps_taken < max_steps:
        function_calls = [s for s in interaction.steps if s.type == "function_call"]

        if not function_calls:
            logging.info(f"Kosten dieser Anfrage: ${total_cost:.6f}")
            print(f"\nGesamtkosten dieser Anfrage: ${total_cost:.6f}")
            # NEU: Dictionary statt nur Text
            return {
                "answer": interaction.output_text,
                "tool_calls": tool_calls,
                "cost": total_cost,
            }

        results_input = []
        for call in function_calls:
            tool_calls.append({"name": call.name, "args": dict(call.arguments)})  # NEU
            try:
                func = available_functions[call.name]
                result = func(**call.arguments)
                logging.info(
                    f"Tool: {call.name} | Args: {call.arguments} | Result: {result}"
                )
                print(f"[Schritt {steps_taken + 1}] {call.name}({call.arguments}) -> {result}")
            except Exception as e:
                result = f"Fehler: {e}"
                logging.error(f"Tool {call.name} fehlgeschlagen: {e}")
                print(f"[Schritt {steps_taken + 1}] {call.name} fehlgeschlagen: {e}")

            results_input.append(
                {
                    "type": "function_result",
                    "name": call.name,
                    "call_id": call.id,
                    "result": [{"type": "text", "text": result}],
                }
            )

        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            previous_interaction_id=interaction.id,
            tools=tools,
            input=results_input,
        )
        total_cost += calculate_cost(interaction.usage)
        steps_taken += 1

    logging.warning("Maximale Anzahl an Schritten erreicht.")
    logging.info(f"Kosten dieser Anfrage: ${total_cost:.6f}")
    print(f"\nGesamtkosten dieser Anfrage: ${total_cost:.6f}")
    return {
        "answer": "Maximale Anzahl an Schritten erreicht.",
        "tool_calls": tool_calls,
        "cost": total_cost,
    }


# --- Verwendung ---
if __name__ == "__main__":
    try:
        ergebnis = run_agent("Wie ist der Status von Bestellung 123 und was weißt du über Fahrer d1?")
        print(f"\nFinale Antwort: {ergebnis['answer']}")
    except Exception as e:
        logging.error(f"Anfrage endgültig fehlgeschlagen: {e}")
        print("\nDie Anfrage ist fehlgeschlagen.")
        print("Details stehen in agent.log.")