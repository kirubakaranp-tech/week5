from pathlib import Path

from secure_rag import answer_question
from secure_store import sync_folder

QUESTION = "What is the salary revision cycle and how much increase does a rating of 4 get?"
RESULTS_FILE = Path("results") / "access_test.md"


def main():
    sync_folder()
    print(f"\nQuestion: {QUESTION}\n")

    lines = ["# Access control test", "", f"Question: {QUESTION}", "",
             "| Role | Answer | HR-only chunks retrieved |", "|---|---|---|"]
    for role in ["employee", "hr"]:
        answer, chunks = answer_question(QUESTION, role)
        hr_chunks = sum(1 for chunk in chunks if chunk["allowed_roles"] == "hr")
        print(f"Role: {role} -> '{answer}'")
        print(f"   retrieved {len(chunks)} chunks, {hr_chunks} of them HR-only\n")
        lines.append(f"| {role} | {answer} | {hr_chunks} of {len(chunks)} |")

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved the results in {RESULTS_FILE}")


if __name__ == "__main__":
    main()
