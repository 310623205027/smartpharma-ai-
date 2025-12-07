import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Initialize database connection"""
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            self.conn = psycopg2.connect(database_url)
        else:
            # Local fallback
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', '2006'),
                dbname=os.getenv('DB_NAME', 'smartpharma_db'),
                port=int(os.getenv('DB_PORT', 5432))
            )
    
    def connect(self):
        """Ensure database connection is active"""
        try:
            if self.conn is None or self.conn.closed:
                database_url = os.getenv('DATABASE_URL')
                if database_url:
                    self.conn = psycopg2.connect(database_url)
                else:
                    self.conn = psycopg2.connect(
                        host=os.getenv('DB_HOST', 'localhost'),
                        user=os.getenv('DB_USER', 'postgres'),
                        password=os.getenv('DB_PASSWORD', '2006'),
                        dbname=os.getenv('DB_NAME', 'smartpharma_db'),
                        port=int(os.getenv('DB_PORT', 5432)),
                        connect_timeout=5
                    )
                logger.info("✓ Database connected successfully")
            return self.conn
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        try:
            if self.conn and not self.conn.closed:
                self.conn.close()
                self.conn = None
                logger.info("✓ Database disconnected")
        except Exception as e:
            logger.error(f"✗ Error disconnecting: {e}")

    # Updated helper method to safely create a cursor
    def get_cursor(self):
        """Return a new cursor, ensuring the connection is alive"""
        conn = self.connect()
        return conn.cursor(cursor_factory=RealDictCursor)

    def create_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    barcode VARCHAR(100) UNIQUE,
                    expiry_date DATE,
                    packaging_type VARCHAR(50),
                    eco_score FLOAT DEFAULT 5.0,
                    stock_quantity INT DEFAULT 0,
                    price FLOAT DEFAULT 0.0,
                    added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    product_id INT REFERENCES products(id) ON DELETE CASCADE,
                    alert_type VARCHAR(50),
                    severity VARCHAR(20),
                    message TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    product_id INT REFERENCES products(id) ON DELETE CASCADE,
                    quantity_change INT,
                    transaction_type VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_message TEXT,
                    bot_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("✓ Database tables created successfully")
        except Exception as e:
            logger.error(f"✗ Error creating tables: {e}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()

    def insert_product(self, name, category, barcode, expiry_date, packaging_type, eco_score, stock_quantity, price):
        """Insert new product"""
        cursor = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO products 
                (name, category, barcode, expiry_date, packaging_type, eco_score, stock_quantity, price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, category, barcode, expiry_date, packaging_type, float(eco_score), int(stock_quantity), float(price)))
            
            product_id = cursor.fetchone()['id']
            conn.commit()
            logger.info(f"✓ Product '{name}' added with ID {product_id}")
            return product_id
        except psycopg2.IntegrityError:
            if conn:
                conn.rollback()
            logger.error(f"✗ Product barcode already exists: {barcode}")
            return None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"✗ Error inserting product: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_products(self):
        cursor = None
        try:
            cursor = self.get_cursor()
            cursor.execute("""
                SELECT id, name, category, barcode, expiry_date, packaging_type, eco_score, stock_quantity, price, added_on
                FROM products
                ORDER BY added_on DESC
            """)
            products = cursor.fetchall()
            result = []
            for p in products:
                product_dict = dict(p)
                if product_dict.get('expiry_date'):
                    product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
                if product_dict.get('added_on'):
                    product_dict['added_on'] = product_dict['added_on'].strftime('%Y-%m-%d %H:%M:%S')
                result.append(product_dict)
            logger.info(f"✓ Retrieved {len(result)} products")
            return result
        except Exception as e:
            logger.error(f"✗ Error fetching products: {e}")
            return []
    
    def get_product_by_barcode(self, barcode):
    """Get product by barcode"""
    cursor = None
    try:
        cursor = self.get_cursor()
        cursor.execute("""
            SELECT id, name, category, barcode, expiry_date, 
                   packaging_type, eco_score, stock_quantity, price
            FROM products 
            WHERE barcode = %s
        """, (barcode,))
        
        product = cursor.fetchone()
        if product:
            product_dict = dict(product)
            if product_dict.get('expiry_date'):
                product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
            logger.info(f"✓ Product found: {product_dict['name']}")
            return product_dict
        
        logger.warning(f"✗ Product not found with barcode: {barcode}")
        return None
    except Exception as e:
        logger.error(f"✗ Error fetching product by barcode: {e}")
        return None
    finally:
        if cursor:
            cursor.close()

def get_product_by_id(self, product_id):
    """Get product by ID"""
    cursor = None
    try:
        cursor = self.get_cursor()
        cursor.execute("""
            SELECT id, name, category, barcode, expiry_date, 
                   packaging_type, eco_score, stock_quantity, price
            FROM products 
            WHERE id = %s
        """, (product_id,))
        
        product = cursor.fetchone()
        if product:
            product_dict = dict(product)
            if product_dict.get('expiry_date'):
                product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
            return product_dict
        return None
    except Exception as e:
        logger.error(f"✗ Error fetching product by ID: {e}")
        return None
    finally:
        if cursor:
            cursor.close()

def get_expiring_products(self, days=7):
    """Get products expiring within specified days"""
    cursor = None
    try:
        cursor = self.get_cursor()
        future_date = (datetime.now() + timedelta(days=days)).date()
        today = datetime.now().date()
        
        cursor.execute("""
            SELECT id, name, category, barcode, expiry_date, 
                   packaging_type, eco_score, stock_quantity, price
            FROM products 
            WHERE expiry_date <= %s AND expiry_date >= %s
            AND stock_quantity > 0
            ORDER BY expiry_date ASC
        """, (future_date, today))
        
        products = cursor.fetchall()
        result = []
        for p in products:
            product_dict = dict(p)
            if product_dict.get('expiry_date'):
                product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
            result.append(product_dict)
        
        logger.info(f"✓ Found {len(result)} expiring products")
        return result
    except Exception as e:
        logger.error(f"✗ Error fetching expiring products: {e}")
        return []
    finally:
        if cursor:
            cursor.close()

def get_low_stock_products(self, threshold=50):
    """Get products with low stock quantity"""
    cursor = None
    try:
        cursor = self.get_cursor()
        cursor.execute("""
            SELECT id, name, category, barcode, expiry_date, 
                   packaging_type, eco_score, stock_quantity, price
            FROM products 
            WHERE stock_quantity > 0 AND stock_quantity < %s
            ORDER BY stock_quantity ASC
        """, (threshold,))
        
        products = cursor.fetchall()
        result = []
        for p in products:
            product_dict = dict(p)
            if product_dict.get('expiry_date'):
                product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
            result.append(product_dict)
        
        logger.info(f"✓ Found {len(result)} low stock products")
        return result
    except Exception as e:
        logger.error(f"✗ Error fetching low stock products: {e}")
        return []
    finally:
        if cursor:
            cursor.close()

def update_stock(self, product_id, quantity_change):
    """Update product stock quantity"""
    cursor = None
    try:
        cursor = self.get_cursor()
        cursor.execute("""
            UPDATE products 
            SET stock_quantity = stock_quantity + %s,
                updated_on = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING stock_quantity
        """, (quantity_change, product_id))
        
        new_stock = cursor.fetchone()
        self.conn.commit()
        
        if new_stock:
            logger.info(f"✓ Stock updated for product {product_id}: {new_stock['stock_quantity']} units")
            return new_stock['stock_quantity']
        return None
    except Exception as e:
        if self.conn:
            self.conn.rollback()
        logger.error(f"✗ Error updating stock: {e}")
        return None
    finally:
        if cursor:
            cursor.close()

def add_sample_data(self):
    """Add sample data for testing"""
    cursor = None
    try:
        cursor = self.get_cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM products")
        if cursor.fetchone()['count'] > 0:
            logger.info("✓ Sample data already exists")
            return
        
        sample_products = [
            ('Aspirin 500mg', 'Analgesics', 'ASP001', (datetime.now() + timedelta(days=2)).date(), 'Cardboard', 8.5, 150, 5.99),
            ('Amoxicillin 250mg', 'Antibiotics', 'AMX001', (datetime.now() + timedelta(days=1)).date(), 'Plastic', 3.5, 10, 12.50),
            ('Vitamin D3', 'Supplements', 'VIT001', (datetime.now() + timedelta(days=90)).date(), 'Glass', 7.5, 300, 9.99),
            ('Ibuprofen 400mg', 'Analgesics', 'IBU001', (datetime.now() + timedelta(days=5)).date(), 'Paper', 8.0, 180, 7.50),
            ('Metformin 500mg', 'Diabetes', 'MET001', (datetime.now() + timedelta(days=3)).date(), 'Plastic', 3.5, 5, 8.75),
            ('Omeprazole 20mg', 'Gastric', 'OMP001', (datetime.now() + timedelta(days=60)).date(), 'Cardboard', 8.5, 220, 14.99),
            ('Paracetamol 650mg', 'Pain Relief', 'PAR001', (datetime.now() + timedelta(days=45)).date(), 'Paper', 8.0, 280, 6.50),
            ('Cough Syrup', 'Cough Relief', 'COUGH001', (datetime.now() + timedelta(days=20)).date(), 'Glass', 7.5, 95, 11.99),
        ]
        
        for product in sample_products:
            try:
                cursor.execute("""
                    INSERT INTO products 
                    (name, category, barcode, expiry_date, packaging_type, eco_score, stock_quantity, price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, product)
            except psycopg2.IntegrityError:
                self.conn.rollback()
        
        self.conn.commit()
        logger.info("✓ Sample data added successfully")
    except Exception as e:
        logger.error(f"✗ Error adding sample data: {e}")
        if self.conn:
            self.conn.rollback()
    finally:
        if cursor:
            cursor.close()
