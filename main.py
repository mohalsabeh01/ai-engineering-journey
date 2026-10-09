from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import logging
import re


load_dotenv()

logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

# --- Retry sichtbar machen (httpx für Gemini, httpx2 für das openai-SDK) ---
RETRY_PATTERN = re.compile(r"HTTP/[\d.]+ (429|500|502|503|504)")


def is_retry_signal(record):
    return bool(RETRY_PATTERN.search(record.getMessage()))


console = logging.StreamHandler()
console.setFormatter(logging.Formatter("[Retry] Server-Problem, neuer Versuch folgt: %(message)s"))
console.addFilter(is_retry_signal)
for logger_name in ("httpx", "httpx2"):
    logging.getLogger(logger_name).addHandler(console)

# --- NEU: Groq über das OpenAI-kompatible SDK ---
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    max_retries=2,  # 1 Versuch + max. 2 Wiederholungen (wird im Log überprüft)
)

# Modellname aus .env (GROQ_MODEL), sonst Standard. Modelle werden oft abgeschaltet,
# deshalb steht der Name nicht fest im Code.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# NEU: Arbeitsvertrag für das Modell, steht vor jeder Unterhaltung
SYSTEM_PROMPT = (
    "Du bist ein Assistent für einen Lieferdienst. "
    "Du kannst nur zwei Dinge: den Status einer Bestellung abfragen (dafür brauchst du die Bestellnummer) "
    "und Informationen zu einem Fahrer abfragen (dafür brauchst du die Fahrer-ID). "
    "Erfinde keine Informationen. Wenn du etwas mit deinen Tools nicht herausfinden kannst, "
    "sag ehrlich, dass du es nicht weißt, und sag, wobei du helfen kannst. "
    "Du kennst keine Lieferzeiten und keine Kontaktdaten. "
    "Wenn die Bestellnummer oder die Fahrer-ID fehlt, frag danach."
)

# Free Tier: kostenlos. Preise nur eintragen, falls später bezahlt wird.
PRICE_PER_MILLION_INPUT = 0.0
PRICE_PER_MILLION_OUTPUT = 0.0


def calculate_cost(usage):
    logging.info(f"Tokens: input={usage.prompt_tokens}, output={usage.completion_tokens}")
    input_cost = (usage.prompt_tokens / 1_000_000) * PRICE_PER_MILLION_INPUT
    output_cost = (usage.completion_tokens / 1_000_000) * PRICE_PER_MILLION_OUTPUT
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


# NEU: OpenAI-Format verschachtelt die Definition unter "function"
order_tool = {
    "type": "function",
    "function": {
        "name": "get_order_status",
        "description": "Gibt den Lieferstatus einer Bestellung zurück",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Die Bestellnummer"}
            },
            "required": ["order_id"],
        },
    },
}

driver_tool = {
    "type": "function",
    "function": {
        "name": "get_driver_info",
        "description": "Gibt Name, Fahrzeug und Status eines Fahrers zurück. Keine Telefonnummer, keine Adresse.",
        "parameters": {
            "type": "object",
            "properties": {
                "driver_id": {"type": "string", "description": "Die Fahrer-ID"}
            },
            "required": ["driver_id"],
        },
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
    tool_calls = []
    logging.info(f"Neue Anfrage [{MODEL}]: {user_input}")

    # NEU: Wir verwalten den Gesprächsverlauf selbst (kein previous_interaction_id)
    messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_input},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    total_cost += calculate_cost(response.usage)

    steps_taken = 0
    while steps_taken < max_steps:
        message = response.choices[0].message

        if not message.tool_calls:
            logging.info(f"Kosten dieser Anfrage: ${total_cost:.6f}")
            print(f"\nGesamtkosten dieser Anfrage: ${total_cost:.6f}")
            return {
                "answer": message.content,
                "tool_calls": tool_calls,
                "cost": total_cost,
            }

        # NEU: Die Tool-Anfrage des Modells kommt selbst in den Verlauf
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })

        for tc in message.tool_calls:
            name = tc.function.name
            # NEU: Argumente kommen als JSON-Text, nicht als Dictionary
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            try:
                func = available_functions[name]
                result = func(**args)
                logging.info(f"Tool: {name} | Args: {args} | Result: {result}")
                print(f"[Schritt {steps_taken + 1}] {name}({args}) -> {result}")
            except Exception as e:
                result = f"Fehler: {e}"
                logging.error(f"Tool {name} fehlgeschlagen: {e}")
                print(f"[Schritt {steps_taken + 1}] {name} fehlgeschlagen: {e}")

            tool_calls.append({"name": name, "args": args, "result": result})

            # NEU: Jedes Ergebnis als eigene "tool"-Nachricht mit passender ID
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,  # der komplette Verlauf, jedes Mal
            tools=tools,
        )
        total_cost += calculate_cost(response.usage)
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
        print(f"Tools: {[tc['name'] for tc in ergebnis['tool_calls']]}")
    except Exception as e:
        logging.error(f"Anfrage endgültig fehlgeschlagen: {e}")
        print("\nDie Anfrage ist fehlgeschlagen.")
        print("Details stehen in agent.log.")
