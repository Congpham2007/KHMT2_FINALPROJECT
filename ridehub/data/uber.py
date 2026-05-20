import os
import time
import mysql.connector
from sqlalchemy import create_engine
import pandas as pd

# ================= DATABASE CONFIGURATION =================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Tuan23321@",
    "database": "qlud",
}

# Resolve CSV path relative to this file's location
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_THIS_DIR)
CSV_PATH = os.path.join(_PROJECT_DIR, "ncr_ride_bookings.csv")


def auto_setup_database():
    """Auto-create database, tables, and import CSV data if needed."""
    print("⏳ Khởi động hệ thống RideHub...")

    try:
        # 1. Connect to MySQL server (without specifying database)
        server_conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"]
        )
        cursor = server_conn.cursor()

        # 2. Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        server_conn.close()

        # 3. Connect to the target database and check data
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SHOW TABLES LIKE 'rides'")
        table_exists = cursor.fetchone()

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM rides")
            count = cursor.fetchone()[0]
            if count > 10000:
                print(f"✅ Database đã sẵn sàng ({count:,} chuyến đi). Bật giao diện...")
                conn.close()
                return

        # 4. Import from CSV if DB is empty
        print("⚠️ Database trống! Bắt đầu tiến trình Import 150.000 dòng từ CSV...")
        start_time = time.time()

        print("📥 Đang đọc file ncr_ride_bookings.csv...")
        df = pd.read_csv(CSV_PATH)
        df.fillna(0, inplace=True)

        engine_url = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
        engine = create_engine(engine_url)

        print("🚀 Đang bơm dữ liệu vào MySQL... (Mất khoảng 10-15 giây)")
        df.to_sql(name='rides', con=engine, if_exists='replace', index=False)

        end_time = time.time()
        print(f"✅ HOÀN TẤT IMPORT! Thời gian: {end_time - start_time:.1f} giây. Khởi động UI...")
        conn.close()

    except FileNotFoundError:
        print(f"❌ LỖI: Không tìm thấy file CSV tại: {CSV_PATH}")
        exit()
    except Exception as e:
        print(f"❌ Lỗi Hệ Thống: {e}")
        exit()


def get_db_connection():
    """Return a new MySQL connection, or None on failure."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception:
        return None


def setup_database():
    """Create admin_users, flagged_users, and suspended_users tables + seed data."""
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()

    # Admin Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            username VARCHAR(50) PRIMARY KEY,
            password VARCHAR(50) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            role VARCHAR(50) NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM admin_users")
    if cursor.fetchone()[0] == 0:
        users = [("admin", "admin123", "Admin", "Manager")]
        for i in range(1, 4):
            users.append((f"sup{i}", "123456", f"Supervisor {i}", "Supervisor"))
        for i in range(1, 11):
            users.append((f"head{i}", "123456", f"Department Head {i}", "Head"))
        cursor.executemany("INSERT INTO admin_users VALUES (%s, %s, %s, %s)", users)

    # Flag and Suspend tables for Module 3
    cursor.execute("CREATE TABLE IF NOT EXISTS flagged_users (uid VARCHAR(100) PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS suspended_users (uid VARCHAR(100) PRIMARY KEY)")

    conn.commit()
    conn.close()
