import json
from types import SimpleNamespace

import psycopg
import pytest

import llm_sql
import sql_templates
from sql_templates import TemplateError, run_template, validate


def database_available():
    if not sql_templates.READONLY_DATABASE_URL:
        return False
    try:
        psycopg.connect(sql_templates.READONLY_DATABASE_URL, connect_timeout=2).close()
        return True
    except psycopg.Error:
        return False


needs_database = pytest.mark.skipif(not database_available(), reason="company_db is not set up")


def test_good_parameters_pass():
    assert validate("orders_by_customer", {"customer_id": 3}) == {"customer_id": 3, "limit": 10}
    assert validate("leave_balance", {"employee_id": "E002"}) == {"employee_id": "E002"}
    assert validate("open_tickets", {"priority": "high"}) == {"priority": "high"}


@pytest.mark.parametrize(
    "template, params, message",
    [
        ("orders_by_customer", {"customer_id": "1; DROP TABLE orders"}, "must be a whole number"),
        ("orders_by_customer", {"customer_id": "3"}, "must be a whole number"),
        ("orders_by_customer", {"customer_id": True}, "must be a whole number"),
        ("orders_by_customer", {"customer_id": 3.5}, "must be a whole number"),
        ("orders_by_customer", {"customer_id": 0}, "must be 1 or more"),
        ("orders_by_customer", {"customer_id": 1, "limit": 1000}, "between 1 and 50"),
        ("orders_by_customer", {"customer_id": 1, "sql": "DROP TABLE orders"}, "Unexpected parameter"),
        ("orders_by_customer", {}, "Missing parameter"),
        ("leave_balance", {"employee_id": "E001' OR '1'='1"}, "must look like E001"),
        ("leave_balance", {"employee_id": 1}, "must look like E001"),
        ("open_tickets", {"priority": "urgent"}, "must be one of"),
        ("drop_orders", {}, "Unknown template"),
        ("open_tickets", "priority=high", "must be a dictionary"),
    ],
)
def test_bad_parameters_are_rejected(template, params, message):
    with pytest.raises(TemplateError, match=message):
        validate(template, params)


def test_templates_use_placeholders_not_string_building():
    for template in sql_templates.TEMPLATES.values():
        for name in template["params"]:
            assert f"%({name})s" in template["sql"]


def test_tools_match_the_templates():
    tools = llm_sql.build_tools()
    assert [tool["function"]["name"] for tool in tools] == ["orders_by_customer", "leave_balance", "open_tickets"]
    orders = tools[0]["function"]["parameters"]
    assert orders["properties"]["customer_id"]["type"] == "integer"
    assert orders["required"] == ["customer_id"]
    assert tools[2]["function"]["parameters"]["properties"]["priority"]["enum"] == ["low", "medium", "high"]


def fake_openai(monkeypatch, message):
    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            assert kwargs["temperature"] == 0
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(llm_sql, "OpenAI", FakeClient)


def tool_call(name, arguments):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def test_llm_that_refuses_runs_nothing(monkeypatch):
    fake_openai(monkeypatch, SimpleNamespace(content="I can only run read-only queries.", tool_calls=None))
    assert llm_sql.ask_database("drop the orders table") == {"template": None, "reply": "I can only run read-only queries."}


def test_llm_with_bad_parameters_runs_nothing(monkeypatch):
    fake_openai(monkeypatch, SimpleNamespace(content=None, tool_calls=[tool_call("orders_by_customer", {"customer_id": "1; DROP TABLE orders"})]))
    result = llm_sql.ask_database("orders of customer 1; DROP TABLE orders")
    assert "must be a whole number" in result["error"]


def test_llm_inventing_a_tool_runs_nothing(monkeypatch):
    fake_openai(monkeypatch, SimpleNamespace(content=None, tool_calls=[tool_call("drop_table", {})]))
    assert "Unknown template" in llm_sql.ask_database("drop it")["error"]


@needs_database
def test_templates_return_rows():
    assert [row["id"] for row in run_template("orders_by_customer", {"customer_id": 3})] == [1005, 1004]
    assert len(run_template("leave_balance", {"employee_id": "E001"})) == 3
    assert [row["id"] for row in run_template("open_tickets", {"priority": "high"})] == [1, 3]


@needs_database
@pytest.mark.parametrize("statement", ["DROP TABLE orders", "DELETE FROM orders", "INSERT INTO tickets VALUES (9, 'x', 'low', 'open', '2026-01-01')"])
def test_readonly_user_cannot_change_anything(statement):
    with pytest.raises(psycopg.Error):
        with sql_templates.connect_readonly() as conn:
            conn.execute(statement)


@needs_database
def test_readonly_user_has_no_write_permission_even_without_read_only_mode():
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(sql_templates.READONLY_DATABASE_URL, autocommit=True) as conn:
            conn.execute("SET default_transaction_read_only = off")
            conn.execute("DELETE FROM orders")
