import os
import psycopg2
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

@tool
def post_penalty_to_ledger(
    order_id: int, 
    penalty_applied_inr: float,
    vendor_name: str,
    expected_date: str,
    actual_date: str,
    delay_days: int
) -> str:
    """
    Updates the active_orders database to officially apply a financial penalty in INR.
    
    Args:
        order_id: The integer ID of the order.
        penalty_applied_inr: The final calculated penalty amount in INR.
        vendor_name: The name of the vendor (e.g., "Tata", "Cisco").
        expected_date: The expected delivery date.
        actual_date: The actual delivery date.
        delay_days: The total number of days the order was delayed.
    """

    DB_URL = os.environ.get("UPDATEONLY_DATABASE_URL")
    if not DB_URL:
        return "Error: UPDATEONLY_DATABASE_URL not found in environment variables."

    conn = None

    try:
        conn = psycopg2.connect(DB_URL)
        conn.set_session(autocommit=True)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE orders 
                SET penalty_applied_inr = %s 
                WHERE order_id = %s 
                RETURNING order_id, penalty_applied_inr;
                """, 
                (penalty_applied_inr, order_id)
            )
            
            updated_row = cursor.fetchone()
            
            if not updated_row:
                return f"Error: Order ID {order_id} was not found in database. No rows updated."
                
        return f"Success: Order {order_id} penalty set to ₹{penalty_applied_inr:,.2f} in database."
        
    except Exception as e:
        return f"Unable to update the DB -> {e}"

    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    print(post_penalty_to_ledger.invoke({"order_id": 1, "penalty_applied_inr": 6000.0}))