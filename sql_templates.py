import os
import re

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

READONLY_DATABASE_URL = os.getenv("READONLY_DATABASE_URL", "")
PRIORITIES = ["low", "medium", "high"]

TEMPLATES = {
    "orders_by_customer": {
        "description": "List the orders of one customer, newest first.",
        "sql": "SELECT id, order_date, status, total_amount FROM orders "
               "WHERE customer_id = %(customer_id)s ORDER BY order_date DESC LIMIT %(limit)s",
        "params": {"customer_id": "id", "limit": "limit"},
    },
    "leave_balance": {
        "description": "Show how many days of each leave type an employee has left.",
        "sql": "SELECT leave_type, days_left FROM leave_balances "
               "WHERE employee_id = %(employee_id)s ORDER BY leave_type",
        "params": {"employee_id": "employee_id"},
    },
    "open_tickets": {
        "description": "List the open support tickets with one priority.",
        "sql": "SELECT id, title, created_at FROM tickets "
               "WHERE status = 'open' AND priority = %(priority)s ORDER BY created_at",
        "params": {"priority": "priority"},
    },
}


class TemplateError(ValueError):
    pass


def check_value(name, kind, value):
    if kind in ("id", "limit"):
        if type(value) is not int:
            raise TemplateError(f"{name} must be a whole number, got {value!r}")
        if kind == "id" and value < 1:
            raise TemplateError(f"{name} must be 1 or more, got {value}")
        if kind == "limit" and not 1 <= value <= 50:
            raise TemplateError(f"{name} must be between 1 and 50, got {value}")
        return

    if kind == "employee_id":
        if not isinstance(value, str) or not re.fullmatch(r"E\d{3}", value):
            raise TemplateError(f"{name} must look like E001, got {value!r}")
        return

    if kind == "priority":
        if value not in PRIORITIES:
            raise TemplateError(f"{name} must be one of {PRIORITIES}, got {value!r}")
        return

    raise TemplateError(f"Unknown parameter type {kind}")


def validate(template_name, params):
    if template_name not in TEMPLATES:
        raise TemplateError(f"Unknown template {template_name!r}. Allowed: {', '.join(TEMPLATES)}")
    if not isinstance(params, dict):
        raise TemplateError("Parameters must be a dictionary")

    expected = TEMPLATES[template_name]["params"]
    if "limit" in expected and "limit" not in params:
        params = {**params, "limit": 10}

    unexpected = set(params) - set(expected)
    missing = set(expected) - set(params)
    if unexpected:
        raise TemplateError(f"Unexpected parameter(s): {', '.join(sorted(unexpected))}")
    if missing:
        raise TemplateError(f"Missing parameter(s): {', '.join(sorted(missing))}")

    for name, kind in expected.items():
        check_value(name, kind, params[name])
    return params


def connect_readonly():
    conn = psycopg.connect(READONLY_DATABASE_URL, connect_timeout=5, row_factory=dict_row)
    conn.read_only = True
    return conn


def run_template(template_name, params):
    params = validate(template_name, params)
    with connect_readonly() as conn:
        return conn.execute(TEMPLATES[template_name]["sql"], params).fetchall()
