# ============================================================================
# File: database.py - Fixed PostgreSQL Database Management
# ============================================================================

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os

class Database:
    """Handle all database operations for SmartPharma AI"""
    
    def __init__(self):
        """Initialize database connection parameters"""
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'password')
        self.database = os.getenv('DB_NAME', 'smartpharma_db')
        self.port = os.getenv('DB_PORT', 5432)
        self.conn = None
    
    def connect(self):
        """Establish connection to PostgreSQL database"""
        try:
            if self.conn is None:
                self.conn = psycopg2.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    port=self.port
                )
                print("✅ Database connected successfully")
            return self.conn
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            print("✅ Database disconnected")
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    barcode VARCHAR(100) UNIQUE,
                    expiry_date DATE,
                    mfg_date DATE,
                    packaging_type VARCHAR(50),
                    eco_score FLOAT DEFAULT 5.0,
                    stock_quantity INT DEFAULT 0,
                    price FLOAT,
                    added_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    product_id INT REFERENCES products(id),
                    alert_type VARCHAR(50),
                    severity VARCHAR(20),
                    message TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    product_id INT REFERENCES products(id),
                    quantity_change INT,
                    transaction_type VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                );
            """)
            
            conn.commit()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            if conn:
                conn.rollback()
    
    def insert_product(self, name, category, barcode, expiry_date, packaging_type, eco_score, stock_quantity, price, mfg_date=None):
        """Insert new product into database"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO products (name, category, barcode, expiry_date, mfg_date, packaging_type, eco_score, stock_quantity, price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (name, category, barcode, expiry_date, mfg_date, packaging_type, eco_score, stock_quantity, price))
            
            product_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ Product '{name}' added with ID {product_id}")
            return product_id
        except psycopg2.IntegrityError as e:
            print(f"❌ Product already exists: {barcode}")
            conn.rollback()
            return None
        except Exception as e:
            print(f"❌ Error inserting product: {e}")
            if conn:
                conn.rollback()
            return None
    
    def get_all_products(self):
        """Retrieve all products from database"""
        try:
            conn = self.connect()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM products WHERE stock_quantity > 0 ORDER BY added_on DESC;")
            products = cursor.fetchall()
            
            # Convert to list of dicts with proper date formatting
            result = []
            for p in products:
                product_dict = dict(p)
                # Convert date objects to strings
                if product_dict.get('expiry_date'):
                    product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
                if product_dict.get('mfg_date'):
                    product_dict['mfg_date'] = product_dict['mfg_date'].strftime('%Y-%m-%d')
                result.append(product_dict)
            
            return result
        except Exception as e:
            print(f"❌ Error fetching products: {e}")
            return []
    
    def get_product_by_barcode(self, barcode):
        """Get product by barcode"""
        try:
            conn = self.connect()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM products WHERE barcode = %s;", (barcode,))
            product = cursor.fetchone()
            
            if product:
                product_dict = dict(product)
                # Convert date objects to strings
                if product_dict.get('expiry_date'):
                    product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
                if product_dict.get('mfg_date'):
                    product_dict['mfg_date'] = product_dict['mfg_date'].strftime('%Y-%m-%d')
                return product_dict
            return None
        except Exception as e:
            print(f"❌ Error fetching product: {e}")
            return None
    
    def get_expiring_products(self, days=4):
        """Get products expiring within specified days"""
        try:
            conn = self.connect()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            future_date = (datetime.now() + timedelta(days=days)).date()
            today = datetime.now().date()
            
            cursor.execute("""
                SELECT * FROM products 
                WHERE expiry_date <= %s AND expiry_date >= %s
                ORDER BY expiry_date ASC;
            """, (future_date, today))
            
            products = cursor.fetchall()
            
            # Convert to list of dicts with proper date formatting
            result = []
            for p in products:
                product_dict = dict(p)
                if product_dict.get('expiry_date'):
                    product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
                if product_dict.get('mfg_date'):
                    product_dict['mfg_date'] = product_dict['mfg_date'].strftime('%Y-%m-%d')
                result.append(product_dict)
            
            print(f"✅ Found {len(result)} expiring products")
            return result
        except Exception as e:
            print(f"❌ Error fetching expiring products: {e}")
            return []
    
    def get_low_stock_products(self, threshold=20):
        """Get products with low stock quantity"""
        try:
            conn = self.connect()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM products 
                WHERE stock_quantity < %s AND stock_quantity > 0
                ORDER BY stock_quantity ASC;
            """, (threshold,))
            
            products = cursor.fetchall()
            
            # Convert to list of dicts with proper date formatting
            result = []
            for p in products:
                product_dict = dict(p)
                if product_dict.get('expiry_date'):
                    product_dict['expiry_date'] = product_dict['expiry_date'].strftime('%Y-%m-%d')
                if product_dict.get('mfg_date'):
                    product_dict['mfg_date'] = product_dict['mfg_date'].strftime('%Y-%m-%d')
                result.append(product_dict)
            
            print(f"✅ Found {len(result)} low stock products")
            return result
        except Exception as e:
            print(f"❌ Error fetching low stock products: {e}")
            return []
    
    def add_sample_data(self):
        """Add sample data for testing"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Check if data already exists
            cursor.execute("SELECT COUNT(*) FROM products;")
            if cursor.fetchone()[0] > 0:
                print("✅ Sample data already exists")
                return
            
            sample_products = [
                ('Aspirin 500mg', 'Analgesics', 'ASP001', (datetime.now() + timedelta(days=2)).date(), (datetime.now() - timedelta(days=300)).date(), 'Cardboard', 8.5, 150, 5.99),
                ('Amoxicillin 250mg', 'Antibiotics', 'AMX001', (datetime.now() + timedelta(days=1)).date(), (datetime.now() - timedelta(days=365)).date(), 'Plastic', 3.5, 10, 12.50),
                ('Vitamin D3', 'Supplements', 'VIT001', (datetime.now() + timedelta(days=90)).date(), (datetime.now() - timedelta(days=200)).date(), 'Glass', 7.5, 300, 9.99),
                ('Ibuprofen 400mg', 'Analgesics', 'IBU001', (datetime.now() + timedelta(days=5)).date(), (datetime.now() - timedelta(days=250)).date(), 'Paper', 8.0, 180, 7.50),
                ('Metformin 500mg', 'Diabetes', 'MET001', (datetime.now() + timedelta(days=3)).date(), (datetime.now() - timedelta(days=180)).date(), 'Plastic', 3.5, 5, 8.75),
                ('Omeprazole 20mg', 'Gastric', 'OMP001', (datetime.now() + timedelta(days=60)).date(), (datetime.now() - timedelta(days=150)).date(), 'Cardboard', 8.5, 220, 14.99),
            ]
            
            for product in sample_products:
                try:
                    cursor.execute("""
                        INSERT INTO products (name, category, barcode, expiry_date, mfg_date, packaging_type, eco_score, stock_quantity, price)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, product)
                except psycopg2.IntegrityError:
                    pass
            
            conn.commit()
            print("✅ Sample data added successfully")
        except Exception as e:
            print(f"❌ Error adding sample data: {e}")
            if conn:
                conn.rollback()
    
    def close(self):
        """Close database connection"""
        self.disconnect()


# ============================================================================
# File: alert_manager.py - Fixed Alert Manager
# ============================================================================

class AlertManager:
    """Manage pharmacy alerts (expiry, stock, etc)"""
    
    def __init__(self, db):
        """Initialize with database instance"""
        self.db = db
    
    def get_expiring_products(self, days=4):
        """Get expiring products within specified days"""
        try:
            products = self.db.get_expiring_products(days=days)
            print(f"✅ AlertManager: Found {len(products)} expiring products")
            return products
        except Exception as e:
            print(f"❌ Error in get_expiring_products: {e}")
            return []
    
    def get_low_stock_products(self, threshold=20):
        """Get low stock products"""
        try:
            products = self.db.get_low_stock_products(threshold=threshold)
            print(f"✅ AlertManager: Found {len(products)} low stock products")
            return products
        except Exception as e:
            print(f"❌ Error in get_low_stock_products: {e}")
            return []
    
    def check_expiring_alerts(self, days=4):
        """Check and create alerts for expiring products"""
        try:
            expiring = self.get_expiring_products(days=days)
            alerts = []
            
            for product in expiring:
                try:
                    # Parse date string
                    expiry_str = product.get('expiry_date')
                    if isinstance(expiry_str, str):
                        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                    else:
                        expiry_date = expiry_str
                    
                    days_left = (expiry_date - datetime.now().date()).days
                    
                    # Determine severity
                    if days_left < 1:
                        severity = 'critical'
                    elif days_left < 3:
                        severity = 'high'
                    else:
                        severity = 'warning'
                    
                    alerts.append({
                        'product_id': product.get('id'),
                        'product_name': product.get('name'),
                        'type': 'expiry',
                        'severity': severity,
                        'message': f"{product.get('name')} expires in {days_left} days",
                        'expiry_date': expiry_str
                    })
                except Exception as e:
                    print(f"❌ Error processing product {product.get('name')}: {e}")
                    continue
            
            return alerts
        except Exception as e:
            print(f"❌ Error in check_expiring_alerts: {e}")
            return []
    
    def generate_reorder_suggestions(self):
        """Generate product reorder suggestions based on stock and expiry"""
        try:
            low_stock = self.get_low_stock_products(threshold=50)
            suggestions = []
            
            for product in low_stock:
                suggestions.append({
                    'product_id': product.get('id'),
                    'product_name': product.get('name'),
                    'current_stock': product.get('stock_quantity'),
                    'suggested_reorder': int(product.get('stock_quantity', 0) * 2),
                    'priority': 'high' if product.get('stock_quantity', 0) < 20 else 'medium'
                })
            
            return suggestions
        except Exception as e:
            print(f"❌ Error in generate_reorder_suggestions: {e}")
            return []