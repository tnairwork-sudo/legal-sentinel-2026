import os
import json
import requests
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

# 1. SETUP: AI & TNLAW Database
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# The "Direct Text" Connection Fix
if not firebase_admin._apps:
    # This part takes your giant secret key and turns it into a real badge
    key_dict = json.loads(os.environ["FIREBASE_KEY_PATH"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. THE HUNTER: Finding Leads
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        "q_keywords": "India Expansion, Renewable Energy, FDI",
        "locations": ["United Kingdom", "United Arab Emirates"],
        "person_titles": ["General Counsel", "CEO"],
        "organization_num_employees_ranges": ["200,10000"] 
    }
    try:
        response = requests.post(url, json=data)
        return response.json().get('people', [])
    except:
        return []

# 3. THE COUNSEL: Drafting
def draft_retainer_email(lead):
    company = lead.get('organization', {}).get('name', 'your firm')
    prompt = f"Draft a high-end cold email for Tushar Nair (SC Advocate) to {lead['name']} at {company} about April 2026 legal risks and a retainer."
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Drafting error."

# 4. EXECUTION
leads = get_leads()
if not leads:
    print("No leads found today.")
else:
    for lead in leads[:5]:
        email_draft = draft_retainer_email(lead)
        db.collection("sentinel_leads").add({
            "name": lead['name'],
            "company": lead['organization']['name'],
            "draft": email_draft,
            "timestamp": firestore.SERVER_VALUE
        })
        print(f"Pushed {lead['name']} to Dashboard.")
