import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def verify_rbac(db_url, role_label, expect_read, expect_update):
    if not db_url:
        print(f"❌ {role_label} URL is missing from .env")
        return
        
    print(f"\n--- Testing Role: {role_label} ---")
    
    try:
        # Autocommit is required so a failed test doesn't break the next test
        conn = psycopg2.connect(db_url)
        conn.autocommit = True 
        cursor = conn.cursor()
        
        # 1. Test READ Privileges
        try:
            cursor.execute("SELECT 1 FROM orders LIMIT 1;")
            if expect_read:
                print("  ✅ SELECT: Succeeded (Expected)")
            else:
                print("  ❌ SELECT: Succeeded (WARNING: Should have failed!)")
        except Exception as e:
            if not expect_read:
                print("  ✅ SELECT: Blocked by Postgres (Expected)")
            else:
                print(f"  ❌ SELECT: Failed (WARNING: Should have succeeded) -> {e}")

        # 2. Test UPDATE Privileges (WHERE FALSE ensures we don't alter real data)
        try:
            cursor.execute("UPDATE orders SET penalty_applied_inr = 0 WHERE FALSE;")
            if expect_update:
                print("  ✅ UPDATE: Succeeded (Expected)")
            else:
                print("  ❌ UPDATE: Succeeded (WARNING: Should have failed!)")
        except psycopg2.errors.InsufficientPrivilege:
            if not expect_update:
                print("  ✅ UPDATE: Blocked by Postgres 'InsufficientPrivilege' (Expected)")
            else:
                print("  ❌ UPDATE: Blocked (WARNING: Should have succeeded)")
                
        conn.close()
        
    except Exception as e:
        print(f"❌ FAILED to connect: {e}")

if __name__ == "__main__":
    print("Starting RBAC Penetration Test...")
    
    # Test Read-Only Role (Should Read: Yes, Should Update: No)
    verify_rbac(os.environ.get("READONLY_DATABASE_URL"), "READ-ONLY", expect_read=True, expect_update=False)
    
    # Test Update Role (Should Read: Yes, Should Update: Yes)
    verify_rbac(os.environ.get("UPDATEONLY_DATABASE_URL"), "UPDATE-ONLY", expect_read=True, expect_update=True)
    
    print("\nTest Complete.")