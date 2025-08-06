from flask import Flask, render_template, request, jsonify, redirect, url_for
import uuid
from datetime import datetime, timedelta
import os
from supabase import create_client, Client
import random

app = Flask(__name__)

# Supabase configuration
SUPABASE_URL = "https://tddovxrnfnrdvrludfwb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRkZG92eHJuZm5yZHZybHVkZndiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQyOTUwMTgsImV4cCI6MjA2OTg3MTAxOH0.iTug0w1UXP9gRWIyhhYQrudt-UAASXAvWtvXfhe_oqI"
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
    
    return redirect(url_for('bills'))

if __name__ == '__main__':
    app.run(debug=True)