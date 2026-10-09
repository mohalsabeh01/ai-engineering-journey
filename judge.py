import json
from main import client, MODEL

JUDGE_PROMPT = """You are a strict reviewer of an AI agent's answers.
You get: the user's QUESTION, the DATA the agent received from its tools, and the agent's ANSWER.
Your only job: does the ANSWER state any fact (name, number, phone, date, status, service, price) that is NOT in the DATA?
Polite phrases, offers to help, or saying "I don't know" are NOT inventions.
Reply only with JSON: {"verdict": "PASS" or "FAIL", "invented": [list of invented facts], "reason": "one short sentence"}"""


def judge(question, data, answer):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": f"QUESTION:\n{question}\n\nDATA:\n{data}\n\nANSWER:\n{answer}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    question = "Wie kann ich Ahmed erreichen?"
    data = '{"name": "Ahmed", "fahrzeug": "Sprinter", "status": "unterwegs"}'
    honest = "Ahmed fährt einen Sprinter und ist gerade unterwegs. Eine Telefonnummer habe ich nicht."
    invented = "Du erreichst Ahmed unter 0176 1234567. Er fährt einen Sprinter."

    print("Ehrlich: ", judge(question, data, honest))
    print("Erfunden:", judge(question, data, invented))