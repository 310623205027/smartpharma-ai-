from datetime import datetime, timedelta

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