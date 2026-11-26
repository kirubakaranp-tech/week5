import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from sql_templates import PRIORITIES, TEMPLATES, TemplateError, run_template

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = (
    "You help staff read company data. You can only use the tools you are given, and each tool runs "
    "one fixed, read-only query. Fill in the parameters from the user's question. "
    "If the request does not match a tool, or asks to change or delete data, do not call any tool "
    "and say that you can only run the listed read-only queries."
)
PARAMETER_SCHEMAS = {
    "id": {"type": "integer", "minimum": 1},
    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
    "employee_id": {"type": "string", "pattern": "^E[0-9]{3}$", "description": "Like E001"},
    "priority": {"type": "string", "enum": PRIORITIES},
}


def build_tools():
    tools = []
    for name, template in TEMPLATES.items():
        properties = {param: PARAMETER_SCHEMAS[kind] for param, kind in template["params"].items()}
        required = [param for param in template["params"] if param != "limit"]
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": template["description"],
                "parameters": {"type": "object", "properties": properties, "required": required},
            },
        })
    return tools


def ask_database(question):
    client = OpenAI(max_retries=5)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}],
        tools=build_tools(),
        temperature=0,
    )
    message = response.choices[0].message

    if not message.tool_calls:
        return {"template": None, "reply": (message.content or "").strip()}

    call = message.tool_calls[0]
    try:
        params = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        return {"template": call.function.name, "error": "The model sent parameters that are not valid JSON"}

    try:
        rows = run_template(call.function.name, params)
    except TemplateError as error:
        return {"template": call.function.name, "params": params, "error": str(error)}
    return {"template": call.function.name, "params": params, "rows": rows}


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Show the last orders of customer 3"
    result = ask_database(question)
    print(f"Question: {question}")
    for key, value in result.items():
        print(f"{key}: {value}")
