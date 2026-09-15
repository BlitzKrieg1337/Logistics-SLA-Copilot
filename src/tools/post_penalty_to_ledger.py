import sqlite3

from langchain_core.tools import tool
from pathlib import Path

DB_DIR = Path(Path(__file__).resolve().parents[2]) / "data" / "supply_chain.db"

@tool
def post_penalty_to_ledger(order_id: int, penalty_applied_inr: float) -> str:
    """
    Updates the active_orders database to officially apply a financial penalty.
    
    Args:
        order_id: The integer ID of the order.
        penalty_applied_inr: The final calculated penalty amount in INR.
    """

    try:
        conn = sqlite3.connect(DB_DIR)
        cursor = conn.cursor()
        print("loaded db")
        cursor.execute("UPDATE orders SET penalty_applied_inr = ? WHERE order_id = ?", 
                       (penalty_applied_inr, order_id))
        print("Updated")
        conn.commit()
        conn.close()
        return "Added penalty in DB."
        
    except Exception as e:
        return f"Unable to update the DB -> {e}"

# if __name__ == "__main__":
#     post_penalty_to_ledger(1, 6000)