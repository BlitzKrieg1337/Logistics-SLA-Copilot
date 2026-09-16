import os
import psycopg2

from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

@tool
def query_sql_analytics(sql_query: str) -> str:
    """
    Executes a read-only SELECT query against the Neon PostgreSQL logistics database.
    
    Use this tool to find order statuses, expected/actual delivery dates, 
    and to map order IDs to vendor names for contract lookups.

    Database Schema:
    - vendors (vendor_id SERIAL, vendor_name VARCHAR(100), contact_email VARCHAR(100))
    - orders (order_id SERIAL, vendor_id INTEGER, expected_date DATE, actual_date DATE, status VARCHAR(50), penalty_applied_inr NUMERIC(12, 2))
    
    Relationships:
    - orders.vendor_id = vendors.vendor_id
    
    Rules:
    - ONLY output valid PostgreSQL SELECT queries.
    - ALWAYS append LIMIT 15 to your queries unless using aggregations like COUNT().
    - DO NOT include formatting like ```sql in the input.
    - Order are one of the following only - DELIVERED_ON_TIME, IN_TRANSIT, DELIVERED_LATE
    """

    sql= sql_query.strip()
    if not sql.upper().startswith("SELECT"):
        return "Error: Read-only tool. Only SELECT queries are allowed."

    DB_URL = os.environ.get("READONLY_DATABASE_URL")
    if not DB_URL:
        return "Error: READONLY_DATABASE_URL not found in environment variables."

    conn = None
    
    try:
        conn = psycopg2.connect(DB_URL)
        conn.set_session(readonly = True, autocommit = True)

        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchmany(15)
            columns = [description[0] for description in cursor.description] if cursor.description else []

            if not rows:
                return "Query executed successfully, but returned no results."

            result_str = f"{columns}\n "
            for row in rows:
                result_str += f"{row}\n"

            return result_str

    except Exception as e:
        return f"SQL Error -> {e}"

    finally:
        if conn is not None:
            conn.close()



if __name__ == "__main__":
    print(query_sql_analytics.invoke({
        "sql_query": "SELECT * FROM orders LIMIT 5"
    }))