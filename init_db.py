import urllib.parse
from sqlalchemy import create_engine, text

def init_db():
    # 1. ENTER YOUR DETAILS HERE
    USER = "root"
    # If your password is, for example, "pass@2026", 
    # we must encode it so the @ doesn't break the URL.
    RAW_PASS = "Micah@2026"  # <--- Type your ACTUAL password here
    HOST = "127.0.0.1"
    PORT = 3306
    DB = "upia_db"

    try:
        # 2. ENCODE THE PASSWORD
        safe_pass = urllib.parse.quote_plus(RAW_PASS)
        
        # 3. CONSTRUCT THE URL
        # We manually build it to ensure NO prefix is added
        url = f"mysql+pymysql://{USER}:{safe_pass}@{HOST}:{PORT}/{DB}"
        
        print(f"Connecting to: {HOST} via Port: {PORT}...")
        engine = create_engine(url)
        
        sql = """
        CREATE TABLE IF NOT EXISTS monthly_targets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            Pair_ID VARCHAR(50),
            Branch VARCHAR(100),
            Subsector VARCHAR(100),
            Sector VARCHAR(100),
            Role VARCHAR(100),
            Disb_Target DECIMAL(15, 2),
            Target_New_Customers DECIMAL(10, 2),
            Target_Unique_Customers DECIMAL(10, 2),
            Target_Active_Customers DECIMAL(10, 2),
            Target_Dormant_Customers DECIMAL(10, 2),
            Target_Amount_Collected DECIMAL(15, 2),
            Target_OTC_Pct DECIMAL(5, 2),
            Target_DD_Plus_7_Pct DECIMAL(5, 2),
            Target_Overall_Collection_Pct DECIMAL(5, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("✅ SUCCESS! The table is created.")
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    init_db()