from datetime import datetime, timedelta
import random

class AIPredictors:
    """AI models for demand prediction, expiry forecasting, and eco-scoring"""
    
    def __init__(self, db):
        """Initialize with database instance"""
        self.db = db
        self.seasonal_patterns = {
            'Analgesics': {'peak_months': [1, 2, 11, 12], 'base_demand': 150},
            'Antibiotics': {'peak_months': [1, 3, 11], 'base_demand': 120},
            'Supplements': {'peak_months': [1, 9], 'base_demand': 200},
            'Diabetes': {'peak_months': [], 'base_demand': 100},
            'Gastric': {'peak_months': [2, 7, 8], 'base_demand': 110},
        }
    
    def predict_expiring_medicines(self, days=7):
        """Predict medicines expiring within days"""
        expiring = self.db.get_expiring_products(days=days)
        predictions = []
        
        for product in expiring:
            expiry = datetime.strptime(product['expiry_date'], '%Y-%m-%d').date() if isinstance(product['expiry_date'], str) else product['expiry_date']
            days_left = (expiry - datetime.now().date()).days
            
            predictions.append({
                'id': product['id'],
                'name': product['name'],
                'category': product['category'],
                'expiry_date': str(product['expiry_date']),
                'days_left': days_left,
                'stock': product['stock_quantity'],
                'urgency_score': max(0, 10 - days_left),
                'risk_level': 'critical' if days_left < 2 else 'high' if days_left < 4 else 'medium'
            })
        
        return sorted(predictions, key=lambda x: x['days_left'])
    
    def predict_high_demand_products(self):
        """Predict high-demand products using seasonal patterns"""
        products = self.db.get_all_products()
        current_month = datetime.now().month
        predictions = []
        
        for product in products:
            category = product.get('category', 'Other')
            pattern = self.seasonal_patterns.get(category, {'peak_months': [], 'base_demand': 100})
            
            # Calculate demand multiplier based on season
            is_peak = current_month in pattern['peak_months']
            demand_multiplier = 1.5 if is_peak else 1.0
            predicted_demand = int(pattern['base_demand'] * demand_multiplier)
            
            # Adjust based on current stock
            stock_ratio = product['stock_quantity'] / (predicted_demand + 1)
            confidence = min(95, 60 + (stock_ratio * 10))
            
            predictions.append({
                'id': product['id'],
                'name': product['name'],
                'category': category,
                'current_stock': product['stock_quantity'],
                'predicted_demand': predicted_demand,
                'demand_score': predicted_demand,
                'confidence': round(confidence, 1),
                'recommendation': 'Reorder' if product['stock_quantity'] < predicted_demand else 'Maintain'
            })
        
        return sorted(predictions, key=lambda x: x['predicted_demand'], reverse=True)
    
    def get_eco_score_analysis(self):
        """Analyze packaging eco-scores"""
        products = self.db.get_all_products()
        
        if not products:
            return []
        
        # Group by packaging type
        packaging_stats = {}
        for product in products:
            pkg_type = product.get('packaging_type', 'unknown')
            if pkg_type not in packaging_stats:
                packaging_stats[pkg_type] = {'count': 0, 'total_score': 0, 'products': []}
            
            packaging_stats[pkg_type]['count'] += 1
            packaging_stats[pkg_type]['total_score'] += product['eco_score']
            packaging_stats[pkg_type]['products'].append(product['name'])
        
        # Calculate averages
        analysis = []
        for pkg_type, stats in packaging_stats.items():
            avg_score = stats['total_score'] / stats['count']
            analysis.append({
                'packaging_type': pkg_type,
                'count': stats['count'],
                'avg_eco_score': round(avg_score, 2),
                'rating': 'Excellent' if avg_score >= 8 else 'Good' if avg_score >= 6 else 'Fair' if avg_score >= 4 else 'Poor'
            })
        
        return sorted(analysis, key=lambda x: x['avg_eco_score'], reverse=True)
