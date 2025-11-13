from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PharmacyChatbot:
    """Enhanced Chatbot with database awareness for SmartPharma"""
    
    def __init__(self, db):
        """Initialize chatbot with database instance"""
        self.db = db
        logger.info("Chatbot initialized")
    
    def get_response(self, user_message):
        """Generate intelligent response based on database data"""
        try:
            message = user_message.lower().strip()
            
            if not message:
                return "Hello! How can I assist you today? 😊"
            
            # Total products query
            if any(word in message for word in ['total products', 'how many products', 'total medicines', 'products available', 'count products']):
                return self._get_total_products()
            
            # Expiring products query
            elif any(word in message for word in ['expiring', 'expire', 'expired', 'about to expire', 'expiry']):
                return self._get_expiring_info()
            
            # Low stock query
            elif any(word in message for word in ['low stock', 'stock low', 'running out', 'inventory low', 'reorder']):
                return self._get_low_stock_info()
            
            # Inventory status
            elif any(word in message for word in ['inventory', 'stock status', 'inventory status', 'overall status']):
                return self._get_inventory_status()
            
            # Category query
            elif any(word in message for word in ['category', 'categories', 'types', 'medicines by']):
                return self._get_categories()
            
            # Eco score query
            elif any(word in message for word in ['eco', 'sustainable', 'packaging', 'environmental', 'green']):
                return self._get_eco_info()
            
            # Search product
            elif any(word in message for word in ['find', 'search', 'look for', 'show me']):
                return self._search_product(message)
            
            # Help/greeting
            elif any(word in message for word in ['help', 'hello', 'hi', 'what can you', 'can you help', 'assist', 'info']):
                return self._get_help()
            
            else:
                return self._get_default_response()
        
        except Exception as e:
            logger.error(f'Chatbot error: {str(e)}')
            return f"Sorry, I encountered an error: {str(e)}"
    
    def _get_total_products(self):
        """Get total products from database"""
        try:
            products = self.db.get_all_products()
            total = len(products) if products else 0
            total_stock = sum(int(p.get('stock_quantity', 0)) for p in products) if products else 0
            
            if total == 0:
                return "No products in inventory yet."
            
            top_5 = sorted(products, key=lambda x: int(x.get('stock_quantity', 0)), reverse=True)[:5]
            
            response = f"""📦 Inventory Overview
━━━━━━━━━━━━━━━━━━
Total Products: {total}
Total Stock Units: {total_stock}

Top 5 Products by Stock:
"""
            for i, p in enumerate(top_5, 1):
                response += f"{i}. {p['name']}: {p['stock_quantity']} units\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting products: {e}')
            return "Unable to fetch product data"
    
    def _get_expiring_info(self):
        """Get expiring products information"""
        try:
            expiring_7days = self.db.get_expiring_products(days=7)
            
            if not expiring_7days:
                return "✓ Good news! No products expiring in next 7 days."
            
            critical = []
            warning = []
            
            for product in expiring_7days:
                try:
                    expiry_str = str(product.get('expiry_date', ''))
                    if expiry_str:
                        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                        days_left = (expiry_date - datetime.now().date()).days
                        
                        if days_left < 0:
                            critical.append((product, 'EXPIRED'))
                        elif days_left <= 3:
                            critical.append((product, f'{days_left} days'))
                        elif days_left <= 7:
                            warning.append((product, f'{days_left} days'))
                except:
                    pass
            
            response = "⏰ Expiry Alert Status\n"
            
            if critical:
                response += f"\nCRITICAL - {len(critical)} item(s):\n"
                for prod, info in critical[:5]:
                    response += f"  • {prod['name']} - {info} (Stock: {prod['stock_quantity']})\n"
            
            if warning:
                response += f"\nWARNING - {len(warning)} item(s):\n"
                for prod, info in warning[:5]:
                    response += f"  • {prod['name']} - {info} (Stock: {prod['stock_quantity']})\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting expiry info: {e}')
            return "Unable to fetch expiry data"
    
    def _get_low_stock_info(self):
        """Get low stock products"""
        try:
            low_stock = self.db.get_low_stock_products(threshold=50)
            
            if not low_stock:
                return "✓ All products have healthy stock levels!"
            
            response = f"📉 Low Stock Alert ({len(low_stock)} items)\n"
            response += "━━━━━━━━━━━━━━━━━━\n\n"
            
            for prod in sorted(low_stock, key=lambda x: int(x.get('stock_quantity', 0)))[:10]:
                stock = int(prod.get('stock_quantity', 0))
                status = "CRITICAL" if stock < 10 else "LOW"
                response += f"[{status}] {prod['name']}\n"
                response += f"  Stock: {stock} units\n"
                response += f"  Expiry: {prod.get('expiry_date', 'N/A')}\n\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting low stock: {e}')
            return "Unable to fetch stock data"
    
    def _get_inventory_status(self):
        """Get complete inventory status"""
        try:
            products = self.db.get_all_products()
            expiring = self.db.get_expiring_products(days=7)
            low_stock = self.db.get_low_stock_products(threshold=50)
            
            total_products = len(products) if products else 0
            total_stock = sum(int(p.get('stock_quantity', 0)) for p in products) if products else 0
            avg_eco = sum(float(p.get('eco_score', 5)) for p in products) / total_products if total_products > 0 else 0
            total_value = sum(float(p.get('price', 0)) * int(p.get('stock_quantity', 0)) for p in products) if products else 0
            
            response = f"""📊 Inventory Status Report
━━━━━━━━━━━━━━━━━━━━━━━━
📦 Total Products: {total_products}
📊 Total Stock Units: {total_stock}
💰 Total Inventory Value: ₹{total_value:.2f}
🌱 Avg Eco Score: {avg_eco:.1f}/10

⚠️ Issues Found:
🔴 Expiring (7 days): {len(expiring)}
📉 Low Stock Items: {len(low_stock)}

💡 Recommendations:
1. Review expiring products for disposal planning
2. Reorder items with critical stock levels
3. Check packaging sustainability scores
"""
            return response
        
        except Exception as e:
            logger.error(f'Error getting inventory status: {e}')
            return "Unable to fetch inventory status"
    
    def _get_categories(self):
        """Get product categories"""
        try:
            products = self.db.get_all_products()
            
            if not products:
                return "No products in database"
            
            categories = {}
            for prod in products:
                cat = prod.get('category', 'Other')
                if cat not in categories:
                    categories[cat] = {'count': 0, 'stock': 0}
                categories[cat]['count'] += 1
                categories[cat]['stock'] += int(prod.get('stock_quantity', 0))
            
            response = "📋 Product Categories\n"
            response += "━━━━━━━━━━━━━━━━━━\n\n"
            
            for cat in sorted(categories.keys(), key=lambda x: categories[x]['count'], reverse=True):
                data = categories[cat]
                response += f"• {cat}\n"
                response += f"  Products: {data['count']}\n"
                response += f"  Stock: {data['stock']} units\n\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting categories: {e}')
            return "Unable to fetch categories"
    
    def _get_eco_info(self):
        """Get eco-score and sustainability info"""
        try:
            products = self.db.get_all_products()
            
            if not products:
                return "No eco data available"
            
            packaging_types = {}
            for prod in products:
                pkg_type = prod.get('packaging_type', 'Unknown')
                eco = float(prod.get('eco_score', 5))
                
                if pkg_type not in packaging_types:
                    packaging_types[pkg_type] = {'count': 0, 'total_eco': 0}
                
                packaging_types[pkg_type]['count'] += 1
                packaging_types[pkg_type]['total_eco'] += eco
            
            response = "🌱 Eco-Score & Packaging Analysis\n"
            response += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for pkg_type in sorted(packaging_types.keys()):
                data = packaging_types[pkg_type]
                avg_eco = data['total_eco'] / data['count']
                
                if avg_eco >= 8.5:
                    rating = "Excellent"
                elif avg_eco >= 7:
                    rating = "Good"
                elif avg_eco >= 5:
                    rating = "Fair"
                else:
                    rating = "Poor"
                
                response += f"• {pkg_type.title()}\n"
                response += f"  Products: {data['count']}\n"
                response += f"  Eco Score: {avg_eco:.1f}/10 ({rating})\n\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error getting eco info: {e}')
            return "Unable to fetch eco data"
    
    def _search_product(self, message):
        """Search for a specific product"""
        try:
            products = self.db.get_all_products()
            
            # Extract search term
            words = message.split()
            search_terms = [w for w in words if w not in ['find', 'search', 'look', 'for', 'show', 'me']]
            search_term = ' '.join(search_terms).strip() if search_terms else ''
            
            if not search_term:
                return "Please specify a product name or barcode to search"
            
            results = []
            for prod in products:
                if (search_term.lower() in prod['name'].lower() or 
                    search_term.lower() in str(prod.get('barcode', '')).lower() or
                    search_term.lower() in prod.get('category', '').lower()):
                    results.append(prod)
            
            if not results:
                return f"No products found matching '{search_term}'"
            
            response = f"Search Results for '{search_term}':\n"
            response += "━━━━━━━━━━━━━━━━━━\n\n"
            
            for prod in results[:5]:
                response += f"📦 {prod['name']}\n"
                response += f"  Barcode: {prod.get('barcode', 'N/A')}\n"
                response += f"  Category: {prod.get('category', 'N/A')}\n"
                response += f"  Stock: {prod['stock_quantity']} units\n"
                response += f"  Price: ₹{prod['price']}\n"
                response += f"  Expiry: {prod.get('expiry_date', 'N/A')}\n\n"
            
            return response
        
        except Exception as e:
            logger.error(f'Error searching product: {e}')
            return "Unable to search products"
    
    def _get_help(self):
        """Get help information"""
        return """👋 Welcome to SmartPharma AI Assistant

I can help you with:

📦 Inventory:
  • "How many products?"
  • "What's expiring?"
  • "Low stock items?"
  • "Inventory status?"

📊 Analytics:
  • "Category information?"
  • "Eco-score analysis?"
  • "Show me [product name]"

💰 Business:
  • "Reorder suggestions?"
  • "Product search?"

Just ask me anything about your pharmacy inventory!
"""
    
    def _get_default_response(self):
        """Get default response for unrecognized queries"""
        return """I didn't quite understand that. Try asking:
• How many products?
• What's expiring?
• Low stock items?
• Inventory status?
• Show me [product name]
• Eco-score analysis?

Type 'help' for more options!
"""