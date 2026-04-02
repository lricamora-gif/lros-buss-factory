#!/usr/bin/env python3
"""
ONE-BUTTON PLAY – PROJECT 1: 1,000 BUSINESSES FACTORY
Run this on Render. It will continuously create new micro‑businesses
with subdomains like weightloss.moccasin.ph, each with its own landing page and payment link.
"""

import os
import sys
import json
import time
import random
import requests
from dotenv import load_dotenv

load_dotenv()

# ==================== CONFIGURATION ====================
# Environment variables – set these on Render
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")          # base for Businesses table
PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY")
NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN")                # Netlify personal access token
DOMAIN = "moccasin.ph"                                    # your domain

# LROS orchestrator URL (your backend)
LROS_API = "https://lros1.onrender.com/api/generate"

# ==================== FUNCTIONS ====================

def generate_business_package():
    """Call LROS Business Factory agent to generate a random business package."""
    topics = ["weight loss", "crypto trading", "parenting tips", "home workout",
              "meditation", "digital marketing", "budgeting", "meal prep",
              "language learning", "DIY crafts"]
    topic = random.choice(topics)
    prompt = f"""
You are the Business Factory. Generate a complete business package for topic: {topic}.
Output JSON with: business_name, lead_magnet_title, lead_magnet_content,
email_sequence (list of {day, subject, body}), social_media_posts (list of {text}).
"""
    resp = requests.post(LROS_API, json={"prompt": prompt, "model": "deepseek", "pattern": "chain"})
    if resp.status_code != 200:
        raise Exception(f"LROS call failed: {resp.status_code}")
    package_text = resp.json()["response"]
    # Extract JSON from response (may be wrapped in markdown)
    try:
        # Attempt to parse whole response as JSON
        package = json.loads(package_text)
    except json.JSONDecodeError:
        # Look for JSON block
        import re
        match = re.search(r'\{.*\}', package_text, re.DOTALL)
        if match:
            package = json.loads(match.group(0))
        else:
            raise Exception("Could not parse JSON from LROS response")
    return package

def create_netlify_site(business_name):
    """Create a Netlify site with a subdomain of moccasin.ph."""
    subdomain = business_name.lower().replace(' ', '-')
    # Create site via Netlify API
    headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"}
    # First, create a new site
    resp = requests.post("https://api.netlify.com/api/v1/sites", headers=headers, json={
        "name": subdomain,
        "custom_domain": f"{subdomain}.{DOMAIN}",
        "force_ssl": True
    })
    if resp.status_code != 200:
        raise Exception(f"Netlify site creation failed: {resp.text}")
    site = resp.json()
    site_id = site["id"]
    # Now we need to deploy a simple HTML landing page. For now, we'll just return the URL.
    # In a real implementation, you'd deploy content via Netlify's deploy API.
    # Here we'll return the site URL and assume you'll manually add content later.
    return f"https://{subdomain}.{DOMAIN}", site_id

def create_paymongo_link(business_name, amount_php=2700):
    """Create a one‑time payment link via PayMongo."""
    headers = {
        "Authorization": f"Basic {PAYMONGO_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "data": {
            "attributes": {
                "amount": amount_php * 100,  # centavos
                "description": f"Product from {business_name}",
                "currency": "PHP",
                "remarks": "One‑time purchase"
            }
        }
    }
    resp = requests.post("https://api.paymongo.com/v1/links", headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        raise Exception(f"PayMongo link creation failed: {resp.text}")
    return resp.json()["data"]["attributes"]["checkout_url"]

def log_to_airtable(business_name, subdomain, landing_url, payment_link):
    """Add a record to Airtable Businesses table."""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Businesses"
    data = {
        "records": [{
            "fields": {
                "Name": business_name,
                "Subdomain": subdomain,
                "Landing Page URL": landing_url,
                "Payment Link": payment_link,
                "Created At": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "Status": "launched"
            }
        }]
    }
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code != 200:
        raise Exception(f"Airtable record creation failed: {resp.text}")
    print(f"✅ Airtable record added for {business_name}")

def launch_business(package):
    """Create a full business from the package."""
    print(f"🚀 Launching {package['business_name']}...")
    landing_url, site_id = create_netlify_site(package['business_name'])
    payment_link = create_paymongo_link(package['business_name'])
    log_to_airtable(package['business_name'],
                    package['business_name'].lower().replace(' ', '-'),
                    landing_url,
                    payment_link)
    print(f"✅ Business {package['business_name']} live at {landing_url}")
    # Optionally, you could also deploy the landing page content using Netlify's deploy API
    # For now, the site is empty; you can later add a simple HTML page manually or via a template.

def factory_loop():
    """Main loop – creates one business per hour."""
    print("🏭 Business Factory started. Will create one business per hour.")
    while True:
        try:
            package = generate_business_package()
            launch_business(package)
        except Exception as e:
            print(f"❌ Error creating business: {e}")
        print("⏳ Waiting 1 hour before next business...")
        time.sleep(3600)  # one hour; change to 300 for 5 minutes for faster testing

def main():
    print("\n🔥 ONE-BUTTON PLAY – PROJECT 1: 1,000 BUSINESSES FACTORY\n")
    # Check required environment variables
    required = ["AIRTABLE_TOKEN", "AIRTABLE_BASE_ID", "PAYMONGO_SECRET_KEY", "NETLIFY_TOKEN"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Please set them on Render (or in .env) and run again.")
        return
    # Start the factory
    factory_loop()

if __name__ == "__main__":
    main()
