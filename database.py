# -*- coding: utf-8 -*-
import sqlite3
import os
import json
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("Database")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zaxro_bot.db")
CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "products.json")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(clear_mock_products: bool = False):
    """Barcha kerakli jadvallarni yaratish va dastlabki sozlash"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Foydalanuvchilar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                phone TEXT,
                language TEXT DEFAULT 'uz',
                is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Mahsulotlar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT DEFAULT 'atir',
                name TEXT NOT NULL,
                brand TEXT,
                gender TEXT DEFAULT 'uniseks',
                volume TEXT,
                price INTEGER NOT NULL,
                image TEXT,
                top_notes TEXT,
                heart_notes TEXT,
                base_notes TEXT,
                durability TEXT,
                description TEXT,
                in_stock INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Savatcha jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, product_id)
            )
        """)
        
        # Buyurtmalar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                customer_address TEXT,
                items_json TEXT NOT NULL,
                total_amount INTEGER NOT NULL,
                payment_method TEXT DEFAULT 'karta',
                receipt_file_id TEXT,
                status TEXT DEFAULT 'kutilmoqda',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Promokodlar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_percent INTEGER DEFAULT 0,
                discount_amount INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Aksiyalar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                text TEXT NOT NULL,
                image TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Mijoz savollari va administrator javoblari
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                answer_text TEXT,
                status TEXT DEFAULT 'kutilmoqda',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        if clear_mock_products:
            # Soxta atirlarni tozalash (foydalanuvchi talabi bo'yicha)
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM cart")
            
        conn.commit()
        logger.info("Ma'lumotlar bazasi jadvallari tekshirildi.")


# ─── FOYDALANUVCHILAR ──────────────────────────────────────────

def register_user(user_id: int, full_name: str, username: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, full_name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username
        """, (user_id, full_name, username))
        conn.commit()


def get_user_language(user_id: int) -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if (row and row[0]) else "uz"


def set_user_language(user_id: int, lang: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        conn.commit()


def update_user_phone(user_id: int, phone: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        conn.commit()


def get_user(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def is_user_blocked(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return bool(row[0]) if row else False


def set_user_blocked(user_id: int, blocked: bool):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (1 if blocked else 0, user_id))
        conn.commit()


def get_all_users() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


# ─── MAHSULOTLAR ────────────────────────────────────────────────

def dump_products_to_json():
    """Bazada mavjud barcha mahsulotlarni products.json ga saqlash"""
    prods = get_all_products()
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(prods, f, ensure_ascii=False, indent=2)


def get_all_products() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_product(product_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_product(
    name: str,
    brand: str,
    gender: str,
    volume: str,
    price: int,
    image: str = "",
    top_notes: str = "",
    heart_notes: str = "",
    base_notes: str = "",
    durability: str = "",
    description: str = "",
    in_stock: int = 1
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (
                name, brand, gender, volume, price, image,
                top_notes, heart_notes, base_notes, durability, description, in_stock
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, brand, gender, volume, price, image,
              top_notes, heart_notes, base_notes, durability, description, in_stock))
        new_id = cursor.lastrowid
        conn.commit()
    dump_products_to_json()
    return new_id


def delete_product(product_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        cursor.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))
        conn.commit()
    dump_products_to_json()


def update_product_price(product_id: int, new_price: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, product_id))
        conn.commit()
    dump_products_to_json()


def update_product_stock(product_id: int, in_stock: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET in_stock = ? WHERE id = ?", (in_stock, product_id))
        conn.commit()
    dump_products_to_json()


def get_distinct_brands() -> List[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND brand != '' ORDER BY brand ASC")
        return [row[0] for row in cursor.fetchall()]


def filter_products(
    brand: Optional[str] = None,
    gender: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    in_stock_only: bool = False
) -> List[dict]:
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if brand:
        query += " AND brand = ?"
        params.append(brand)
        
    if gender and gender != "barchasi":
        query += " AND gender = ?"
        params.append(gender)
        
    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
        
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)
        
    if in_stock_only:
        query += " AND in_stock = 1"
        
    query += " ORDER BY id DESC"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# ─── SAVATCHA (CART) ──────────────────────────────────────────

def add_to_cart(user_id: int, product_id: int, quantity: int = 1) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, product_id) DO UPDATE SET
                quantity = cart.quantity + excluded.quantity
        """, (user_id, product_id, quantity))
        conn.commit()
        return get_cart_count(user_id)


def update_cart_quantity(user_id: int, product_id: int, quantity: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        if quantity <= 0:
            cursor.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        else:
            cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (quantity, user_id, product_id))
        conn.commit()


def remove_from_cart(user_id: int, product_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        conn.commit()


def clear_cart(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit()


def get_cart_items(user_id: int) -> Tuple[List[dict], int]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.quantity, p.*
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
            ORDER BY c.created_at ASC
        """, (user_id,))
        rows = cursor.fetchall()
        items = []
        total = 0
        for r in rows:
            d = dict(r)
            subtotal = d["price"] * d["quantity"]
            d["subtotal"] = subtotal
            total += subtotal
            items.append(d)
        return items, total


def get_cart_count(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(quantity) FROM cart WHERE user_id = ?", (user_id,))
        val = cursor.fetchone()[0]
        return val if val else 0


# ─── BUYURTMALAR (ORDERS) ──────────────────────────────────────

def create_order(
    user_id: int,
    customer_name: str,
    customer_phone: str,
    customer_address: str,
    items: List[dict],
    total_amount: int,
    payment_method: str = "karta",
    receipt_file_id: Optional[str] = None
) -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM orders")
        max_id = cursor.fetchone()[0] or 1000
        new_id = max_id + 1
        order_code = f"ZP-{new_id}"
        
        cursor.execute("""
            INSERT INTO orders (
                order_code, user_id, customer_name, customer_phone,
                customer_address, items_json, total_amount, payment_method,
                receipt_file_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'kutilmoqda')
        """, (
            order_code, user_id, customer_name, customer_phone,
            customer_address, json.dumps(items, ensure_ascii=False), total_amount,
            payment_method, receipt_file_id
        ))
        conn.commit()
        return order_code


def update_order_receipt(order_code: str, receipt_file_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders
            SET receipt_file_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_code = ?
        """, (receipt_file_id, order_code))
        conn.commit()


def update_order_status(order_code: str, status: str, admin_notes: Optional[str] = None) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders
            SET status = ?, admin_notes = COALESCE(?, admin_notes), updated_at = CURRENT_TIMESTAMP
            WHERE order_code = ?
        """, (status, admin_notes, order_code))
        conn.commit()
        
        cursor.execute("SELECT * FROM orders WHERE order_code = ?", (order_code,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_order_by_code(order_code: str) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_code = ?", (order_code,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_orders(user_id: int, limit: int = 10) -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_all_orders(limit: int = 50) -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]


# ─── AKSIYA VA PROMOKODLAR ──────────────────────────────────────

def add_promocode(code: str, discount_percent: int = 0, discount_amount: int = 0):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO promocodes (code, discount_percent, discount_amount, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(code) DO UPDATE SET
                discount_percent = excluded.discount_percent,
                discount_amount = excluded.discount_amount,
                is_active = 1
        """, (code.strip().upper(), discount_percent, discount_amount))
        conn.commit()


def get_promocode(code: str) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promocodes WHERE code = ? AND is_active = 1", (code.strip().upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_promocodes() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promocodes ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def add_promotion(text: str, title: str = "", image: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO promotions (title, text, image, is_active)
            VALUES (?, ?, ?, 1)
        """, (title, text, image))
        new_id = cursor.lastrowid
        conn.commit()
        return new_id


def get_active_promotions() -> List[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promotions WHERE is_active = 1 ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def delete_all_promotions():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM promotions")
        conn.commit()


# ─── SAVOL-JAVOB TICKETLARI (SUPPORT) ───────────────────────────

def create_support_ticket(user_id: int, question: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO support_tickets (user_id, question_text, status)
            VALUES (?, ?, 'kutilmoqda')
        """, (user_id, question))
        t_id = cursor.lastrowid
        conn.commit()
        return t_id


def answer_support_ticket(ticket_id: int, answer: str) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE support_tickets
            SET answer_text = ?, status = 'javob_berildi'
            WHERE id = ?
        """, (answer, ticket_id))
        conn.commit()
        cursor.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ─── STATISTIKA ─────────────────────────────────────────────────

def get_statistics() -> dict:
    today_str = date.today().strftime("%Y-%m-%d")
    month_str = date.today().strftime("%Y-%m")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Jami foydalanuvchilar
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0
        
        # Bugungi yangi foydalanuvchilar
        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?", (today_str,))
        today_users = cursor.fetchone()[0] or 0
        
        # Jami buyurtmalar
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM orders")
        row = cursor.fetchone()
        total_orders, total_revenue = row[0] or 0, row[1] or 0
        
        # Bugungi buyurtmalar va summa
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
            FROM orders
            WHERE DATE(created_at) = ? AND status != 'rad_etildi'
        """, (today_str,))
        row = cursor.fetchone()
        today_orders, today_revenue = row[0] or 0, row[1] or 0
        
        # Oylik buyurtmalar va summa
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(total_amount), 0)
            FROM orders
            WHERE strftime('%Y-%m', created_at) = ? AND status != 'rad_etildi'
        """, (month_str,))
        row = cursor.fetchone()
        month_orders, month_revenue = row[0] or 0, row[1] or 0
        
        # Mahsulotlar soni
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0] or 0
        
        return {
            "total_users": total_users,
            "today_users": today_users,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "month_orders": month_orders,
            "month_revenue": month_revenue,
            "products_count": products_count
        }
