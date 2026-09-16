import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

READONLY_ROLE = os.environ.get("READONLY_ROLE")
READONLY_PASSWORD = os.environ.get("READONLY_PASSWORD")

UPDATE_ROLE = os.environ.get("UPDATE_ROLE")
UPDATE_PASSWORD = os.environ.get("UPDATE_PASSWORD")


def run(cursor, sql, label):
    """
    Runs one SQL statement at a time and prints whether it worked.
    This prevents one bad command from failing the entire script silently.
    """
    try:
        cursor.execute(sql)
        print(f"  OK -> {label}")
    except Exception as e:
        print(f"  FAILED -> {label}: {e}")


def init_db():
    if not all([DATABASE_URL, READONLY_ROLE, READONLY_PASSWORD, UPDATE_ROLE, UPDATE_PASSWORD]):
        print("Error -> One or more required environment variables are missing!")
        return

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

        # Lock down default public access
        run(cursor, "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;", "revoke default table access from PUBLIC")
        run(cursor, "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;", "revoke default privileges from PUBLIC")

        # ---- 2. CREATING ROLES (Safe Idempotent Method) ----
        print("\nCreating security roles...")
        run(cursor, f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{READONLY_ROLE}') THEN
                    CREATE ROLE {READONLY_ROLE} WITH LOGIN PASSWORD '{READONLY_PASSWORD}';
                END IF;
            END
            $$;
        """, f"ensure {READONLY_ROLE} exists")

        run(cursor, f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{UPDATE_ROLE}') THEN
                    CREATE ROLE {UPDATE_ROLE} WITH LOGIN PASSWORD '{UPDATE_PASSWORD}';
                END IF;
            END
            $$;
        """, f"ensure {UPDATE_ROLE} exists")

        # ---- 3. Assigning Permissions ----
        print(f"\nApplying permissions for {READONLY_ROLE}...")
        run(cursor, f"GRANT CONNECT ON DATABASE {db_name} TO {READONLY_ROLE};", "grant connect")
        run(cursor, f"GRANT USAGE ON SCHEMA public TO {READONLY_ROLE};", "grant usage")
        run(cursor, f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {READONLY_ROLE};", "grant select on existing tables")
        run(cursor, f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {READONLY_ROLE};", "grant select on future tables")

        print(f"\nApplying permissions for {UPDATE_ROLE}...")
        run(cursor, f"GRANT CONNECT ON DATABASE {db_name} TO {UPDATE_ROLE};", "grant connect")
        run(cursor, f"GRANT USAGE ON SCHEMA public TO {UPDATE_ROLE};", "grant usage")
        run(cursor, f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {UPDATE_ROLE};", "grant select on existing tables")
        run(cursor, f"GRANT UPDATE ON orders TO {UPDATE_ROLE};", "grant update on orders")

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