import re

from llm import ask
from secure_store import get_collection

ROLE_ACCESS = {"employee": ["all"], "hr": ["hr", "all"]}
USERS = {"arun": "employee", "meena": "hr"}
TOP_K = 4
I_DONT_KNOW = "I don't know."

PROMPT = """You answer questions from Northwind Software staff using ONLY the context below.

Rules:
- Use only facts written in the context. Do not use anything you know from elsewhere.
- If the context does not contain the answer, reply with exactly: I don't know.
- Answer in one or two short sentences.
- End with the number of the context block you used, like [2].

Context:
{context}

Question: {question}
Answer:"""


def retrieve(question, role, top_k=TOP_K):
    if role not in ROLE_ACCESS:
        raise ValueError(f"Unknown role {role!r}. Known roles: {', '.join(ROLE_ACCESS)}")

    collection = get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[question],
        n_results=min(top_k, collection.count()),
        where={"allowed_roles": {"$in": ROLE_ACCESS[role]}},
    )
    chunks = []
    for text, metadata in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"text": text, **metadata})
    return chunks


def describe_source(chunk):
    if "page" in chunk:
        return f"{chunk['source']} p.{chunk['page']}"
    return f"{chunk['source']}, {chunk.get('section', '')}".rstrip(", ")


def answer_question(question, role):
    chunks = retrieve(question, role)
    if not chunks:
        return I_DONT_KNOW, chunks

    context = "\n\n".join(f"[{number}] {chunk['text']}" for number, chunk in enumerate(chunks, start=1))
    reply = ask(PROMPT.format(context=context, question=question))

    if not reply or reply.lower().replace("’", "'").startswith("i don't know"):
        return I_DONT_KNOW, chunks

    used = re.findall(r"\[(\d+)\]", reply)
    number = int(used[0]) if used and 1 <= int(used[0]) <= len(chunks) else 1
    answer = re.sub(r"\s*\[\d+\]", "", reply).strip()
    return f"{answer} (Source: {describe_source(chunks[number - 1])})", chunks


def answer_for_user(question, username):
    if username not in USERS:
        raise PermissionError(f"Unknown user {username!r}")
    return answer_question(question, USERS[username])
