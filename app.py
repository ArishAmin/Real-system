from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import uuid
from datetime import datetime, timedelta
import os
from supabase import create_client, Client
import random
import requests


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "argos_models")
os.environ['ARGOS_TRANSLATE_PACKAGES_DIR'] = MODELS_DIR

from argostranslate.translate import get_installed_languages
from argostranslate import translate

WORLDPAY_USERNAME = os.getenv('WORLDPAY_USERNAME')
WORLDPAY_PASSWORD = os.getenv('WORLDPAY_PASSWORD')
# Supabase configuration
SUPABASE_URL = "https://tddovxrnfnrdvrludfwb.supabase.co"
SUPABASE_KEY ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRkZG92eHJuZm5yZHZybHVkZndiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQyOTUwMTgsImV4cCI6MjA2OTg3MTAxOH0.iTug0w1UXP9gRWIyhhYQrudt-UAASXAvWtvXfhe_oqI"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Country data
COUNTRIES = [
    {"name": "China", "code": "CN"},
    {"name": "United States", "code": "US"},
    {"name": "Germany", "code": "DE"},
    {"name": "France", "code": "FR"},
    {"name": "Japan", "code": "JP"},
    {"name": "United Kingdom", "code": "UK"},
    {"name": "India", "code": "IN"},
    {"name": "Malaysia","code": "MY"},
    {"name": "Belgium", "code": "BE"},
    {"name": "Italy", "code": "IT"},
    
]
# Language mapping for each country
LANGUAGE_MAP = {
    "China": "zh",
    "United States": "en",
    "Germany": "de",
    "France": "fr",
    "Japan": "ja",
    "United Kingdom": "en",
    "India": "hi",
    "Malaysia": "ms",
    "Belgium": "nl",
    "Italy": "it"
}

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

EUROPEAN_COUNTRIES = {"Germany", "France", "Italy", "Belgium"}

def format_amount(amount, country):
    
    if country in EUROPEAN_COUNTRIES:
        # European style: comma for decimal, dot for thousands
        return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        # US/international style
        return f"{amount:,.2f}"

@app.context_processor
def inject_translation():
    country = session.get('country', 'United States')  
    lang_code = LANGUAGE_MAP.get(country, 'en')  
    return dict(
        translate=lambda text: translate_text(text, lang_code),
        lang_code=lang_code
    )

@app.route('/')
def index():
    return render_template('index.html', countries=COUNTRIES)

# Translator cache to avoid reloading on each request
TRANSLATORS = {}

def get_translator(from_code, to_code):
    key = (from_code, to_code)
    if key not in TRANSLATORS:
        langs = translate.get_installed_languages()
        from_lang = next((l for l in langs if l.code == from_code), None)
        to_lang = next((l for l in langs if l.code == to_code), None)
        if from_lang and to_lang:
            translator = from_lang.get_translation(to_lang)
            if translator:  # Only store if a model exists
                TRANSLATORS[key] = translator
    return TRANSLATORS.get(key)

def translate_text(text, target_lang):
    translator = get_translator("en", target_lang)
    if translator:
        return translator.translate(text)
    return text

@app.route('/bills')
def bills():
    lang_code = LANGUAGE_MAP.get(session.get('country'))
    # Get the latest invoice (the one just created)
    latest_invoice = supabase.table('invoices').select('*').order('created_at', desc=True).limit(1).execute().data[0]
    latest_invoice['description'] = translate_text(latest_invoice['description'], lang_code)
    latest_invoice['vendor_id']= translate_text(latest_invoice['vendor_id'], lang_code)
    

    random_invoices = generate_random_invoices(3)
        
    return render_template('bills.html', 
                         latest_invoice=latest_invoice,
                         random_invoices=random_invoices,
                         lang_code=lang_code,)

def generate_random_invoices(count):
    lang_code = LANGUAGE_MAP.get(session.get('country'))

    descriptions = [
        translate_text("Web Development Services", lang_code),
        translate_text("Consulting Fees", lang_code),
        translate_text("Software License", lang_code),
        translate_text("Cloud Hosting", lang_code),
        translate_text("Technical Support", lang_code),
        translate_text("UI/UX Design", lang_code),
        translate_text("API Integration", lang_code),
        translate_text("Data Analysis", lang_code),
        translate_text("Server Maintenance", lang_code),
        translate_text("Database Administration", lang_code),
    ]
    if lang_code == 'de':
        if "Web Development Services" in descriptions:
            descriptions[descriptions.index("Web Development Services")] = "Webentwicklung Dienstleistungen"
        if "Consulting Fees" in descriptions:
            descriptions[descriptions.index("Consulting Fees")] = "Beratungsgebühren"
        

    invoices = []
    for _ in range(count):
        # Generate random date within last 30 days
        random_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        
        invoices.append({
            "invoice_id": f"INV-{random_date.replace('-', '')}-{random.randint(1000, 9999)}",
            "date": random_date,
            "description": random.choice(descriptions),
            "amount": round(random.uniform(50, 2000), 2),
            
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

        country = session.get('country')

        # Define country-specific templates and settings
        COUNTRY_SETTINGS = {
            'China': {'template': 'china.html', 'exchange_rate': 7.18},
            'India': {'template': 'india.html', 'exchange_rate': 83.5},
            'United States': {'template': 'united_states.html', 'exchange_rate': 1},
            'Malaysia': {'template': 'malaysia.html', 'exchange_rate': 4.5},
            'Germany': {'template': 'germany.html', 'exchange_rate': 0.85},
            'France': {'template': 'france.html', 'exchange_rate': 0.85},
            'Italy': {'template': 'italy.html', 'exchange_rate': 0.85},
            'Belgium': {'template': 'belgium.html', 'exchange_rate': 0.85},
            'United Kingdom': {'template': 'united_kingdom.html', 'exchange_rate': 0.75},
            'Japan': {'template': 'japan.html', 'exchange_rate': 110.0}
        }

        # Get country settings or use defaults
        settings = COUNTRY_SETTINGS.get(country)

        total_local = session['total_amount'] * settings['exchange_rate'] if settings else session['total_amount']
        total = total_local * 1.06
        formatted_total_local = format_amount(total, country)
        lang_code = LANGUAGE_MAP.get(country)

        return render_template(
            settings['template'],
            country=session.get('country_name', ''),
            country_code=country,
            exchange_rate=settings['exchange_rate'],
            local=formatted_total_local,
            local_numeric=total,
            date=datetime.now().strftime('%Y-%m-%d'),
            total_usd=session['total_amount'],
            lang_code=lang_code,
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
        if country not in ['China','United States', 'India','Malaysia','Germany','France','Italy','Belgium','United Kingdom','Japan']:
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
            'United States': {
                'currency': 'USD',
                'exchange_rate': 1,
                'billing_address': {
                    'address1': '123 Main St',
                    'address2': '456 Elm St',
                    'address3': '789 Oak St',
                    'city': 'New York',
                    'postalCode': '10001',
                    'countryCode': 'US'
                }
            },
            'India': {
                'currency': 'INR',
                'exchange_rate': 83.5,
                'billing_address': {
                    'address1': '123 MG Road',
                    'address2': '456 Brigade Road',
                    'address3': '789 Church Street',
                    'city': 'Bangalore',
                    'postalCode': '560001',
                    'countryCode': 'IN'
                }
            },
            'Malaysia': {
                'currency': 'MYR',
                'exchange_rate': 4.5,
                'billing_address': {
                    'address1': '123 Jalan Bukit Bintang',
                    'address2': '456 Jalan Sultan Ismail',
                    'address3': '789 Jalan Pudu',
                    'city': 'Kuala Lumpur',
                    'postalCode': '55100',
                    'countryCode': 'MY'
                }
            },
            'Germany': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Berlin Strasse',
                    'address2': '456 Berlin Platz',
                    'address3': '789 Berlin Weg',
                    'city': 'Berlin',
                    'postalCode': '10115',
                    'countryCode': 'DE'
                }
            },
            'France': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Rue de Paris',
                    'address2': '456 Avenue de France',
                    'address3': '789 Boulevard de Paris',
                    'city': 'Paris',
                    'postalCode': '75001',
                    'countryCode': 'FR'
                }
            },
            'Italy': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Via Roma',
                    'address2': '456 Piazza Italia',
                    'address3': '789 Corso Italia',
                    'city': 'Rome',
                    'postalCode': '00100',
                    'countryCode': 'IT'
                }
            },
            'Belgium': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Rue de Bruxelles',
                    'address2': '456 Avenue de Belgique',
                    'address3': '789 Boulevard de Bruxelles',
                    'city': 'Brussels',
                    'postalCode': '1000',
                    'countryCode': 'BE'
                }
            },
            'United Kingdom': {
                'currency': 'GBP',
                'exchange_rate': 0.75,
                'billing_address': {
                    'address1': '123 London Road',
                    'address2': '456 London Street',
                    'address3': '789 London Lane',
                    'city': 'London',
                    'postalCode': 'EC1A 1BB',
                    'countryCode': 'GB'
                }
            },
            'Japan': {
                'currency': 'JPY',
                'exchange_rate': 147.82,
                'billing_address': {
                    'address1': '123 Tokyo Street',
                    'address2': '456 Tokyo Avenue',
                    'address3': '789 Tokyo Lane',
                    'city': 'Tokyo',
                    'postalCode': '100-0001',
                    'countryCode': 'JP'
                }
            }
        }

        config = COUNTRY_CONFIG[country]
        
        # 4. Calculate amount in local currency
        usd_amount = float(session.get('total_amount', 0))
        if country == 'Japan':
            local_amount=int(usd_amount * config['exchange_rate'])
        else:
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
                "narrative": {"line1": "APG Payment"},
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
            local=format_amount(local_amount / 100, country)
            payment_url = data["_links"]["self"]["href"]
            payment_id = payment_url.split("/payments/")[1].split("/")[0]
            session.update({
                'payment_id': payment_id,
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
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
    try:
        
        country = session.get('country') 
        
        # 2. Country validation and config
        COUNTRY_SETTINGS = {
            'China': {
                'currency': 'CNY',
                'language': 'zh',
                'exchange_rate': 7.18,
                'customer': {
                    'firstName': 'Xhiao',
                    'lastName': 'Xubeg',
                    'email': 'xhiao@example.com'
                },
            },
            'United States': {
                'currency': 'USD',
                'language': 'en',
                'exchange_rate': 1,
                'customer': {
                    'firstName': 'John',
                    'lastName': 'Doe',
                    'email': 'john@example.com'
                },
            },
            'Germany': {
                'currency': 'EUR',
                'language': 'de',
                'exchange_rate': 0.85,
                'customer': {
                    'firstName': 'Hans',
                    'lastName': 'Müller',
                    'email': 'hans@example.com'
                },
            },
            'France': {
                'currency': 'EUR',
                'language': 'fr',
                'exchange_rate': 0.85,
                'customer': {
                    'firstName': 'Jean',
                    'lastName': 'Dupont',
                    'email': 'jean@example.com'
                }
            },
            'Italy': {
                'currency': 'EUR',
                'language': 'it',
                'exchange_rate': 0.85,
                'customer': {
                    'firstName': 'Mario',
                    'lastName': 'Rossi',
                    'email': 'mario@example.com'
                }
            },
            'Belgium': {
                'currency': 'EUR',
                'language': 'nl',
                'exchange_rate': 0.85,
                'customer': {
                    'firstName': 'Jan',
                    'lastName': 'Peeters',
                    'email': 'jan@example.com'
                }
            },
            'United Kingdom': {
                'currency': 'GBP',
                'language': 'en',
                'exchange_rate': 0.75,
                'customer': {
                    'firstName': 'John',
                    'lastName': 'Doe',
                    'email': 'john@example.com'
                }
            },
            'Japan': {
                'currency': 'JPY',
                'language': 'ja',
                'exchange_rate': 147.82,
                'customer': {
                    'firstName': 'Taro',
                    'lastName': 'Yamamoto',
                    'email': 'taro@example.com'
                }
            },    
        }
        
        if country not in COUNTRY_SETTINGS:
            return jsonify({
                'status': 'error',
                'message': f'Alipay not supported in {country}',
                'supported_countries': list(COUNTRY_SETTINGS.keys())
            }), 400

        config = COUNTRY_SETTINGS[country]
        
        usd_amount = session.get('total_amount', 0)
        if country == 'Japan':
            local_amount=int(usd_amount * config['exchange_rate'])
        else:
            local_amount = int(usd_amount * config['exchange_rate'] * 100)  # in cents 

        # 3. Build fixed Alipay payload (structure never changes)
        payload = {
            "transactionReference": f"ALP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",
            },
            "instruction": {
                "method": "alipay_cn",
                "value": {
                    "amount": local_amount,  
                    "currency": config['currency']
                },
                "narrative": {
                    "line1": "APG Service"
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
                    **config['customer'],
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
            local=format_amount(local_amount / 100, country)
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
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
    
    try:
        # 1. Get country from session and validate
        country = session.get('country')  
        if country not in ['China','United States','Germany','France','Italy','Belgium','United Kingdom','Japan']:
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
            'United States': {
                'currency': 'USD',
                'exchange_rate': 1,
            },
            'Germany': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
            },
            'France': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
            },
            'Italy': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
            },
            'Belgium': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
            },
            'United Kingdom': {
                'currency': 'GBP',
                'exchange_rate': 0.75,
            },
            'Japan': {
                'currency': 'JPY',
                'exchange_rate': 147.82,
            },
        }

        config = COUNTRY_CONFIG[country]
        
        # 4. Calculate amount in local currency
        usd_amount = float(session.get('total_amount', 0))
        if country == 'Japan':
            local_amount=int(usd_amount * config['exchange_rate'])
        else:
            local_amount = int(usd_amount * config['exchange_rate'] * 100)    # in cents

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
            local=format_amount(local_amount / 100, country)
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
                'paid_currency': config['currency'],
                'payment_method': 'wechatpay',
                
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

@app.route('/process_paypal', methods=['POST'])
def process_paypal():
    try:
        
        country = session.get('country') 
        
        COUNTRY_CONFIG = {
            'United States': {
                'currency': 'USD',
                'exchange_rate': 1,
                'billing_address': {
                    'address1': '123 Main St',
                    'address2': '456 Elm St',
                    'address3': '789 Oak St',
                    'postalCode': '10001',
                    'city': 'New York',
                    'state': 'NY',
                    'countryCode': 'US'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "NY",
                        "countryCode": "US"
                    }
                },
                "customer": {
                    "email":"hannamontana@gmail.com" 
                },
            },
            'India': {
                'currency': 'INR',
                'exchange_rate': 83.5,
                'billing_address': {
                    'address1': '123 MG Road',
                    'address2': '456 Brigade Road',
                    'address3': '789 Church Street',
                    'postalCode': '560001',
                    'city': 'Bangalore',
                    'state': 'KA',
                    'countryCode': 'IN'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "KA",
                        "countryCode": "IN"
                    }
                },
                "customer": {
                    "email":"asdasd@gmail.com"
                }
            },
            'Malaysia': {
                'currency': 'MYR',
                'exchange_rate': 4.5,
                'billing_address': {
                    'address1': '123 Jalan Bukit Bintang',
                    'address2': '456 Jalan Sultan Ismail',
                    'address3': '789 Jalan Pudu',
                    'postalCode': '55100',
                    'city': 'Kuala Lumpur',
                    'state': 'WP',
                    'countryCode': 'MY'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "WP",
                        "countryCode": "MY"
                    }
                },
                "customer": {
                    "email":"asdasd@gmail.com"
                }
            },
            'Germany': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Berlin Strasse',
                    'address2': '456 Berlin Platz',
                    'address3': '789 Berlin Weg',
                    'postalCode': '10115',
                    'city': 'Berlin',
                    'state': 'BE',
                    'countryCode': 'DE'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "DE",
                        "countryCode": "DE"
                    }
                },
                "customer": {
                    "email":"james@example.com"
                }
            },
            'France': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Rue de Paris',
                    'address2': '456 Avenue de France',
                    'address3': '789 Boulevard de Paris',
                    'postalCode': '75001',
                    'city': 'Paris',
                    'state': 'IDF',
                    'countryCode': 'FR'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "IDF",
                        "countryCode": "FR"
                    }
                },
                "customer": {
                    "email":"james@example.com"
                }
            },
            'Italy': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Via Roma',
                    'address2': '456 Piazza Italia',
                    'address3': '789 Corso Italia',
                    'postalCode': '00100',
                    'city': 'Rome',
                    'state': 'RM',
                    'countryCode': 'IT'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "RM",
                        "countryCode": "IT"
                    }
                },
                "customer": {
                    "email":"james@example.com"
                }
            },
            'Belgium': {
                'currency': 'EUR',
                'exchange_rate': 0.85,
                'billing_address': {
                    'address1': '123 Rue de Bruxelles',
                    'address2': '456 Avenue de Belgique',
                    'address3': '789 Boulevard de Bruxelles',
                    'postalCode': '1000',
                    'city': 'Brussels',
                    'state': 'BRU',
                    'countryCode': 'BE'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "BRU",
                        "countryCode": "BE"
                    }
                },
                "customer": {
                    "email":"jaems@example.com"
                }
            },
            'United Kingdom': {
                'currency': 'GBP',
                'exchange_rate': 0.75,
                'billing_address': {
                    'address1': '123 London Road',
                    'address2': '456 London Street',
                    'address3': '789 London Lane',
                    'postalCode': 'EC1A 1BB',
                    'city': 'London',
                    'state': 'ENG',
                    'countryCode': 'GB'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "ENG",
                        "countryCode": "GB"
                    }
                },
                "customer": {
                    "email":"jemes@example.com"
                }
            },
            'Japan': {
                'currency': 'JPY',
                'exchange_rate': 147.82,
                'billing_address': {
                    'address1': '123 Tokyo Street',
                    'address2': '456 Tokyo Avenue',
                    'address3': '789 Tokyo Lane',
                    'postalCode': '100-0001',
                    'city': 'Tokyo',
                    'state': '13',
                    'countryCode': 'JP'
                },
                "shipping": {
                    "firstName": "James",
                    "lastName": "Moriarty",
                    "address": {
                        "address1": "The Palatine Centre",
                        "postalCode": "DH1 3LE",
                        "city": "Durham",
                        "state": "13",
                        "countryCode": "JP"
                    }
                },
                "customer": {
                    "email":"james@example.com"
                }
            }            
        }
        
        if country not in COUNTRY_CONFIG:
            return jsonify({
                'status': 'error',
                'message': f'Paypal not supported in {country}',
                'supported_countries': list(COUNTRY_CONFIG.keys())
            }), 400

        config = COUNTRY_CONFIG[country]
        
        
        usd_amount = session.get('total_amount', 0)
        if country == 'Japan':
            local_amount=int(usd_amount * config['exchange_rate'])
        else:
            local_amount = int(usd_amount * config['exchange_rate'] * 100)  # in cents

        
        payload = {
            "transactionReference": f"PYPL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",
            },
            "instruction": {
                "method": "paypal",
                "value": {
                    "amount": local_amount,
                    "currency": config['currency']
                },
                "narrative": {
                    "line1": "APG Service"
                },
                "paymentInstrument": {
                    "type": "direct",
                    "billingAddress": {
                        **config['billing_address'],    
                    }
                },
                "settlement": {
                   "auto": True
                },
                "resultUrls": {
                    "cancel": url_for('bills', _external=True),
                    "failure": url_for('bills', _external=True),
                    "pending": url_for('bills', _external=True),
                    "success": url_for('payment_success', _external=True),
                    
                },
                "shipping": {
                    **config['shipping'],
                },
                "customer": {
                    **config['customer'],
                },
            }
        }
        headers = {
            "Content-Type": "application/json",
            "WP-Api-Version": "2024-07-01"
        }
        # 4. Call Paypal API
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
            local=format_amount(local_amount / 100, country)
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
                'paid_currency': config['currency']
            })
            return jsonify({
                'status': 'success',
                'redirect_url': data.get('redirect')
            })

        return jsonify({
            'status': 'error',
            'message': 'Paypal API error',
            'response': response.text
        }), 400

    except Exception:
        return jsonify({'status': 'error', 'message': 'Processing failed'}), 500

@app.route('/process_paysafecard', methods=['POST'])
def process_paysafecard():
    try:
        
        country = session.get('country') 
        
        # 2. Country validation and config
        COUNTRY_SETTINGS = {
            'Germany': {
                'currency': 'EUR',
                'country': 'DE',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'hans@example.com'
                },
            },
            'France': {
                'currency': 'EUR',
                'country': 'FR',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'jean@example.com'
                }
            },
            'Italy': {
                'currency': 'EUR',
                'country': 'IT',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'mario@example.com'
                }
            },
            'Belgium': {
                'currency': 'EUR',
                'country': 'BE',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'jan@example.com'
                }
            },
            'United Kingdom': {
                'currency': 'GBP',
                'country': 'GB',
                'exchange_rate': 0.75,
                'customer': {
                    'email': 'john@example.com'
                }
            },
        }
        
        if country not in COUNTRY_SETTINGS:
            return jsonify({
                'status': 'error',
                'message': f'Paysafecard not supported in {country}',
                'supported_countries': list(COUNTRY_SETTINGS.keys())
            }), 400

        config = COUNTRY_SETTINGS[country]
        
        total_amount = session.get('total_amount', 0)
        local_amount = float(total_amount) * config['exchange_rate'] * 100  # in cents

        # 3. Build fixed paysafecard payload (structure never changes)
        payload = {
            "transactionReference": f"PAYSFECRD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",
            },
            "instruction": {
                "method": "paysafecard",
                "value": {
                    "amount": int(float(local_amount)), 
                    "currency": config['currency']
                },
                "narrative": {
                    "line1": "APG Service"
                },
                "paymentInstrument": {
                    "type": "direct",
                    "country": config['country'],
                },
                "resultUrls": {
                    "pending": url_for('bills', _external=True),                  
                    "success": url_for('payment_success', _external=True),
                    "cancel": url_for('bills', _external=True)
                },
                "customer": {
                    **config['customer'],
                }
            }
        }
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
        # 5. Handle response
        if response.status_code == 201:
            data = response.json()
            local=format_amount(local_amount / 100, country)
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
                'paid_currency': config['currency']
            })
            return jsonify({
                'status': 'success',
                'redirect_url': data.get('redirect')
            })

        return jsonify({
            'status': 'error',
            'message': 'Paysafecard API error',
            'response': response.text
        }), 400

    except Exception:
        return jsonify({'status': 'error', 'message': 'Processing failed'}), 500

@app.route('/process_openbanking', methods=['POST'])
def process_openbanking():
    try:
        
        country = session.get('country') 
        
        # 2. Country validation and config
        COUNTRY_SETTINGS = {
            'Germany': {
                'currency': 'EUR',
                'country': 'DE',
                'language': 'de',
                'bankCode': '1345',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'hans@example.com',
                    'customerId': 'id1234',
                },
            },
            'France': {
                'currency': 'EUR',
                'country': 'FR',
                'language': 'fr',
                'bankCode': '5678',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'jean@example.com',
                    'customerId': 'id5678',
                }
            },
            'Italy': {
                'currency': 'EUR',
                'country': 'IT',
                'language': 'it',
                'bankCode': '9101',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'mario@example.com',
                    'customerId': 'id9101',
                }
            },
            'Belgium': {
                'currency': 'EUR',
                'country': 'BE',
                'language': 'nl',
                'bankCode': '1122',
                'exchange_rate': 0.85,
                'customer': {
                    'email': 'jan@example.com',
                    'customerId': 'id1122',
                }
            },
            'United Kingdom': {
                'currency': 'GBP',
                'country': 'GB',
                'language': 'en',
                'bankCode': '3344',
                'exchange_rate': 0.75,
                'customer': {
                    'email': 'john@example.com',
                    'customerId': 'id3344',
                }
            },
        }
        
        if country not in COUNTRY_SETTINGS:
            return jsonify({
                'status': 'error',
                'message': f'Openbanking not supported in {country}',
                'supported_countries': list(COUNTRY_SETTINGS.keys())
            }), 400

        config = COUNTRY_SETTINGS[country]
        
        total_amount = session.get('total_amount', 0)
        local_amount = float(total_amount) * config['exchange_rate'] *100  # in cents

        # 3. Build fixed openbanking payload (structure never changes)
        payload = {
            "transactionReference": f"OPENBANK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",
            },
            "instruction": {
                "method": "open_banking",
                "expiryIn": 200, 
                "value": {
                    "amount": int(float(local_amount)), 
                    "currency": config['currency']
                },
                "narrative": {
                    "line1": "APG Service"
                },
                "paymentInstrument": {
                    "type": "direct",
                    "country": config['country'],
                    "language": config['language'],
                    "bankCode": config['bankCode'],
                },
                "resultUrls": {
                    "pending": url_for('bills', _external=True),                  
                    "success": url_for('payment_success', _external=True),
                    "cancel": url_for('bills', _external=True),
                    "failure": url_for('bills', _external=True)
                },
                "customer": {
                    **config['customer'],
                }
            }
        }
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
        # 5. Handle response
        if response.status_code == 201:
            data = response.json()
            local=format_amount(local_amount / 100, country)
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
                'paid_currency': config['currency']
            })
            return jsonify({
                'status': 'success',
                'redirect_url': data.get('redirect')
            })

        return jsonify({
            'status': 'error',
            'message': 'Openbanking API error',
            'response': response.text
        }), 400

    except Exception:
        return jsonify({'status': 'error', 'message': 'Processing failed'}), 500

@app.route('/process_bancontact', methods=['POST'])
def process_bancontact():
        
        total_amount = session.get('total_amount', 0)
        local_amount = float(total_amount) * 0.85 *100  # in cents

        # 3. Build fixed bancontact payload (structure never changes)
        payload = {
            "transactionReference": f"BANCONT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",
            },
            "instruction": {
                "method": "bancontact",
                "value": {
                    "amount": int(float(local_amount)),
                    "currency": "EUR"
                },
                "narrative": {
                    "line1": "APG Service"
                },
                "paymentInstrument": {
                    "type": "direct",
                    "country": "BE",  
                },
                "resultUrls": {
                    "cancel": url_for('bills', _external=True),
                    "pending": url_for('bills', _external=True),                  
                    "success": url_for('payment_success', _external=True),
                    
                },
                "customer": {
                    "email": 'jan@example.com',
                }
            }
        }
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
        # 5. Handle response
        if response.status_code == 201:
            data = response.json()
            country = session.get('country', 'Belgium')
            local=format_amount(local_amount / 100, country)
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
                'paid_currency': 'EUR',
            })
            return jsonify({
                'status': 'success',
                'redirect_url': data.get('redirect')
            })

        return jsonify({
            'status': 'error',
            'message': 'bancontact API error',
            'response': response.text
        }), 400

@app.route('/process_konbini', methods=['POST'])
def process_konbini():
        
        config = {
            'customer': {
                'lastName': 'Yamada',
                'email': 'Taro@example.com',
                'phone': '08012345678',
            }
        }
        
        total_amount = session.get('total_amount', 0)
        local_amount = float(total_amount) * 147.82 

        # 3. Build fixed konbini payload (structure never changes)
        payload = {
            "transactionReference": f"KONBINI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "merchant": {
                "entity": "default",
            },
            "instruction": {
                "method": "konbini",
                "value": {
                    "amount": int(float(local_amount)),  
                    "currency": 'JPY',
                },
                "narrative": {
                    "line1": "APG Service"
                },
                "paymentInstrument": {
                    "type": "direct",
                    "country": 'JP',
                },
                "resultUrls": {
                    "pending": url_for('payment_success', _external=True)                  
                },
                "customer": {
                    **config['customer'],
                }
            }
        }
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
        # 5. Handle response
        if response.status_code == 201:
            data = response.json()
            country = session.get('country', 'Japan')
            local=format_amount(local_amount / 100, country)
            session.update({
                'payment_id': data.get('paymentId'),
                'transaction_ref': payload['transactionReference'],
                'paid_amount': local,
                'paid_currency': 'JPY'
            })
            return jsonify({
                'status': 'success',
                'redirect_url': data.get('redirect')
            })

        return jsonify({
            'status': 'error',
            'message': 'Konbini API error',
            'response': response.text
        }), 400
    
@app.route('/success')
def payment_success():

    country = session.get('country', '')
    lang_code = LANGUAGE_MAP.get(country)

    """Unified success page for all payment methods"""
    return render_template('success.html',
        payment_id=session.get('payment_id'),
        transaction_ref=session.get('transaction_ref'),
        amount_usd=session.get('total_amount'),
        amount_paid=session.get('paid_amount'),
        currency=session.get('paid_currency'),
        method=session.get('payment_method'),
        date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        lang_code=lang_code,
    )

if __name__ == '__main__':
    app.run(debug=True)
