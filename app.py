# ============================================================================
# 🧠 SmartPharma AI - Intelligent Pharmacy Waste & Packaging Management System
# ============================================================================
# File: app.py (Main Flask Application)

from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import json
from database import Database
from barcode_reader import BarcodeReader
from alert_manager import AlertManager
from ai_predictor import AIPredictors
from chatbot import PharmacyChatbot

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload

# Initialize modules
db = Database()
barcode_reader = BarcodeReader()
alert_manager = AlertManager(db)
ai_predictor = AIPredictors(db)
chatbot = PharmacyChatbot(db)

# ============================================================================
# 📊 DASHBOARD ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/dashboard')
def get_dashboard_data():
    """Fetch stock and analytics data for dashboard"""
    try:
        # Get all products
        products = db.get_all_products()
        
        # Calculate metrics
        total_products = len(products)
        total_stock = sum(p['stock_quantity'] for p in products)
        avg_eco_score = sum(p['eco_score'] for p in products) / total_products if total_products > 0 else 0
        
        # Get expiring soon (< 4 days)
        expiring = alert_manager.get_expiring_products(days=4)
        
        # Get high demand products (sample AI prediction)
        high_demand = ai_predictor.predict_high_demand_products()
        
        return jsonify({
            'status': 'success',
            'metrics': {
                'total_products': total_products,
                'total_stock': total_stock,
                'avg_eco_score': round(avg_eco_score, 2),
                'expiring_count': len(expiring),
                'waste_prevented_kg': round(total_products * 0.15, 2)  # Demo calculation
            },
            'expiring_soon': expiring[:5],
            'high_demand': high_demand[:5],
            'products': products[:10]  # Latest 10 products
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# 📤 UPLOAD & BARCODE ROUTES
# ============================================================================

@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    """Upload page template"""
    return render_template('upload.html')

@app.route('/api/upload', methods=['POST'])
def upload_barcode():
    """Handle barcode image upload and decode"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Save temporary file
        filepath = f"temp_{file.filename}"
        file.save(filepath)
        
        # Decode barcode
        decoded_data = barcode_reader.decode_barcode(filepath)
        
        # Clean up temp file
        os.remove(filepath)
        
        if not decoded_data:
            return jsonify({'status': 'error', 'message': 'No barcode detected'}), 400
        
        return jsonify({
            'status': 'success',
            'barcode': decoded_data['barcode'],
            'format': decoded_data['format'],
            'message': 'Barcode decoded successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/add-product', methods=['POST'])
def add_product():
    """Add new product to database"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['name', 'category', 'barcode', 'expiry_date', 'packaging_type', 'stock_quantity', 'price']
        if not all(k in data for k in required):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        # Calculate eco_score based on packaging type
        eco_scores = {
            'plastic': 3.5,
            'paper': 8.0,
            'glass': 7.5,
            'cardboard': 8.5,
            'metal': 7.0,
            'biodegradable': 9.5
        }
        eco_score = eco_scores.get(data['packaging_type'].lower(), 5.0)
        
        # Insert product
        product_id = db.insert_product(
            name=data['name'],
            category=data['category'],
            barcode=data['barcode'],
            expiry_date=data['expiry_date'],
            packaging_type=data['packaging_type'],
            eco_score=eco_score,
            stock_quantity=int(data['stock_quantity']),
            price=float(data['price'])
        )
        
        return jsonify({
            'status': 'success',
            'product_id': product_id,
            'message': 'Product added successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# 🚨 ALERTS ROUTES - ENHANCED WITH DETAILED ALERT SYSTEM
# ============================================================================

@app.route('/alerts')
def alerts_page():
    """Alerts page template"""
    return render_template('alerts.html')

@app.route('/api/alerts')
def get_alerts():
    """Get active alerts (expiring products, low stock, etc)"""
    try:
        print("=== Fetching Alerts ===")
        
        expiring = alert_manager.get_expiring_products(days=4)
        low_stock = alert_manager.get_low_stock_products(threshold=20)
        
        print(f"Expiring products: {len(expiring)}")
        print(f"Low stock products: {len(low_stock)}")
        
        alerts = []
        alert_id = 1
        
        # Process expiring product alerts
        for product in expiring:
            try:
                expiry_str = product.get('expiry_date')
                if isinstance(expiry_str, str):
                    expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
                else:
                    expiry_date = expiry_str
                
                days_left = (expiry_date - datetime.now().date()).days
                severity = 'critical' if days_left < 2 else 'warning'
                
                alerts.append({
                    'alert_id': alert_id,
                    'type': 'expiry',
                    'severity': severity,
                    'product': product.get('name', 'Unknown'),
                    'product_id': product.get('id'),
                    'message': f"Expires in {days_left} days (on {expiry_str})",
                    'details': {
                        'barcode': product.get('barcode', 'N/A'),
                        'category': product.get('category', 'N/A'),
                        'expiry_date': expiry_str,
                        'current_stock': product.get('stock_quantity', 0)
                    },
                    'timestamp': datetime.now().isoformat(),
                    'action_required': True
                })
                alert_id += 1
            except Exception as e:
                print(f"Error processing expiring product: {e}")
                continue
        
        # Process low stock alerts
        for product in low_stock[:5]:
            try:
                alerts.append({
                    'alert_id': alert_id,
                    'type': 'stock',
                    'severity': 'warning',
                    'product': product.get('name', 'Unknown'),
                    'product_id': product.get('id'),
                    'message': f"Stock low: {product.get('stock_quantity', 0)} units remaining",
                    'details': {
                        'barcode': product.get('barcode', 'N/A'),
                        'category': product.get('category', 'N/A'),
                        'current_stock': product.get('stock_quantity', 0),
                        'price': f"${product.get('price', 0):.2f}",
                        'packaging': product.get('packaging_type', 'N/A')
                    },
                    'timestamp': datetime.now().isoformat(),
                    'action_required': True
                })
                alert_id += 1
            except Exception as e:
                print(f"Error processing low stock product: {e}")
                continue
        
        # Sort alerts by severity and timestamp
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        alerts.sort(key=lambda x: (severity_order.get(x['severity'], 3), x['timestamp']))
        
        print(f"Total alerts generated: {len(alerts)}")
        
        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'count': len(alerts),
            'critical_count': sum(1 for a in alerts if a['severity'] == 'critical'),
            'warning_count': sum(1 for a in alerts if a['severity'] == 'warning')
        })
    except Exception as e:
        print(f"Error in get_alerts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/alerts/<int:alert_id>')
def get_alert_details(alert_id):
    """Get detailed information about a specific alert"""
    try:
        # Get all alerts
        expiring = alert_manager.get_expiring_products(days=4)
        low_stock = alert_manager.get_low_stock_products(threshold=20)
        
        all_alerts = []
        current_id = 1
        
        for product in expiring:
            days_left = (datetime.strptime(product['expiry_date'], '%Y-%m-%d').date() - datetime.now().date()).days
            
            if current_id == alert_id:
                return jsonify({
                    'status': 'success',
                    'alert': {
                        'alert_id': current_id,
                        'type': 'expiry',
                        'severity': 'critical' if days_left < 2 else 'warning',
                        'product_name': product['name'],
                        'product_id': product.get('id'),
                        'full_details': {
                            'barcode': product.get('barcode'),
                            'category': product.get('category'),
                            'expiry_date': product.get('expiry_date'),
                            'current_stock': product.get('stock_quantity'),
                            'packaging_type': product.get('packaging_type'),
                            'price': product.get('price'),
                            'eco_score': product.get('eco_score'),
                            'days_until_expiry': days_left
                        },
                        'recommended_actions': [
                            'Review current stock levels',
                            'Consider promotional discounts',
                            'Plan disposal if necessary',
                            'Update inventory records'
                        ],
                        'timestamp': datetime.now().isoformat()
                    }
                })
            current_id += 1
        
        for product in low_stock:
            if current_id == alert_id:
                return jsonify({
                    'status': 'success',
                    'alert': {
                        'alert_id': current_id,
                        'type': 'stock',
                        'severity': 'warning',
                        'product_name': product['name'],
                        'product_id': product.get('id'),
                        'full_details': {
                            'barcode': product.get('barcode'),
                            'category': product.get('category'),
                            'current_stock': product.get('stock_quantity'),
                            'packaging_type': product.get('packaging_type'),
                            'price': product.get('price'),
                            'eco_score': product.get('eco_score')
                        },
                        'recommended_actions': [
                            'Place order for new stock',
                            'Monitor sales trends',
                            'Check supplier availability',
                            'Update reorder levels'
                        ],
                        'timestamp': datetime.now().isoformat()
                    }
                })
            current_id += 1
        
        return jsonify({'status': 'error', 'message': 'Alert not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/alerts/filter', methods=['POST'])
def filter_alerts():
    """Filter alerts by type and severity"""
    try:
        data = request.get_json()
        alert_type = data.get('type')  # 'expiry', 'stock', or 'all'
        severity = data.get('severity')  # 'critical', 'warning', or 'all'
        
        expiring = alert_manager.get_expiring_products(days=4)
        low_stock = alert_manager.get_low_stock_products(threshold=20)
        
        alerts = []
        alert_id = 1
        
        # Process expiring alerts
        if alert_type in ['expiry', 'all']:
            for product in expiring:
                days_left = (datetime.strptime(product['expiry_date'], '%Y-%m-%d').date() - datetime.now().date()).days
                sev = 'critical' if days_left < 2 else 'warning'
                
                if severity == 'all' or severity == sev:
                    alerts.append({
                        'alert_id': alert_id,
                        'type': 'expiry',
                        'severity': sev,
                        'product': product['name'],
                        'message': f"Expires in {days_left} days",
                        'timestamp': datetime.now().isoformat()
                    })
                    alert_id += 1
        
        # Process stock alerts
        if alert_type in ['stock', 'all']:
            for product in low_stock[:3]:
                if severity == 'all' or severity == 'warning':
                    alerts.append({
                        'alert_id': alert_id,
                        'type': 'stock',
                        'severity': 'warning',
                        'product': product['name'],
                        'message': f"Stock low: {product['stock_quantity']} units",
                        'timestamp': datetime.now().isoformat()
                    })
                    alert_id += 1
        
        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/alerts/dismiss/<int:alert_id>', methods=['POST'])
def dismiss_alert(alert_id):
    """Mark an alert as dismissed"""
    try:
        # This would typically update a database field to mark alert as dismissed
        return jsonify({
            'status': 'success',
            'message': f'Alert {alert_id} dismissed successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/sales_counter')
def sales_counter():
    """Sales counter page"""
    return render_template('sales_counter.html')

@app.route('/api/record-sale', methods=['POST'])
def record_sale():
    """Record a sale transaction"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['barcode', 'quantity', 'amount', 'product_id']
        if not all(k in data for k in required):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        barcode = data['barcode']
        quantity = int(data['quantity'])
        amount = float(data['amount'])
        product_id = data['product_id']
        
        # Check if product exists and has enough stock
        product = db.get_product_by_id(product_id)
        
        if not product:
            return jsonify({'status': 'error', 'message': 'Product not found'}), 404
        
        if product['stock_quantity'] < quantity:
            return jsonify({'status': 'error', 'message': 'Insufficient stock'}), 400
        
        # Record the transaction
        transaction_id = db.record_transaction(
            product_id=product_id,
            quantity=quantity,
            amount=amount,
            transaction_type='sale',
            barcode=barcode
        )
        
        # Update stock
        new_stock = product['stock_quantity'] - quantity
        db.update_product_stock(product_id, new_stock)
        
        print(f"✅ Sale recorded: {product['name']} - {quantity} units - ${amount:.2f}")
        
        return jsonify({
            'status': 'success',
            'transaction_id': transaction_id,
            'message': 'Sale recorded successfully'
        })
    except Exception as e:
        print(f"❌ Error recording sale: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sales-stats')
def get_sales_stats():
    """Get today's sales statistics"""
    try:
        stats = db.get_sales_stats()
        
        return jsonify({
            'status': 'success',
            'total_transactions': stats['total_transactions'],
            'total_revenue': stats['total_revenue'],
            'total_units': stats['total_units']
        })
    except Exception as e:
        print(f"❌ Error fetching sales stats: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sales-report/download')
def download_sales_report():
    """Download sales report as Excel file"""
    try:
        # Get all sales from today
        sales_data = db.get_today_sales()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Sales Report"
        
        # Define styles
        header_fill = PatternFill(start_color="00C49A", end_color="00C49A", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        summary_fill = PatternFill(start_color="E8ECF1", end_color="E8ECF1", fill_type="solid")
        summary_font = Font(bold=True, size=11)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Set column widths
        columns = {
            'A': 15,
            'B': 25,
            'C': 15,
            'D': 12,
            'E': 15,
            'F': 15
        }
        for col, width in columns.items():
            ws.column_dimensions[col].width = width
        
        # Add title
        ws.merge_cells('A1:F1')
        title = ws['A1']
        title.value = f"Daily Sales Report - {datetime.now().strftime('%B %d, %Y')}"
        title.font = Font(bold=True, size=14, color="FFFFFF")
        title.fill = PatternFill(start_color="3A9BDC", end_color="3A9BDC", fill_type="solid")
        title.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 25
        
        # Add headers
        headers = ["Time", "Product Name", "Barcode", "Quantity (Strips)", "Unit Price", "Total Amount"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_idx)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        ws.row_dimensions[3].height = 20
        
        # Add data rows
        total_revenue = 0.0
        total_units = 0
        
        for idx, sale in enumerate(sales_data, 4):
            ws.cell(row=idx, column=1).value = sale['time']
            ws.cell(row=idx, column=2).value = sale['product_name']
            ws.cell(row=idx, column=3).value = sale['barcode']
            ws.cell(row=idx, column=4).value = sale['quantity']
            ws.cell(row=idx, column=5).value = sale['unit_price']
            ws.cell(row=idx, column=6).value = sale['amount']
            
            # Apply borders and formatting
            for col in range(1, 7):
                cell = ws.cell(row=idx, column=col)
                cell.border = border
                if col in [4, 5, 6]:
                    cell.alignment = Alignment(horizontal="right")
            
            # Format currency columns
            ws.cell(row=idx, column=5).number_format = '$#,##0.00'
            ws.cell(row=idx, column=6).number_format = '$#,##0.00'
            
            total_revenue += sale['amount']
            total_units += sale['quantity']
        
        # Add summary section
        summary_row = len(sales_data) + 5
        
        # Summary title
        ws.merge_cells(f'A{summary_row}:F{summary_row}')
        summary_title = ws[f'A{summary_row}']
        summary_title.value = "SUMMARY"
        summary_title.font = Font(bold=True, size=12, color="FFFFFF")
        summary_title.fill = PatternFill(start_color="3A9BDC", end_color="3A9BDC", fill_type="solid")
        summary_title.alignment = Alignment(horizontal="center")
        
        # Summary details
        summary_row += 1
        summary_items = [
            ("Total Transactions", len(sales_data)),
            ("Total Units Sold", total_units),
            ("Total Revenue", f"${total_revenue:.2f}")
        ]
        
        col_idx = 1
        for label, value in summary_items:
            # Label
            label_cell = ws.cell(row=summary_row, column=col_idx)
            label_cell.value = label
            label_cell.font = summary_font
            label_cell.fill = summary_fill
            label_cell.border = border
            
            # Value
            value_cell = ws.cell(row=summary_row, column=col_idx + 1)
            value_cell.value = value
            value_cell.font = Font(bold=True, size=11)
            value_cell.fill = summary_fill
            value_cell.border = border
            value_cell.alignment = Alignment(horizontal="right")
            
            col_idx += 2
        
        # Generate file
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Sales_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# Additional route for getting product by ID (needed for sales counter)
# ============================================================================

@app.route('/api/product/<int:product_id>')
def get_product(product_id):
    """Get product details by ID"""
    try:
        product = db.get_product_by_id(product_id)
        
        if product:
            return jsonify({
                'status': 'success',
                'data': product
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Product not found'
            }), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# 💡 INSIGHTS & ANALYTICS ROUTES
# ============================================================================

@app.route('/insights')
def insights_page():
    """Insights page template"""
    return render_template('insights.html')

@app.route('/api/insights')
def get_insights():
    """Get AI-driven insights and predictions"""
    try:
        products = db.get_all_products()
        
        # Expiry insights
        expiry_data = ai_predictor.predict_expiring_medicines(days=7)
        
        # Demand insights
        demand_data = ai_predictor.predict_high_demand_products()
        
        # Waste prevention
        total_waste_prevented = len(products) * 0.15  # kg per product
        
        # Packaging insights
        packaging_breakdown = ai_predictor.get_eco_score_analysis()
        
        return jsonify({
            'status': 'success',
            'expiry_insights': expiry_data[:6],
            'demand_insights': demand_data[:6],
            'waste_prevented_kg': round(total_waste_prevented, 2),
            'avg_eco_score': round(sum(p['eco_score'] for p in products) / len(products), 2) if products else 0,
            'packaging_analysis': packaging_breakdown
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# 🤖 CHATBOT ROUTES
# ============================================================================

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI Chatbot endpoint for pharmacy queries"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip().lower()
        
        if not user_message:
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400
        
        # Get chatbot response
        response = chatbot.get_response(user_message)
        
        return jsonify({
            'status': 'success',
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# STATIC & TEMPLATE FILES
# ============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize database
    db.create_tables()
    
    # Add sample data if empty
    db.add_sample_data()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)