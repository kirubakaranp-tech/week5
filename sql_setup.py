import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

load_dotenv()

DATABASE_NAME = "company_db"
READONLY_USER = "company_readonly"
SCHEMA_FILE = Path("sql") / "company_db.sql"


def main():
    admin_url = os.getenv("DATABASE_ADMIN_URL")
    readonly_url = os.getenv("READONLY_DATABASE_URL")
    if not admin_url or not readonly_url:
        print("Please set DATABASE_ADMIN_URL and READONLY_DATABASE_URL in your .env file first.")
        return

    password = conninfo_to_dict(readonly_url).get("password")
    if not password or password == "CHOOSE_A_PASSWORD":
        print("Please choose a password for the read-only user in READONLY_DATABASE_URL.")
        return

    with psycopg.connect(admin_url, autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE_NAME,)).fetchone():
            conn.execute(f"CREATE DATABASE {DATABASE_NAME}")
            print(f"Created database {DATABASE_NAME}")

    with psycopg.connect(make_conninfo(admin_url, dbname=DATABASE_NAME), autocommit=True) as conn:
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        print("Created the tables and sample data")

        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (READONLY_USER,)).fetchone()
        command = "ALTER ROLE {} LOGIN PASSWORD {}" if exists else "CREATE ROLE {} LOGIN PASSWORD {}"
        conn.execute(sql.SQL(command).format(sql.Identifier(READONLY_USER), sql.Literal(password)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(DATABASE_NAME), sql.Identifier(READONLY_USER)))
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(READONLY_USER)))
        conn.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(READONLY_USER)))
        conn.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(sql.Identifier(READONLY_USER)))
        print(f"User {READONLY_USER} can only read (SELECT)")


if __name__ == "__main__":
    main()
