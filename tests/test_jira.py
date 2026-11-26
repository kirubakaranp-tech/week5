import pytest
import requests

from connectors import jira_connector


def issue(number):
    return {
        "key": f"HR-{number}",
        "fields": {
            "summary": f"Issue {number}",
            "status": {"name": "To Do"},
            "assignee": None if number % 2 else {"displayName": "Priya"},
            "priority": {"name": "Medium"},
            "updated": "2026-11-20T10:15:00.000+0530",
        },
    }


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def test_search_uses_the_new_endpoint_and_follows_pages(monkeypatch):
    pages = [
        {"issues": [issue(n) for n in range(1, 7)], "nextPageToken": "page2", "isLast": False},
        {"issues": [issue(n) for n in range(7, 13)], "isLast": True},
    ]
    calls = []

    def fake_get(url, params, auth, headers, timeout):
        calls.append((url, dict(params)))
        return FakeResponse(pages[len(calls) - 1])

    monkeypatch.setattr(jira_connector, "JIRA_URL", "https://demo.atlassian.net")
    monkeypatch.setattr(jira_connector.requests, "get", fake_get)

    items = jira_connector.search_issues("project = HR", max_items=10)

    assert len(items) == 10
    assert calls[0][0] == "https://demo.atlassian.net/rest/api/3/search/jql"
    assert calls[0][1]["fields"] == "summary,status,assignee,priority,updated"
    assert calls[1][1]["nextPageToken"] == "page2"
    assert items[0] == {"key": "HR-1", "summary": "Issue 1", "status": "To Do", "assignee": "Unassigned",
                        "priority": "Medium", "updated": "2026-11-20"}
    assert items[1]["assignee"] == "Priya"


def test_wrong_token_raises_http_error(monkeypatch):
    monkeypatch.setattr(jira_connector.requests, "get", lambda *args, **kwargs: FakeResponse({}, 401))
    with pytest.raises(requests.HTTPError):
        jira_connector.search_issues("project = HR")
