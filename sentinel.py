import os
import json
import requests
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

# 1. AUTHENTICATION & INITIALIZATION
# This uses the secrets you've already configured in your GitHub repository
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

if not firebase_admin._apps:
    # Decodes the Firebase Service Account JSON from your GitHub Secrets
    key_dict = json.loads(os.environ["FIREBASE_KEY_PATH"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. LEAD SEARCH (Apollo.io)
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    # BROADER TEST CRITERIA: Ensures the Vault gets filled immediately
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        "q_keywords": "Legal, Director, Law Firm, General Counsel, India Expansion", 
        "locations": ["United Kingdom", "United Arab Emirates", "India", "United States"],
        "person_titles": ["General Counsel", "CEO", "Partner", "Legal Director"],
        "organization_num_employees_ranges": ["20,10000"] 
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json().get('people', [])
    except Exception as e:
        print(f"Apollo API Error: {e}")
        return []

# 3. AI STRATEGY DRAFT (Gemini)
def draft_strategy(lead):
    name = lead.get('name', 'Colleague')
    company = lead.get('organization', {}).get('name', 'your organization')
    
    prompt = f"""
    Draft a high-end, cinematic outreach for Tushar Nair, a Supreme Court Advocate.
    Recipient: {name} at {company}.
    Context: They are navigating Indian regulatory shifts (Electricity Law, FCRA, or FDI) in April 2026.
    Requirement: Propose a strategic monthly retainer for structural resilience.
    Tone: Savile Row precision, authoritative, and bespoke.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Drafting Error: {e}")
        return "Drafting error occurred. Please review manually."

# 4. EXECUTION LOOP
print("Initiating Hunt...")
leads = get_leads()

if not leads:
    print("No leads found with current criteria. System idling.")
else:
    print(f"Found {len(leads)} potential targets. Processing top 5...")
    # Limit to 5 leads per run to keep your dashboard clean and high-value
    for lead in leads[:5]:
        company_name = lead.get('organization', {}).get('name', 'Confidential Firm')
        print(f"Analyzing {lead['name']} at {company_name}...")
        
        email_strategy = draft_strategy(lead)
        
        # Pushes data directly into your Firestore "Vault"
        db.collection("sentinel_leads").add({
            "name": lead['name'],
            "company": company_name,
            "draft": email_strategy,
            "timestamp": firestore.SERVER_VALUE
        })
        print(f"SUCCESS: {lead['name']} secured to the Vault.")

print("Mission Complete. Sentinel standing down.")
