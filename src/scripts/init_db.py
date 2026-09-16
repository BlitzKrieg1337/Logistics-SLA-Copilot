import os
import psycopg2

from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def init_db():
    if not DATABASE_URL:
        print(f"Error -> Database url not found in environment variables!")
        return

    print(f"Connecting to Neon PostgreSQL as Admin...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        # Creating SCHEMA
        print(f"Creating vendors and orders table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendors(
                vendor_id SERIAL PRIMARY KEY,
                vendor_name VARCHAR(100) NOT NULL UNIQUE,
                contact_email VARCHAR(100) NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                vendor_id INTEGER NOT NULL REFERENCES vendors(vendor_id),
                expected_date DATE NOT NULL,
                actual_date DATE,
                status VARCHAR(50) NOT NULL,
                penalty_applied_inr NUMERIC(12, 2)
            );
        """)

        # CREATING ROLES
        print(f"Creating security roles...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT from pg_catalog.pg_roles WHERE rolname = 'analytics_read_only') THEN
                    CREATE ROLE analytics_read_only WITH LOGIN PASSWORD 'Readonly_Pass_2026';
                END IF;

                IF NOT EXISTS (SELECT from pg_catalog.pg_roles WHERE rolname = 'penalty_update_only') THEN
                    CREATE ROLE penalty_update_only WITH LOGIN PASSWORD 'Updateonly_Pass_2026';
                END IF;
            END
            $$;
        """)

        # Assigning Permission to analytics_read_only
        print(f"Applying permissions for analytics_read_only")
        cursor.execute("""
            GRANT CONNECT ON DATABASE neondb TO analytics_read_only;
            GRANT USAGE ON SCHEMA public TO analytics_read_only;
            GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_read_only;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_read_only;
        """)

        # Assigning Permission to penalty_update_only
        print(f"Applying permissions for penalty_update_only")
        cursor.execute("""
            GRANT CONNECT ON DATABASE neondb TO penalty_update_only;
            GRANT USAGE ON SCHEMA public TO penalty_update_only;
            GRANT SELECT ON ALL TABLES IN SCHEMA public TO penalty_update_only;
            GRANT UPDATE ON orders TO penalty_update_only;
        """)

        print(F"Successfully initialized Neon Database Schema and RBAC Security!")

    except Exception as e:
        print(f"Error -> {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()
    