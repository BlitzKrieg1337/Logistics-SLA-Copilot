import sqlite3
import os

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.path.join(BASE_DIR, "data", "supply_chain.db")
# print(f' DIRECTORY -> {BASE_DIR}')
# print(f' DIRECTORY -> {DB_PATH}')

def seed_database():
    print(f"INITIALIZING DATABASE AT -> {DB_PATH}")

    # Creating connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ENABLE FOREIGN KEY
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create vendors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_name TEXT NOT NULL UNIQUE,
            contact_email TEXT NOT NULL
        )
    """)

    # Create order table
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                vendor_id INTEGER NOT NULL,
                expected_date DATE NOT NULL,
                actual_date DATE,
                status TEXT NOT NULL,
                penalty_applied_inr REAL,
                FOREIGN KEY (vendor_id) REFERENCES vendors (vendor_id)
            )
        """)

    # Remove if already exists
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM vendors")

    # Mock Vendors Data
    mock_vendors = [
        (1, "Cisco Systems", "logistics@cisco.com"),
        (2, "Siemens EU", "supplychain@siemens.de"),
        (3, "Dell Technologies", "orders@dell.com"),
        (4, "Tata Electronics", "dispatch@tataelectronics.in")
    ]

    cursor.executemany("""
        INSERT INTO vendors (vendor_id, vendor_name, contact_email)
        VALUES (?, ?, ?)
    """, mock_vendors)

    mock_orders = [
        # On-time delivery
        (1001, 1, "2026-09-05", "2026-09-04", "DELIVERED", None),
        
        # Delivered late (5 days late - Siemens)
        (1042, 2, "2026-09-01", "2026-09-06", "LATE", None),
        
        # En route / On track (Dell)
        (1088, 3, "2026-09-25", None, "EN_ROUTE", None),
        
        # Currently Missing / Ongoing delay (Tata Electronics)
        (1099, 4, "2026-09-08", None, "LATE", None),
        
        # Penalty already applied (Siemens)
        (1015, 2, "2026-08-20", "2026-08-25", "DELIVERED", 420000.0)
    ]

    cursor.executemany("""
            INSERT INTO orders (order_id, vendor_id, expected_date, actual_date, status, penalty_applied_inr)
            VALUES (?, ?, ?, ?, ?, ?)
        """, mock_orders)

    conn.commit()
    print(f"Successfully seeded {len(mock_vendors)} vendors and {len(mock_orders)} orders.")

    print('--- DATABASE VIEW ---')
    cursor.execute("""
        SELECT o.order_id, v.vendor_name, v.contact_email, o.expected_date, o.actual_date, o.status, o.penalty_applied_inr
        FROM orders o
        JOIN vendors v on o.vendor_id = v.vendor_id
    """)

    for row in cursor.fetchall():
        print(row)

    conn.close()


if __name__ == '__main__':
    seed_database()