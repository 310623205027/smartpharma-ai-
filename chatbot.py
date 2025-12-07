from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PharmacyChatbot:
    """Enhanced Chatbot with database awareness"""
    
    def __init__(self, db):
        """Initialize chatbot with database instance"""
        self.db = db
    
    def get_response(self, user_message, db=None):
        """Generate intelligent response based on database data"""
        message = user_message.lower().strip()
        
        try:
            # Total products query
            if any(word in message for word in ['total products', 'how many products', 'total medicines', 'products available']):
                return self._get_total_products()
            
            # Expiring products query
            elif any(word in message for word in ['expiring', 'expire', 'expired', 'about to expire']):
                return self._get_expiring_info()
            
            # Low stock query
            elif any(word in message for word in ['low stock', 'stock low', 'running out', 'inventory low']):
                return self._get_low_stock_info()
            
            # Inventory status
            elif any(word in message for word in ['inventory', 'stock status', 'inventory status']):
                return self._get_inventory_status()
            
            # High demand query
            elif any(word in message for word in ['demand', 'high demand', 'popular', 'bestseller']):
                return self._get_demand_info()
            
            # Category query
            elif any(word in message for word in ['category', 'categories', 'types']):
                return self._get_categories()
            
            # Reorder query
            elif any(word in message for word in ['reorder', 'order', 'need to order']):
                return self._get_reorder_suggestions()
            
            # Eco score query
            elif any(word in message for word in ['eco', 'sustainable', 'packaging', 'environmental']):
                return self._get_eco_info()
            
            # Help/greeting
            elif any(word in message for word in ['help', 'hello', 'hi', 'what can you', 'can you help']):
                return self._get_help()
            
            else:
                return "🤔 I didn't understand that. Try asking:\n• How many products?\n• What's expiring?\n• Low stock items?\n• Inventory status?\n• High demand products?\n• Category information?\n• Reorder suggestions?"
        
        except Exception as e:
            logger.error(f'Chatbot error: {str(e)}')
            return f"❌ Error: {str(e)}"
    
    def _get_total_products(self):
        """Get total products from database"""
        try:
            products = self.db.get_all_products()
            total = len(products) if products else 0
            total_stock = sum(p.get('stock_quantity', 0) for p in products) if products else 0
            
            if total == 0:
                return "📊 No products in database yet."
            
            return f"""📦 **Inventory Overview**
━━━━━━━━━━━━━━━━━━
Total Products: {total}
Total Stock: {total_stock} units

Top 5 Products by Stock:
"""  + "\n".join([f"• {p['name']}: {p['stock_quantity']} units" for p in sorted(products, key=lambda x: x.get('stock_quantity', 0), reverse=True)[:5]])
        
        except Exception as e:
            logger.error(f'Error getting products: {e}')
            return "❌ Unable to fetch product data"
    
    def _get_expiring_info(self):
        """Get expiring products information"""
        try:
            expiring_4days = self.db.get_expiring_products(days=4)
            expiring_7days = self.db.get_expiring_products(days=7)
            
            if not expiring_4days:
                return "✅ **Expiry Status**\nNo products expiring in next 7 days. Good stock health!"
            
            critical = []
            warning = []
            
            for product in expiring_7days:
                try:
                    expiry_date = datetime.strptime(
                        str(product.get('expiry_date', '')),
                        '%Y-%m-%d'
                    ).date()
                    days_left = (expiry_date - datetime.now().date()).days
                    
                    if days_left < 0:
                        critical.append((product, 'EXPIRED'))
                    elif days_left <= 3:
                        critical.append((product, f'{days_left} days'))
                    elif days_left <= 7:
                        warning.append((product, f'{days_left} days'))
                except:
                    pass
            
            response = "⏰ **Expiry Alert**\n━━━━━━━━━━━━━━━━━━\n"
            
            if critical:
                response += f"\n🔴 **Critical ({len(critical)}):**\n"
                for prod, info in critical[:5]:
                    response += f"• {prod['name']} - {info} (Stock: {prod['stock_quantity']})\n"
            
            if warning:
                response += f"\n🟡 **Warning ({len(warning)}):**\n"
                for prod, info in warning[:5]:
                    response += f"• {prod['name']} - {info} (Stock: {prod['stock_quantity']})\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting expiry info: {e}')
            return "❌ Unable to fetch expiry data"
    
    def _get_low_stock_info(self):
        """Get low stock products"""
        try:
            low_stock = self.db.get_low_stock_products(threshold=30)
            
            if not low_stock:
                return "✅ **Stock Status**\nAll products have healthy stock levels!"
            
            response = f"📉 **Low Stock Alert** ({len(low_stock)} items)\n━━━━━━━━━━━━━━━━━━\n\n"
            
            for prod in sorted(low_stock, key=lambda x: x.get('stock_quantity', 0))[:10]:
                stock = prod.get('stock_quantity', 0)
                status = "🔴 CRITICAL" if stock < 10 else "🟡 LOW"
                response += f"{status}: {prod['name']}\n  Stock: {stock} units\n  Expiry: {prod.get('expiry_date', 'N/A')}\n\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting low stock: {e}')
            return "❌ Unable to fetch stock data"
    
    def _get_inventory_status(self):
        """Get complete inventory status"""
        try:
            products = self.db.get_all_products()
            expiring = self.db.get_expiring_products(days=7)
            low_stock = self.db.get_low_stock_products(threshold=30)
            
            total_products = len(products) if products else 0
            total_stock = sum(p.get('stock_quantity', 0) for p in products) if products else 0
            avg_eco = sum(p.get('eco_score', 5) for p in products) / total_products if total_products > 0 else 0
            
            response = f"""📊 **Inventory Status Report**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Total Products: {total_products}
📊 Total Stock Units: {total_stock}
🌱 Avg Eco Score: {avg_eco:.1f}/10

⚠️ **Issues:**
🔴 Expiring (7 days): {len(expiring)}
📉 Low Stock: {len(low_stock)}

💡 **Recommendations:**
1. Review expiring products - may need disposal
2. Reorder low stock items immediately
3. Check packaging sustainability
"""
            return response
        
        except Exception as e:
            logger.error(f'Error getting inventory status: {e}')
            return "❌ Unable to fetch inventory status"
    
    def _get_demand_info(self):
        """Get high demand products"""
        try:
            products = self.db.get_all_products()
            
            if not products:
                return "📊 No demand data available"
            
            # Sort by stock/usage ratio
            high_demand = sorted(products, key=lambda x: x.get('stock_quantity', 0))[:5]
            
            response = "🔥 **High Demand Products**\n━━━━━━━━━━━━━━━━━━\n\n"
            
            for prod in high_demand:
                response += f"• {prod['name']}\n"
                response += f"  Category: {prod['category']}\n"
                response += f"  Stock: {prod['stock_quantity']} units\n"
                response += f"  Price: ${prod['price']}\n\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting demand info: {e}')
            return "❌ Unable to fetch demand data"
    
    def _get_categories(self):
        """Get product categories"""
        try:
            products = self.db.get_all_products()
            
            if not products:
                return "📋 No products in database"
            
            categories = {}
            for prod in products:
                cat = prod.get('category', 'Other')
                categories[cat] = categories.get(cat, 0) + 1
            
            response = "📋 **Product Categories**\n━━━━━━━━━━━━━━━━━━\n\n"
            
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                response += f"• {cat}: {count} products\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting categories: {e}')
            return "❌ Unable to fetch categories"
    
    def _get_reorder_suggestions(self):
        """Get reorder suggestions"""
        try:
            low_stock = self.db.get_low_stock_products(threshold=50)
            
            if not low_stock:
                return "✅ All products have sufficient stock. No reorder needed!"
            
            response = "📋 **Reorder Suggestions**\n━━━━━━━━━━━━━━━━━━\n\n"
            
            total_cost = 0
            for prod in sorted(low_stock, key=lambda x: x.get('stock_quantity', 0))[:10]:
                suggested_qty = int(prod.get('stock_quantity', 0) * 2)
                cost = suggested_qty * prod.get('price', 0)
                total_cost += cost
                
                response += f"• {prod['name']}\n"
                response += f"  Current: {prod['stock_quantity']} units\n"
                response += f"  Order: {suggested_qty} units\n"
                response += f"  Est. Cost: ${cost:.2f}\n\n"
            
            response += f"📊 **Total Estimated Cost: ${total_cost:.2f}**"
            return response
        
        except Exception as e:
            logger.error(f'Error getting reorder suggestions: {e}')
            return "❌ Unable to generate reorder suggestions"
    
    def _get_eco_info(self):
        """Get eco-score and sustainability info"""
        try:
            products = self.db.get_all_products()
            
            if not products:
                return "📊 No eco data available"
            
            packaging_types = {}
            for prod in products:
                pkg_type = prod.get('packaging_type', 'Unknown')
                eco = prod.get('eco_score', 5)
                
                if pkg_type not in packaging_types:
                    packaging_types[pkg_type] = {'count': 0, 'total_eco': 0}
                
                packaging_types[pkg_type]['count'] += 1
                packaging_types[pkg_type]['total_eco'] += eco
            
            response = "🌱 **Eco-Score & Packaging Analysis**\n━━━━━━━━━━━━━━━━━━\n\n"
            
            for pkg_type in sorted(packaging_types.keys()):
                data = packaging_types[pkg_type]
                avg_eco = data['total_eco'] / data['count']
                rating = '⭐⭐⭐⭐⭐' if avg_eco >= 8.5 else '⭐⭐⭐⭐' if avg_eco >= 7 else '⭐⭐⭐' if avg_eco >= 5 else '⭐⭐'
                
                response += f"• {pkg_type.title()}\n"
                response += f"  Products: {data['count']}\n"
                response += f"  Eco Score: {avg_eco:.1f}/10 {rating}\n\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting eco info: {e}')
            return "❌ Unable to fetch eco data"
    
    def _get_help(self):
        """Get help information"""
        return """👋 **Welcome to SmartPharma AI Assistant**

I can help you with:

📦 **Inventory:**
  "How many products?"
  "What's expiring?"
  "Low stock items?"

📊 **Analytics:**
  "Inventory status?"
  "Category information?"
  "High demand products?"

💰 **Business:**
  "Reorder suggestions?"
  "Eco score analysis?"

Just ask me anything about your pharmacy inventory! 💊"""