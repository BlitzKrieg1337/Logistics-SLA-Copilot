import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

READONLY_ROLE = os.environ.get("READONLY_ROLE")
READONLY_PASSWORD = os.environ.get("READONLY_PASSWORD")

UPDATE_ROLE = os.environ.get("UPDATE_ROLE")
UPDATE_PASSWORD = os.environ.get("UPDATE_PASSWORD")


def run(cursor, query, label):
    """
    Runs one SQL statement at a time and prints whether it worked.
    Accepts a plain string or a psycopg2.sql.Composed object.
    """
    try:
        cursor.execute(query)
        print(f"  OK -> {label}")
    except Exception as e:
        print(f"  FAILED -> {label}: {e}")


def init_db():
    if not all([DATABASE_URL, READONLY_ROLE, READONLY_PASSWORD, UPDATE_ROLE, UPDATE_PASSWORD]):
        print("Error -> One or more required environment variables are missing!")
        return

    # Narrows str | None -> str for Pylance; redundant at runtime given the check above,
    # but the all() call above doesn't count as a type guard.
    assert DATABASE_URL is not None
    assert READONLY_ROLE is not None
    assert READONLY_PASSWORD is not None
    assert UPDATE_ROLE is not None
    assert UPDATE_PASSWORD is not None

    print("Connecting to Neon PostgreSQL as Admin...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT current_database();")
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Could not determine current database name.")
        db_name = row[0]

        # ---- 1. Creating SCHEMA ----
        print("\nCreating vendors and orders table...")
        run(cursor, """
            CREATE TABLE IF NOT EXISTS vendors(
                vendor_id SERIAL PRIMARY KEY,
                vendor_name VARCHAR(100) NOT NULL UNIQUE,
                contact_email VARCHAR(100) NOT NULL
            );
        """, "create vendors table")

        run(cursor, """
            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id),
                expected_date DATE NOT NULL,
                actual_date DATE,
                status VARCHAR(50) NOT NULL,
                penalty_applied_inr NUMERIC(12, 2)
            );
        """, "create orders table")

        run(cursor, "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;", "revoke default table access from PUBLIC")
        run(cursor, "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;", "revoke default privileges from PUBLIC")

        # ---- 2. CREATING ROLES (Safe Idempotent Method) ----
        print("\nCreating security roles...")
        run(cursor, sql.SQL("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = {role_literal}) THEN
                    CREATE ROLE {role_ident} WITH LOGIN PASSWORD {password_literal};
                END IF;
            END
            $$;
        """).format(
            role_literal=sql.Literal(READONLY_ROLE),
            role_ident=sql.Identifier(READONLY_ROLE),
            password_literal=sql.Literal(READONLY_PASSWORD),
        ), f"ensure {READONLY_ROLE} exists")

        run(cursor, sql.SQL("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = {role_literal}) THEN
                    CREATE ROLE {role_ident} WITH LOGIN PASSWORD {password_literal};
                END IF;
            END
            $$;
        """).format(
            role_literal=sql.Literal(UPDATE_ROLE),
            role_ident=sql.Identifier(UPDATE_ROLE),
            password_literal=sql.Literal(UPDATE_PASSWORD),
        ), f"ensure {UPDATE_ROLE} exists")

        # ---- 3. Assigning Permissions ----
        print(f"\nApplying permissions for {READONLY_ROLE}...")
        run(cursor, sql.SQL("GRANT CONNECT ON DATABASE {} TO {};").format(
            sql.Identifier(db_name), sql.Identifier(READONLY_ROLE)
        ), "grant connect")
        run(cursor, sql.SQL("GRANT USAGE ON SCHEMA public TO {};").format(
            sql.Identifier(READONLY_ROLE)
        ), "grant usage")
        run(cursor, sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {};").format(
            sql.Identifier(READONLY_ROLE)
        ), "grant select on existing tables")
        run(cursor, sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {};").format(
            sql.Identifier(READONLY_ROLE)
        ), "grant select on future tables")

        print(f"\nApplying permissions for {UPDATE_ROLE}...")
        run(cursor, sql.SQL("GRANT CONNECT ON DATABASE {} TO {};").format(
            sql.Identifier(db_name), sql.Identifier(UPDATE_ROLE)
        ), "grant connect")
        run(cursor, sql.SQL("GRANT USAGE ON SCHEMA public TO {};").format(
            sql.Identifier(UPDATE_ROLE)
        ), "grant usage")
        run(cursor, sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {};").format(
            sql.Identifier(UPDATE_ROLE)
        ), "grant select on existing tables")
        run(cursor, sql.SQL("GRANT UPDATE ON orders TO {};").format(
            sql.Identifier(UPDATE_ROLE)
        ), "grant update on orders")

        # ---- 4. Verify ----
        print("\nCurrent grants on orders/vendors:")
        cursor.execute("""
            SELECT grantee, table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE table_name IN ('orders', 'vendors')
              AND grantee IN (%s, %s)
            ORDER BY grantee, table_name, privilege_type;
        """, (READONLY_ROLE, UPDATE_ROLE))

        for row in cursor.fetchall():
            print(f"  {row}")

        print("\nSuccessfully initialized Neon Database Schema and RBAC Security!")

    except Exception as e:
        print(f"Fatal Error -> {e}")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_db()