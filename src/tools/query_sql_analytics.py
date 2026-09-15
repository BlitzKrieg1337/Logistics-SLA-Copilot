import sqlite3

from langchain_core.tools import tool
from pathlib import Path


DB_DIR = Path(Path(__file__).resolve().parents[2]) / "data" / "supply_chain.db"


@tool
def query_sql_analytics(sql_query: str) -> str:
    """
    Executes a SELECT query against the supply chain SQLite database.
    
    Use this tool to find order statuses, expected/actual delivery dates, 
    and to map order IDs to vendor names for contract lookups.

    Database Schema:
    - vendors (vendor_id INT, vendor_name TEXT, contact_email TEXT)
    - orders (order_id INT, vendor_id INT, expected_date DATE, actual_date DATE, status TEXT, penalty_applied_inr REAL)
    
    Relationships:
    - orders.vendor_id = vendors.vendor_id
    
    Rules:
    - ONLY output valid SQLite SELECT queries.
    - DO NOT include formatting like ```sql in the input.
    """

    sql = sql_query.strip()

    if not sql.upper().startswith("SELECT"):
        return "Error: Read-only tool. Only SELECT queries are allowed."
    
    try:
        conn = sqlite3.connect(DB_DIR)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [ description[0] for description in cursor.description]
        conn.close()

        if not rows:
            return "Query executed successfully, but returned no results."

        result_str = f"Columns : {columns}\nData \t: "
        for row in rows:
            result_str += f"{row}\n"

        return result_str

    except Exception as e:
        return f"SQL Error -> {e}"



# if __name__ == "__main__":
#     print(query_sql_analytics('select* from orders'))