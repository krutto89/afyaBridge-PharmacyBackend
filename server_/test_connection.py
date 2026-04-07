import pymysql

print("=== TiDB Cloud Connection Test (Hardcoded) ===")

# Hardcode the values here for testing
DB_USER = "3uQfsY5cKuXxfTC.root"      # ← Must have the .root suffix
DB_PASSWORD = "6FyXrWiHzD4cWfpf"      # ← Replace if you regenerated it
DB_HOST = "gateway01.eu-central-1.prod.aws.tidbcloud.com"
DB_PORT = 4000
DB_NAME = "afya_bridge"

print(f"Using username: '{DB_USER}'")
print(f"Length: {len(DB_USER)}")

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        ssl={'ssl_mode': 'REQUIRED'},
        connect_timeout=20
    )
    print("✅ SUCCESS: Connected to TiDB Cloud!")
    conn.close()

except Exception as e:
    print("❌ FAILED:")
    print(type(e).__name__ + ":", str(e))