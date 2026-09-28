from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_order_status(order_id: str) -> str:
    fake_orders = {
        "123": "Wird geliefert",
        "456": "Zugestellt",
    }
    
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
    "description": "Gibt den Lieferstatus einer Bestellung anhand der Bestellnummer zurück",
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string", "description": "Die Bestellnummer"}
        },
        "required": ["order_id"]
    }

}

driver_tool = {
    "type": "function",
    "name": "get_driver_info",
    "description": "Gibt Informationen über einen Fahrer anhand seiner ID zurück (Name, Fahrzeug, Status)",
    "parameters": {
        "type": "object",
        "properties": {
            "driver_id": {"type": "string", "description": "Die Fahrer-ID"}
        },
        "required": ["driver_id"]
    }
}

available_functions = {
    "get_order_status": get_order_status,
    "get_driver_info": get_driver_info,
}

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="Welche Informationen hast du über Fahrer d1?",
    tools=[order_tool, driver_tool]
)

found_function_call = False

for step in interaction.steps:
    
    if step.type == "function_call":
        found_function_call = True
        print(f"Gemini möchte aufrufen: {step.name}")
        print(f"Mit den Argumenten: {step.arguments}")

        try:
            function_to_call = available_functions[step.name]
            result = function_to_call(**step.arguments)
            print(f"Ergebnis der Funktion: {result}")

            final_interaction = client.interactions.create(
                model="gemini-3.6-flash",
                previous_interaction_id=interaction.id,
                tools=[order_tool, driver_tool],
                input=[
                    {
                        "type": "function_result",
                        "name": step.name,
                        "call_id": step.id,
                        "result": [{"type": "text", "text": result}]
                    }
                ]
            )

            print(f"Gemini's Antwort: {final_interaction.output_text}")

        except Exception as e:
            print(f"Fehler beim Aufrufen der Funktion: {e}")

if not found_function_call:
    print(f"Gemini hat keine Funktion aufgerufen. Direkte Antowrt: {interaction.output_text}")