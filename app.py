from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import uuid
from datetime import datetime, timedelta
import os
from supabase import create_client, Client
import random
import requests

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here'

WORLDPAY_USERNAME = os.getenv('WORLDPAY_USERNAME')
WORLDPAY_PASSWORD = os.getenv('WORLDPAY_PASSWORD')
# Supabase configuration
SUPABASE_URL = "https://tddovxrnfnrdvrludfwb.supabase.co"
SUPABASE_KEY ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRkZG92eHJuZm5yZHZybHVkZndiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQyOTUwMTgsImV4cCI6MjA2OTg3MTAxOH0.iTug0w1UXP9gRWIyhhYQrudt-UAASXAvWtvXfhe_oqI"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Country data
COUNTRIES = [
    {"name": "United States", "code": "US"},
    {"name": "Canada", "code": "CA"},
    {"name": "United Kingdom", "code": "GB"},
    {"name": "Germany", "code": "DE"},
    {"name": "France", "code": "FR"},
    {"name": "Japan", "code": "JP"},
    {"name": "Australia", "code": "AU"},
    {"name": "India", "code": "IN"},
    {"name": "China", "code": "CN"},
    {"name": "Singapore", "code": "SG"},
    {"name": "Malaysia", "code": "MY"},
    {"name": "Brazil", "code": "BR"},
    {"name": "South Africa", "code": "ZA"},
    {"name": "Mexico", "code": "MX"},
    {"name": "Italy", "code": "IT"},
    {"name": "Spain", "code": "ES"}
]

# Sample invoice descriptions
INVOICE_DESCRIPTIONS = [
    "Web Development Services",
    "Consulting Fees",
    "Software License",
    "Cloud Hosting",
    "Technical Support",
    "UI/UX Design",
    "API Integration",
    "Data Analysis"
]

@app.route('/')
def index():
    return render_template('index.html', countries=COUNTRIES)

@app.route('/bills')
def bills():
    # Get the latest invoice (the one just created)
    latest_invoice = supabase.table('invoices').select('*').order('created_at', desc=True).limit(1).execute().data[0]
    
    # Generate 3 random invoices (not saved to database)
    random_invoices = generate_random_invoices(3)
    
    return render_template('bills.html', 
                         latest_invoice=latest_invoice,
                         random_invoices=random_invoices)

def generate_random_invoices(count):
    descriptions = [
        "Web Development Services",
        "Consulting Fees",
        "Software License",
        "Cloud Hosting",
        "Technical Support",
        "UI/UX Design",
        "API Integration",
        "Data Analysis",
        "Server Maintenance",
        "Database Administration"
    ]
    
    vendors = ["VEN-US", "VEN-CA", "VEN-UK", "VEN-DE", "VEN-FR"]
    
    invoices = []
    for _ in range(count):
        # Generate random date within last 30 days
        random_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        
        invoices.append({
            "invoice_id": f"INV-{random_date.replace('-', '')}-{random.randint(1000, 9999)}",
            "date": random_date,
            "description": random.choice(descriptions),
            "amount": round(random.uniform(50, 2000), 2),
            "vendor_id": random.choice(vendors)
        })
    
    return invoices

@app.route('/generate_vendor_id', methods=['POST'])
def generate_vendor_id():
    country_code = request.json.get('country_code')
    vendor_id = f"VEN-{country_code}-{str(uuid.uuid4())[:8].upper()}"
    return jsonify({"vendor_id": vendor_id})

@app.route('/generate_invoice_details', methods=['POST'])
def generate_invoice_details():
    invoice_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    date = datetime.now().strftime('%Y-%m-%d')
    description = random.choice(INVOICE_DESCRIPTIONS)
    amount = round(random.uniform(100, 5000), 2)
    
    return jsonify({
        "invoice_id": invoice_id,
        "date": date,
        "description": description,
        "amount": amount
    })

@app.route('/save_invoice', methods=['POST'])
def save_invoice():
    data = request.json
    
    session['country'] = data['country']
    # Save vendor data
    vendor_data = {
        "vendor_id": data['vendor_id'],
        "country": data['country'],
        "created_at": datetime.now().isoformat()
    }
    supabase.table('vendors').insert(vendor_data).execute()
    
    # Save invoice data
    invoice_data = {
        "invoice_id": data['invoice_id'],
        "date": data['date'],
        "description": data['description'],
        "amount": data['amount'],
        "vendor_id": data['vendor_id'],
        "created_at": datetime.now().isoformat()
    }
    supabase.table('invoices').insert(invoice_data).execute()
    
    return jsonify({"status": "success", "redirect": url_for('bills')})

@app.route('/process_payment', methods=['POST'])
def process_payment():
    try:
        # Get data from request and update session
        data = request.json
        session.update({
            'selected_invoices': data['invoices'],
            'total_amount': data['totalAmount']
        })

        country = session.get('country', '')
        
        # Define country-specific templates and settings
        COUNTRY_SETTINGS = {
            'China': {
                'template': 'china.html',
                'currency': 'CNY',
                'exchange_rate': 7.18,
                
            },
            'IN': {
                'template': 'india.html',
                'currency': 'INR',
                'exchange_rate': 83.5,
                
            },
            'US': {
                'template': 'default_payment.html',
                'currency': 'USD',
                'exchange_rate': 1,
                
            }
            # Add more countries as needed
        }
        
        # Get country settings or use defaults
        settings = COUNTRY_SETTINGS.get(country, {
            'template': 'default_payment.html',
            'currency': 'USD',
            'exchange_rate': 1,
            'payment_methods': ['credit_card']
        })
        
        # Calculate converted amount
        converted_amount = session['total_amount'] * settings['exchange_rate']
        
        # Render the appropriate template directly
        return render_template(
            settings['template'],
            country=session.get('country_name', ''),
            country_code=country,
            total_usd=session['total_amount'],
            total_local=round(converted_amount, 2),
            currency=settings['currency'],
            exchange_rate=settings['exchange_rate'],
            exchange_date=datetime.now().strftime('%Y-%m-%d')
        )
        
    except Exception as e:
        app.logger.error(f"Payment processing error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Payment processing failed'
        }), 500

@app.route('/process_card', methods=['POST'])
def process_card():
    """Process card payments with country-specific configurations"""
    try:
        # 1. Get country from session and validate
        country = session.get('country')  
        if country not in ['China']:
            return jsonify({
                'status': 'error',
                'message': f'Unsupported country: {country}'
            }), 400

        # 2. Get card data from frontend
        card_data = request.get_json()
        if not all(key in card_data for key in ['cardNumber', 'expiryMonth', 
                                              'expiryYear', 'cvc', 'cardHolderName']):
            return jsonify({
                'status': 'error',
                'message': 'Missing required card fields'
            }), 400

        # 3. Country-specific configuration
        COUNTRY_CONFIG = {
            'China': {
                'currency': 'CNY',
                'exchange_rate': 7.18,
                'billing_address': {
                    'address1': '123 Beijing Road',
                    'address2': '456 beijing street',
                    'address3': '789 Beijing Lane',
                    'city': 'Shanghai',
                    'postalCode': '200000',
                    'countryCode': 'CN'
                }
            },
        }

        config = COUNTRY_CONFIG[country]
        
        # 4. Calculate amount in local currency
        usd_amount = float(session.get('total_amount', 0))
        local_amount = int(usd_amount * config['exchange_rate'] * 100)  # in cents

        # 5. Build payload with country-specific details
        payload = {
            "transactionReference": f"CARD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {"entity": "default"},
            "instruction": {
                "method": "card",
                "paymentInstrument": {
                    "type": "plain",
                    "cardHolderName": card_data['cardHolderName'],
                    "cardNumber": card_data['cardNumber'].replace(" ", ""),
                    "expiryDate": {
                        "month": int(card_data['expiryMonth']),
                        "year": int(card_data['expiryYear']) if len(card_data['expiryYear']) == 4 
                               else int(f"20{card_data['expiryYear']}")
                    },
                    "billingAddress": {
                        **config['billing_address'],
                    },
                    "cvc": card_data['cvc']
                },
                "narrative": {"line1": "Bill Payment"},
                "value": {
                    "currency": config['currency'],
                    "amount": local_amount
                }
            }
        }

        # 6. Make API call to Worldpay
        headers = {
            "Content-Type": "application/json",
            "WP-Api-Version": "2024-06-01"
        }

        response = requests.post(
            "https://try.access.worldpay.com/api/payments",
            json=payload,
            headers=headers,
            auth=(WORLDPAY_USERNAME, WORLDPAY_PASSWORD),
            timeout=30
        )
        # 7. Handle response
        if response.status_code == 201:
            data = response.json()
            payment_url = data["_links"]["self"]["href"]
            payment_id = payment_url.split("/payments/")[1].split("/")[0]
            session.update({
                'payment_id': payment_id,
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local_amount / 100,
                'paid_currency': config['currency'],
                'payment_method': 'card',
                'card_last4': payload['instruction']['paymentInstrument']['cardNumber'][-4:]
            })
            
            return jsonify({
                'status': 'success',
                'message': 'Payment processed',
                'receipt_url': url_for('payment_success', _external=True),
                'transaction_id': payload['transactionReference']
            })

        return jsonify({
            'status': 'error',
            'message': 'Payment failed',
            'response': response.json(),
            'status_code': response.status_code
        }), 400

    except Exception as e:
        app.logger.error(f'Card processing error: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
    
@app.route('/process_alipay', methods=['POST'])
def process_alipay():
    """Dedicated Alipay processor with country flexibility"""
    try:
        # 1. Get country from session (set during invoice creation)
        country = session.get('country', 'CN') # Default to China
        
        # 2. Country validation and config
        COUNTRY_SETTINGS = {
            'China': {'currency': 'CNY','language': 'zh'},
        }
        
        if country not in COUNTRY_SETTINGS:
            return jsonify({
                'status': 'error',
                'message': f'Alipay not supported in {country}',
                'supported_countries': list(COUNTRY_SETTINGS.keys())
            }), 400

        config = COUNTRY_SETTINGS[country]
        
        # Calculate total_local using session's total_amount and a default exchange rate (set to 1 if not present)
        total_amount = session.get('total_amount', 0)
        # You may want to define exchange rates for each country; here we use 1 as a fallback
        exchange_rates = {'China': 7.18}
        exchange_rate = exchange_rates.get(country, 1)
        total_local = float(total_amount) * exchange_rate

        # 3. Build fixed Alipay payload (structure never changes)
        payload = {
            "transactionReference": f"ALP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",
            },
            "instruction": {
                "method": "alipay_cn",
                "value": {
                    "amount": int(float(total_local) * 100),  # cents
                    "currency": config['currency']
                },
                "narrative": {
                    "line1": "MindPalace Service"
                },
                "paymentInstrument": {
                    "type": "direct",
                    "language": config['language']
                },
                "resultUrls": {
                    "pending": url_for('bills', _external=True),
                    "failure": url_for('bills', _external=True),
                    "success": url_for('payment_success', _external=True),
                    "cancel": url_for('bills', _external=True)
                },
                "deviceData": {
                    "device": "desktop",
                    "operatingSystem": "windows"
               },
                "customer": {
                    "firstName": "Xhiao",
                    "lastName": "Xubeg",
                    "email": "xhiao@example.com"
                }
            }
        }
        headers = {
            "Content-Type": "application/json",
            "WP-Api-Version": "2024-07-01"
        }
        # 4. Call Alipay API
        response = requests.post(
            "https://try.access.worldpay.com/apmPayments",
            json=payload,
            headers=headers,
            auth=(WORLDPAY_USERNAME, WORLDPAY_PASSWORD),
            timeout=30
        )
        # 5. Handle response
        if response.status_code == 201:
            data = response.json()
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': payload['instruction']['value']['amount'] / 100,
                'paid_currency': config['currency']
            })
            return jsonify({
                'status': 'success',
                'redirect_url': data.get('redirect')
            })

        return jsonify({
            'status': 'error',
            'message': 'Alipay API error',
            'response': response.text
        }), 400

    except Exception:
        return jsonify({'status': 'error', 'message': 'Processing failed'}), 500

@app.route('/process_wechatpay', methods=['POST'])
def process_wechatpay():
    """Process card payments with country-specific configurations"""
    try:
        # 1. Get country from session and validate
        country = session.get('country')  
        if country not in ['China']:
            return jsonify({
                'status': 'error',
                'message': f'Unsupported country: {country}'
            }), 400

        # 3. Country-specific configuration
        COUNTRY_CONFIG = {
            'China': {
                'currency': 'CNY',
                'exchange_rate': 7.18,
            },
        }

        config = COUNTRY_CONFIG[country]
        
        # 4. Calculate amount in local currency
        usd_amount = float(session.get('total_amount', 0))
        local_amount = int(usd_amount * config['exchange_rate'] * 100)  # in cents

        # 5. Build payload with country-specific details
        payload = {
            "transactionReference": f"WECHAT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",  
            },
            "instruction": {
                "method": "wechatpay",  
                "expiryIn": 15,  
                "value": {
                    "amount": local_amount,
                    "currency": config['currency']  
                },
                "narrative": {
                    "line1": "APG Payment"  
                },
                "paymentInstrument": {
                    "type": "direct" 
                },
            }
        }

        # 6. Make API call to Worldpay
        headers = {
            "Content-Type": "application/json",
            "WP-Api-Version": "2024-07-01"
        }

        response = requests.post(
            "https://try.access.worldpay.com/apmPayments",
            json=payload,
            headers=headers,
            auth=(WORLDPAY_USERNAME, WORLDPAY_PASSWORD),
            timeout=30
        )
        # 7. Handle response
        if response.status_code == 201:
            data = response.json()
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local_amount / 100,
                'paid_currency': config['currency'],
                'payment_method': 'card',
                
            })
            
            return jsonify({
                'status': 'success',
                'qrcode': data.get('redirect'),
                'message': 'Payment processed',
                'receipt_url': url_for('payment_success', _external=True),
                'transaction_id': payload['transactionReference']
            })

        return jsonify({
            'status': 'error',
            'message': 'Payment failed',
            'response': response.json(),
            'status_code': response.status_code
        }), 400

    except Exception as e:
        app.logger.error(f'Card processing error: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
    
@app.route('/success')
def payment_success():
    """Unified success page for all payment methods"""
    return render_template('success.html',
        payment_id=session.get('payment_id'),
        transaction_ref=session.get('transaction_ref'),
        amount_usd=session.get('total_amount'),
        amount_paid=session.get('paid_amount'),
        currency=session.get('paid_currency'),
        method=session.get('payment_method'),
        date=datetime.now().strftime('%Y-%m-%d %H:%M')
    )

if __name__ == '__main__':
    app.run(debug=True)