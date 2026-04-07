import mysql.connector, sys

CONN = dict(
    host     = 'gateway01.eu-central-1.prod.aws.tidbcloud.com',
    port     = 4000,
    user     = '3uQfsY5cKuXxfTC.root',
    password = '6FyXrWiHzD4cWfpf',
    database = 'afya_bridge',
    ssl_disabled = False,
)

# Every real table from your SHOW TABLES output
TABLES = [
    'users', 'pharmacy_users', 'doctors', 'patients', 'admin_accounts',
    'pharmacies', 'pharmacy_hours', 'pharmacy_registrations',
    'drugs', 'stock_batches', 'suppliers',
    'prescriptions', 'patient_prescriptions',
    'Orders', 'bulk_orders', 'bulk_order_items',
    'Delivery', 'receipts',
    'Notification', 'Notifications', 'notification_preferences',
    'otp_verifications', 'Riders',
    'Appointment', 'appointment_slots',
    'Consultation', 'ConsultationMessage',
    'Finances', 'Payment', 'mpesa_transactions',
    'RefillOrder', 'RefillOrderItem',
    'Prescription', 'MedicalRecord',
    'Vital', 'Issues', 'messages',
    'broadcast_announcements',
    'Allergy', 'Condition', 'Document', 'EmergencyAlert',
    'EmergencyContact', 'ManualMedicine', 'Medication',
    'OTP', 'Patient', 'RefreshToken', 'SavedLocation',
    'Surgery', 'SymptomMessage', 'SymptomSession', 'Visit',
    'DataExportRequest',
]

try:
    conn   = mysql.connector.connect(**CONN)
    cursor = conn.cursor()
    print(f"Connected to TiDB successfully.\n")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

for table in TABLES:
    try:
        cursor.execute(f"DESCRIBE `{table}`;")
        rows = cursor.fetchall()
        print(f"\n{'='*60}")
        print(f"TABLE: {table}  ({len(rows)} columns)")
        print(f"{'='*60}")
        for r in rows:
            null    = 'NULL    ' if r[2] == 'YES' else 'NOT NULL'
            default = f"  default={r[4]}" if r[4] is not None else ''
            key     = f"  [{r[3]}]" if r[3] else ''
            print(f"  {r[0]:<32} {str(r[1]):<30} {null}{key}{default}")
    except Exception as e:
        print(f"\n[SKIP] {table}: {e}")

cursor.close()
conn.close()
print("\n\nDone.")
