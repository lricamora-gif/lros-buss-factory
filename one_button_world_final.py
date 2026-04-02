#!/usr/bin/env python3
"""
ONE-BUTTON WORLD PLAY – With moccasin.ph subdomains, PayMongo, Airtable, and Zapier social posting.
"""

import os
import sys
import json
import time
import random
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIGURATION ====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
NETLIFY_AUTH_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_PERSONAL_ACCESS_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Domain settings
ROOT_DOMAIN = "moccasin.ph"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ==================== NETLIFY SUBDOMAIN & DEPLOY ====================
def add_netlify_subdomain(subdomain):
    """Add a subdomain to the site via Netlify API."""
    # First, get the site ID (you may need to store it or fetch it once)
    # For simplicity, we assume you have a site already created. We'll fetch it.
    headers = {"Authorization": f"Bearer {NETLIFY_AUTH_TOKEN}"}
    # Get all sites
    sites_resp = requests.get("https://api.netlify.com/api/v1/sites", headers=headers)
    sites_resp.raise_for_status()
    sites = sites_resp.json()
    # Find the site with the root domain (or the first one; adjust as needed)
    site = next((s for s in sites if s.get("custom_domain") == ROOT_DOMAIN), sites[0])
    site_id = site["id"]

    # Add custom domain
    domain_name = f"{subdomain}.{ROOT_DOMAIN}"
    payload = {"domain": domain_name}
    resp = requests.post(f"https://api.netlify.com/api/v1/sites/{site_id}/domains", headers=headers, json=payload)
    if resp.status_code == 409:
        # Domain already exists
        print(f"   Domain {domain_name} already exists.")
    else:
        resp.raise_for_status()
    return domain_name

def deploy_netlify_site(business, payment_link, subdomain):
    """Deploy a landing page using Netlify API."""
    # Build a simple HTML page (you can use a template)
    html = f"""
    <html>
    <head><title>{business['business_name']}</title></head>
    <body>
        <h1>{business['business_name']}</h1>
        <p>Download your free guide: {business['lead_magnet_title']}</p>
        <form action="/subscribe" method="post">
            <input type="email" name="email" placeholder="Your email">
            <button>Get it now</button>
        </form>
        <a href="{payment_link}">Buy Now – ₱27</a>
    </body>
    </html>
    """
    # Deploy via Netlify API – you need to create a new deployment.
    # For simplicity, we'll just return the URL; you'll implement actual deploy.
    return f"https://{subdomain}.{ROOT_DOMAIN}"

# ==================== PAYMENT, AIRTABLE, SUPABASE ====================
def create_paymongo_link(amount_php=27, description="Digital product"):
    headers = {
        "Authorization": f"Basic {PAYMONGO_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "data": {
            "attributes": {
                "amount": amount_php * 100,
                "description": description,
                "currency": "PHP",
                "remarks": "One-time purchase",
                "send_email_receipt": False
            }
        }
    }
    resp = requests.post("https://api.paymongo.com/v1/links", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["data"]["attributes"]["checkout_url"]

def log_to_airtable(business, landing_url, payment_link):
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Businesses"
    data = {
        "records": [{
            "fields": {
                "Name": business["business_name"],
                "Landing Page URL": landing_url,
                "Lead Magnet Title": business["lead_magnet_title"],
                "Payment Link": payment_link,
                "Created At": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "Status": "launched"
            }
        }]
    }
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    print("✅ Logged to Airtable")

def store_in_supabase(business, landing_url, payment_link):
    record = {
        "name": business["business_name"],
        "payment_link": payment_link,
        "landing_page_url": landing_url,
        "lead_magnet_title": business["lead_magnet_title"],
        "lead_magnet_content": business["lead_magnet_content"],
        "email_sequence": json.dumps(business["email_sequence"]),
        "social_posts": json.dumps(business["social_media_posts"])
    }
    supabase.table("businesses").insert(record).execute()

# ==================== BUSINESS FACTORY AGENT ====================
def create_business_package(topic):
    resp = requests.post(
        "https://lros1.onrender.com/api/generate",
        json={
            "prompt": f"You are the Business Factory. Generate a complete business package for topic: {topic}. Output JSON with: business_name, lead_magnet_title, lead_magnet_content, email_sequence, social_media_posts.",
            "model": "deepseek",
            "pattern": "chain"
        }
    )
    if resp.status_code != 200:
        raise Exception("Business Factory call failed")
    package_text = resp.json()["response"]
    return json.loads(package_text)

# ==================== LAUNCH A BUSINESS ====================
def launch_business(package):
    print(f"🚀 Launching {package['business_name']}...")
    # 1. Create subdomain
    subdomain = package['business_name'].lower().replace(' ', '-')
    domain = add_netlify_subdomain(subdomain)
    # 2. Create payment link
    payment_link = create_paymongo_link()
    # 3. Deploy landing page
    landing_url = deploy_netlify_site(package, payment_link, subdomain)
    # 4. Store in Supabase
    store_in_supabase(package, landing_url, payment_link)
    # 5. Log to Airtable (triggers Zapier social posting)
    log_to_airtable(package, landing_url, payment_link)
    print(f"✅ {package['business_name']} live at {landing_url}")

# ==================== FACTORY LOOP ====================
def start_factory():
    topics = ["weight loss", "crypto trading", "parenting tips", "home workout", "meditation", "digital marketing"]
    while True:
        topic = random.choice(topics)
        try:
            package = create_business_package(topic)
            launch_business(package)
        except Exception as e:
            print(f"❌ Failed to create business: {e}")
        time.sleep(3600)  # create one per hour; adjust to 600 for faster

# ==================== MAIN ====================
def main():
    print("\n🔥 ONE-BUTTON WORLD PLAY – Subdomain + PayMongo + Airtable\n")
    # Optional: scale workers (if you have Render API keys)
    # scale_workers()  # you can implement similar to earlier
    print("✅ Starting Business Factory...")
    start_factory()

if __name__ == "__main__":
    main()
