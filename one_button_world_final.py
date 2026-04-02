#!/usr/bin/env python3
"""
ONE-BUTTON PLAY – PROJECT 1: 1,000 BUSINESSES FACTORY
With Telegram notifications for every business created.
"""

import os
import sys
import json
import time
import random
import requests
from dotenv import load_dotenv

load_dotenv()

# ==================== ENVIRONMENT VARIABLES ====================
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_PERSONAL_ACCESS_TOKEN")
NETLIFY_TOKEN = os.getenv("NETLIFY_AUTH_TOKEN")
PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY")

# Telegram – hardcoded from user input (keep secure in production)
TELEGRAM_BOT_TOKEN = "8395136153:AAH_ENfSu1D_MmiypO_8L4_xmjQYysjh_G0"
TELEGRAM_CHAT_ID = "8792022943"

# LROS orchestrator endpoint
LROS_API = "https://lros1.onrender.com/api/generate"
DOMAIN = "moccasin.ph"

# ==================== FUNCTIONS ====================

def send_telegram(message):
    """Send a message to your Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def generate_business_package():
    topics = ["weight loss", "crypto trading", "parenting tips", "home workout",
              "meditation", "digital marketing", "budgeting", "meal prep"]
    topic = random.choice(topics)
    prompt = f"""
You are the Business Factory. Generate a complete business package for topic: {topic}.
Output JSON with: business_name, lead_magnet_title, lead_magnet_content,
email_sequence (list of {{day, subject, body}}), social_media_posts (list of {{text}}).
"""
    resp = requests.post(LROS_API, json={"prompt": prompt, "model": "deepseek", "pattern": "chain"})
    if resp.status_code != 200:
        raise Exception(f"LROS call failed: {resp.status_code}")
    text = resp.json()["response"]
    try:
        return json.loads(text)
    except:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise Exception("Could not parse JSON")

def create_netlify_site(name):
    sub = name.lower().replace(' ', '-')
    headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"}
    resp = requests.post("https://api.netlify.com/api/v1/sites", headers=headers, json={
        "name": sub,
        "custom_domain": f"{sub}.{DOMAIN}",
        "force_ssl": True
    })
    if resp.status_code != 200:
        raise Exception(f"Netlify error: {resp.text}")
    return f"https://{sub}.{DOMAIN}", resp.json()["id"]

def create_paymongo_link(name, amount_php=2700):
    headers = {"Authorization": f"Basic {PAYMONGO_SECRET_KEY}", "Content-Type": "application/json"}
    payload = {"data": {"attributes": {
        "amount": amount_php * 100,
        "description": f"Product from {name}",
        "currency": "PHP",
        "remarks": "One‑time purchase"
    }}}
    resp = requests.post("https://api.paymongo.com/v1/links", headers=headers, json=payload)
    if resp.status_code not in (200,201):
        raise Exception(f"PayMongo error: {resp.text}")
    return resp.json()["data"]["attributes"]["checkout_url"]

def log_to_airtable(name, sub, url, payment):
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    data = {"records": [{"fields": {
        "Name": name,
        "Subdomain": sub,
        "Landing Page URL": url,
        "Payment Link": payment,
        "Created At": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "Status": "launched"
    }}]}
    resp = requests.post(f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Businesses", headers=headers, json=data)
    if resp.status_code != 200:
        raise Exception(f"Airtable error: {resp.text}")

def launch_business(package):
    name = package['business_name']
    print(f"🚀 Launching {name}...")
    landing, _ = create_netlify_site(name)
    payment = create_paymongo_link(name)
    subdomain = name.lower().replace(' ', '-')
    log_to_airtable(name, subdomain, landing, payment)
    msg = f"✅ *New Business Created!*\n🏷️ Name: {name}\n🌐 Landing: {landing}\n💳 Payment: {payment}"
    send_telegram(msg)
    print(f"✅ {name} live at {landing}")

def main():
    send_telegram("🔥 *Business Factory Started* – Will create one new business every hour.")
    print("🔥 ONE-BUTTON PLAY – PROJECT 1: 1,000 BUSINESSES FACTORY")
    while True:
        try:
            pkg = generate_business_package()
            launch_business(pkg)
        except Exception as e:
            error_msg = f"⚠️ Error creating business: {e}"
            print(error_msg)
            send_telegram(error_msg)
        time.sleep(3600)  # one hour; change to 60 for testing

if __name__ == "__main__":
    main()
