import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL", "").rstrip("/")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT = os.getenv("JIRA_PROJECT", "")
FIELDS = "summary,status,assignee,priority,updated"


def get_auth():
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def to_item(issue):
    fields = issue["fields"]
    assignee = fields.get("assignee") or {}
    priority = fields.get("priority") or {}
    return {
        "key": issue["key"],
        "summary": fields["summary"],
        "status": fields["status"]["name"],
        "assignee": assignee.get("displayName", "Unassigned"),
        "priority": priority.get("name", "-"),
        "updated": fields["updated"][:10],
    }


def search_issues(jql, max_items=10):
    items = []
    next_page_token = None

    while len(items) < max_items:
        params = {"jql": jql, "maxResults": min(50, max_items - len(items)), "fields": FIELDS}
        if next_page_token:
            params["nextPageToken"] = next_page_token

        response = requests.get(
            f"{JIRA_URL}/rest/api/3/search/jql",
            params=params,
            auth=get_auth(),
            headers={"Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        for issue in data["issues"]:
            items.append(to_item(issue))

        next_page_token = data.get("nextPageToken")
        if data.get("isLast", True) or not next_page_token:
            break

    return items[:max_items]


def main():
    missing = [name for name in ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT"] if not os.getenv(name)]
    if missing:
        print(f"Please set {', '.join(missing)} in your .env file first.")
        return

    jql = f"project = {JIRA_PROJECT} ORDER BY updated DESC"
    print(f"JQL: {jql}\n")
    try:
        issues = search_issues(jql, max_items=10)
    except requests.HTTPError as error:
        status = error.response.status_code
        if status == 401:
            print("Jira said 401: check JIRA_EMAIL and JIRA_API_TOKEN.")
        elif status in (400, 404):
            print(f"Jira said {status}: check JIRA_URL and the project key {JIRA_PROJECT}.")
        else:
            print(f"Jira said {status}: {error.response.text[:200]}")
        return
    except requests.RequestException as error:
        print(f"Could not reach Jira: {error}")
        return

    print(f"{'Key':10} {'Status':13} {'Priority':9} {'Updated':11} Summary")
    for issue in issues:
        print(f"{issue['key']:10} {issue['status']:13} {issue['priority']:9} {issue['updated']:11} {issue['summary']}")
    print(f"\nListed {len(issues)} issues from project {JIRA_PROJECT}")


if __name__ == "__main__":
    main()
