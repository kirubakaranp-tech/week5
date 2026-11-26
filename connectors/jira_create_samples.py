import requests

from jira_connector import JIRA_PROJECT, JIRA_URL, get_auth

SAMPLE_ISSUES = [
    "Leave balance not updated after approval",
    "HR portal login page is slow in the morning",
    "Add GST number to monthly invoices",
    "Payslip PDF shows the wrong month",
    "Reset password email goes to spam",
    "Attendance report missing for Chennai office",
    "Allow half-day casual leave in the portal",
    "Expense claim upload fails for files over 5 MB",
    "New joiner cannot see the holiday list",
    "Export leave history to Excel",
]


def main():
    for summary in SAMPLE_ISSUES:
        body = {"fields": {"project": {"key": JIRA_PROJECT}, "summary": summary, "issuetype": {"name": "Task"}}}
        response = requests.post(f"{JIRA_URL}/rest/api/3/issue", json=body, auth=get_auth(), timeout=20)
        if response.status_code == 201:
            print(f"Created {response.json()['key']}: {summary}")
        else:
            print(f"Could not create '{summary}': {response.status_code} {response.text[:200]}")


if __name__ == "__main__":
    main()
