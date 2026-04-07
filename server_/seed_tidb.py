#!/usr/bin/env python3
"""
seed_tidb.py — Insert sample rows into TiDB for the AfyaBridge schema.

Tables seeded (in dependency order so FKs are satisfied):
  1. pharmacies
  2. pharmacy_hours
  3. users  (admin + pharmacist + rider + patient)
  4. notification_preferences  (one per user)
  5. suppliers
  6. drugs
  7. stock_batches
  8. prescriptions
  9. orders
  10. bulk_orders + bulk_order_items
  11. deliveries
  12. receipts

Run:
    pip install mysql-connector-python python-dotenv
    python seed_tidb.py

Credentials are read from the .env file in the same directory.
"""

import uuid
import json
import datetime
import os
import sys

try:
    import mysql.connector
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run:  pip install mysql-connector-python python-dotenv")
    sys.exit(1)

# ── Load credentials ──────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

CONN_PARAMS = dict(
    host     = os.getenv('DB_HOST'),
    port     = int(os.getenv('DB_PORT', 4000)),
    user     = os.getenv('DB_USER'),
    password = os.getenv('DB_PASSWORD'),
    database = os.getenv('DB_NAME'),
    ssl_ca   = None,          # TiDB Cloud requires SSL; add path if needed
    ssl_disabled = False,
)

# ── Helpers ───────────────────────────────────────────────────
def uid():
    return str(uuid.uuid4())

def now():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def today():
    return datetime.date.today().isoformat()

def future(days=365):
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

def past(days=30):
    return (datetime.date.today() - datetime.timedelta(days=days)).isoformat()


def run(cursor, sql, params):
    try:
        cursor.execute(sql, params)
    except mysql.connector.errors.IntegrityError as e:
        print(f"  [SKIP duplicate] {e}")


# ═════════════════════════════════════════════════════════════
# SEED DATA
# ═════════════════════════════════════════════════════════════

def seed(cursor):

    # ── 1. PHARMACIES ─────────────────────────────────────────
    print("Seeding pharmacies...")
    PHARMACY_ID = uid()
    run(cursor, """
        INSERT INTO pharmacies
          (id, name, email, phone, address_line1, county, sub_county,
           gps_lat, gps_lng, license_number, license_expiry,
           delivery_zones, is_24hr, is_active, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        PHARMACY_ID, 'AfyaBridge Westlands Pharmacy',
        'westlands@afyabridge.co.ke', '+254700000001',
        'Westlands Avenue, Ground Floor', 'Nairobi', 'Westlands',
        '-1.267226', '36.804614',
        'PPB/2024/WL/001', future(400),
        json.dumps(['Westlands', 'Parklands', 'Highridge']),
        False, True, now(), now()
    ))

    PHARMACY_ID_2 = uid()
    run(cursor, """
        INSERT INTO pharmacies
          (id, name, email, phone, address_line1, county, sub_county,
           gps_lat, gps_lng, license_number, license_expiry,
           delivery_zones, is_24hr, is_active, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        PHARMACY_ID_2, 'AfyaBridge Karen Pharmacy',
        'karen@afyabridge.co.ke', '+254700000002',
        'Karen Shopping Centre, Shop 12', 'Nairobi', 'Karen',
        '-1.321110', '36.713860',
        'PPB/2024/KR/002', future(400),
        json.dumps(['Karen', 'Langata', 'Ongata Rongai']),
        True, True, now(), now()
    ))

    # ── 2. PHARMACY_HOURS ─────────────────────────────────────
    print("Seeding pharmacy_hours...")
    days = [
        ('MON', '08:00:00', '20:00:00', False),
        ('TUE', '08:00:00', '20:00:00', False),
        ('WED', '08:00:00', '20:00:00', False),
        ('THU', '08:00:00', '20:00:00', False),
        ('FRI', '08:00:00', '20:00:00', False),
        ('SAT', '09:00:00', '18:00:00', False),
        ('SUN', None,       None,       True),
    ]
    for day, open_t, close_t, closed in days:
        run(cursor, """
            INSERT INTO pharmacy_hours
              (id, pharmacy_id, day_of_week, open_time, close_time, is_closed)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (uid(), PHARMACY_ID, day, open_t, close_t, closed))

    # ── 3. USERS ──────────────────────────────────────────────
    print("Seeding users...")
    # bcrypt hash of "Password123!" — pre-computed so we don't need bcrypt here
    HASHED_PW = '$2b$10$KIXlhBuGPL9h8H5NqNL8z.oRd0vqXwx3V4mGtVExVRiHSRMxwVqHG'

    ADMIN_ID      = uid()
    PHARMACIST_ID = uid()
    MANAGER_ID    = uid()
    RIDER_ID      = uid()
    PATIENT_ID    = uid()
    DOCTOR_ID     = uid()

    users = [
        (ADMIN_ID,      'admin',      'Admin User',        'admin@afyabridge.co.ke',    None),
        (PHARMACIST_ID, 'pharmacist', 'Jane Pharmacist',   'jane@afyabridge.co.ke',     PHARMACY_ID),
        (MANAGER_ID,    'pharmacist', 'Bob Manager',       'bob@afyabridge.co.ke',      PHARMACY_ID),
        (RIDER_ID,      'rider',      'Ali Rider',         'ali.rider@afyabridge.co.ke',None),
        (PATIENT_ID,    'patient',    'Mary Patient',      'mary@example.co.ke',        None),
        (DOCTOR_ID,     'doctor',     'Dr. Kamau Njoroge', 'dr.kamau@clinic.co.ke',     None),
    ]
    for u_id, role, name, email, pharm_id in users:
        run(cursor, """
            INSERT INTO users
              (id, role, full_name, email, password_hash,
               phone_number, is_active, is_verified,
               account_status, pharmacy_id, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            u_id, role, name, email, HASHED_PW,
            f'+2547{abs(hash(email)) % 100000000:08d}',
            True, True, 'active', pharm_id, now(), now()
        ))

    # ── 4. NOTIFICATION_PREFERENCES ───────────────────────────
    print("Seeding notification_preferences...")
    for u_id, *_ in users:
        run(cursor, """
            INSERT INTO notification_preferences
              (id, user_id,
               sms_enabled, email_enabled, push_enabled, in_app_enabled,
               appointment_alerts, prescription_alerts, payment_alerts,
               delivery_alerts, chat_alerts, broadcast_alerts,
               low_stock_alerts, expiry_alerts, expiry_alert_days,
               created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (uid(), u_id,
              True,True,True,True,
              True,True,True,True,True,True,
              True,True,14, now(),now()))

    # ── 5. SUPPLIERS ──────────────────────────────────────────
    print("Seeding suppliers...")
    SUPPLIER_ID = uid()
    run(cursor, """
        INSERT INTO suppliers
          (id, name, contact_name, email, phone, address, is_active, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        SUPPLIER_ID, 'Surgipharm Kenya Ltd', 'Peter Mwangi',
        'orders@surgipharm.co.ke', '+254722300400',
        'Industrial Area, Nairobi', True, now(), now()
    ))

    SUPPLIER_ID_2 = uid()
    run(cursor, """
        INSERT INTO suppliers
          (id, name, contact_name, email, phone, address, is_active, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        SUPPLIER_ID_2, 'Medisel Kenya Ltd', 'Grace Otieno',
        'supply@medisel.co.ke', '+254733500600',
        'Upper Hill, Nairobi', True, now(), now()
    ))

    # ── 6. DRUGS ──────────────────────────────────────────────
    print("Seeding drugs...")
    DRUG_AMOX_ID   = uid()
    DRUG_PARA_ID   = uid()
    DRUG_METRO_ID  = uid()
    DRUG_METF_ID   = uid()
    DRUG_VITC_ID   = uid()

    drugs = [
        (DRUG_AMOX_ID,  PHARMACY_ID, 'Amoxicillin 500mg',     'Amoxicillin',  'antibiotic', 'capsule', '45.00',  200, 30, 10, True),
        (DRUG_PARA_ID,  PHARMACY_ID, 'Paracetamol 500mg',     'Paracetamol',  'analgesic',  'tablet',  '8.00',   500, 50, 15, False),
        (DRUG_METRO_ID, PHARMACY_ID, 'Metronidazole 400mg',   'Metronidazole','antibiotic', 'tablet',  '25.00',  150, 25, 8,  True),
        (DRUG_METF_ID,  PHARMACY_ID, 'Metformin 500mg',       'Metformin',    'chronic',    'tablet',  '35.00',  300, 40, 12, True),
        (DRUG_VITC_ID,  PHARMACY_ID, 'Vitamin C 1000mg',      'Ascorbic Acid','vitamin',    'tablet',  '12.00',  400, 30, 10, False),
    ]
    for d in drugs:
        run(cursor, """
            INSERT INTO drugs
              (id, pharmacy_id, drug_name, generic_name, category, unit,
               unit_price, quantity_in_stock, reorder_level, critical_level,
               requires_rx, is_active, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (*d, True, now(), now()))

    # ── 7. STOCK_BATCHES ──────────────────────────────────────
    print("Seeding stock_batches...")
    batches = [
        (DRUG_AMOX_ID,  'BATCH-AMX-001', 200, 200, past(180), future(180)),
        (DRUG_PARA_ID,  'BATCH-PAR-001', 500, 500, past(90),  future(270)),
        (DRUG_METRO_ID, 'BATCH-MET-001', 150, 150, past(60),  future(300)),
        (DRUG_METF_ID,  'BATCH-MFM-001', 300, 300, past(120), future(240)),
        (DRUG_VITC_ID,  'BATCH-VTC-001', 400, 400, past(30),  future(330)),
    ]
    for drug_id, batch_no, qty_recv, qty_rem, mfg, exp in batches:
        run(cursor, """
            INSERT INTO stock_batches
              (id, drug_id, supplier_id, received_by,
               batch_number, quantity_received, quantity_remaining,
               manufacture_date, expiry_date, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (uid(), drug_id, SUPPLIER_ID, PHARMACIST_ID,
              batch_no, qty_recv, qty_rem, mfg, exp, now(), now()))

    # ── 8. PRESCRIPTIONS ──────────────────────────────────────
    print("Seeding prescriptions...")
    RX_ID = uid()
    items = json.dumps([
        {
            "drug_id": DRUG_AMOX_ID,
            "drug_name": "Amoxicillin 500mg",
            "dosage": "500mg",
            "frequency": "TID",
            "duration": "7 days",
            "route": "oral",
            "quantity": 21,
            "duration_days": 7,
            "substitution_ok": False,
            "warnings": "Complete the full course",
            "instructions": "Take after meals"
        },
        {
            "drug_id": DRUG_PARA_ID,
            "drug_name": "Paracetamol 500mg",
            "dosage": "500mg",
            "frequency": "QID",
            "duration": "5 days",
            "route": "oral",
            "quantity": 20,
            "duration_days": 5,
            "substitution_ok": True,
            "warnings": "Do not exceed 4 tablets/day",
            "instructions": "Take with water"
        }
    ])
    run(cursor, """
        INSERT INTO prescriptions
          (id, prescription_number,
           patient_id, doctor_id, pharmacy_id, dispensed_by,
           patient_name, patient_phone, patient_address, doctor_name,
           diagnosis, notes, priority, issue_date, expiry_date,
           items, status, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        RX_ID, 'RX-20240001',
        PATIENT_ID, DOCTOR_ID, PHARMACY_ID, None,
        'Mary Patient', '+254712345678', 'Westlands, Nairobi', 'Dr. Kamau Njoroge',
        'Acute Bacterial Tonsillitis', 'Complete full antibiotic course', 'normal',
        today(), future(30),
        items, 'pending', now(), now()
    ))

    # ── 9. ORDERS ─────────────────────────────────────────────
    print("Seeding orders...")
    ORDER_ID = uid()
    run(cursor, """
        INSERT INTO orders
          (id, order_number, prescription_id, pharmacy_id, prepared_by,
           patient_id, patient_name, patient_phone, patient_address,
           delivery_type, priority, status,
           total_amount, payment_status, payment_method, mpesa_ref,
           created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        ORDER_ID, 'ORD-20240001', RX_ID, PHARMACY_ID, PHARMACIST_ID,
        PATIENT_ID, 'Mary Patient', '+254712345678', 'Westlands, Nairobi',
        'home_delivery', 'normal', 'processing',
        1145.00, 'paid', 'mpesa', 'QGH5RK2LMN',
        now(), now()
    ))

    # ── 10. BULK_ORDERS + ITEMS ───────────────────────────────
    print("Seeding bulk_orders...")
    PO_ID = uid()
    run(cursor, """
        INSERT INTO bulk_orders
          (id, pharmacy_id, supplier_id, created_by,
           status, total_cost, expected_date, received_date, notes,
           created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        PO_ID, PHARMACY_ID, SUPPLIER_ID, PHARMACIST_ID,
        'submitted', 45000.00, future(14), None,
        'Monthly stock replenishment — urgent for antibiotics',
        now(), now()
    ))

    po_items = [
        (DRUG_AMOX_ID,  500, 0, '42.00', 'PO-AMX-001', future(365)),
        (DRUG_PARA_ID,  1000, 0, '7.00', 'PO-PAR-001', future(365)),
        (DRUG_METRO_ID, 300, 0, '22.00', 'PO-MET-001', future(365)),
    ]
    for drug_id, qty_ord, qty_rcv, cost, batch, exp in po_items:
        run(cursor, """
            INSERT INTO bulk_order_items
              (id, bulk_order_id, drug_id,
               quantity_ordered, quantity_received,
               unit_cost, batch_number, expiry_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (uid(), PO_ID, drug_id, qty_ord, qty_rcv, cost, batch, exp))

    # ── 11. DELIVERIES ────────────────────────────────────────
    print("Seeding deliveries...")
    DELIVERY_ID = uid()
    run(cursor, """
        INSERT INTO deliveries
          (id, package_number, order_id, rider_id,
           status, accept_status,
           pickup_location, pickup_lat, pickup_lng, pickup_contact,
           dropoff_location, dropoff_lat, dropoff_lng, receiver_contact,
           requirement, estimated_delivery_time, distance, charges,
           delivery_zone, delivery_notes, otp_code,
           delivered_at, date_approved, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        DELIVERY_ID, 'PKG-20240001', ORDER_ID, RIDER_ID,
        'assigned', True,
        'AfyaBridge Westlands Pharmacy, Westlands Ave',
        '-1.267226', '36.804614', '+254700000001',
        'Westlands Gardens, Apt 4B', '-1.270000', '36.800000', '+254712345678',
        None, '30-45 minutes', 2.5, 150.00,
        'Westlands', 'Call upon arrival', '482931',
        None, None, now(), now()
    ))

    # ── 12. RECEIPTS ──────────────────────────────────────────
    print("Seeding receipts...")
    run(cursor, """
        INSERT INTO receipts
          (id, order_id, dispensed_by,
           subtotal, discount, total,
           payment_method, mpesa_ref,
           pdf_path, emailed_at, sms_sent_at,
           created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        uid(), ORDER_ID, PHARMACIST_ID,
        1145.00, 0.00, 1145.00,
        'mpesa', 'QGH5RK2LMN',
        None, None, None, now(), now()
    ))

    print("\n✅  Seed complete. IDs for reference:")
    print(f"   PHARMACY_ID    = {PHARMACY_ID}")
    print(f"   ADMIN_ID       = {ADMIN_ID}")
    print(f"   PHARMACIST_ID  = {PHARMACIST_ID}")
    print(f"   RIDER_ID       = {RIDER_ID}")
    print(f"   PATIENT_ID     = {PATIENT_ID}")
    print(f"   DOCTOR_ID      = {DOCTOR_ID}")
    print(f"   DRUG_AMOX_ID   = {DRUG_AMOX_ID}")
    print(f"   RX_ID          = {RX_ID}")
    print(f"   ORDER_ID       = {ORDER_ID}")
    print(f"   DELIVERY_ID    = {DELIVERY_ID}")
    print(f"   SUPPLIER_ID    = {SUPPLIER_ID}")
    print(f"   PO_ID          = {PO_ID}")


# ── Entry point ───────────────────────────────────────────────
if __name__ == '__main__':
    print(f"Connecting to TiDB @ {CONN_PARAMS['host']}:{CONN_PARAMS['port']}...")
    try:
        conn = mysql.connector.connect(**CONN_PARAMS)
    except Exception as e:
        print(f"❌  Connection failed: {e}")
        sys.exit(1)

    conn.autocommit = False
    cursor = conn.cursor()

    try:
        seed(cursor)
        conn.commit()
        print("\n🎉  All rows committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"\n❌  Error — rolled back: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
