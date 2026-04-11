import os
import requests
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

# 1. SETUP: AI & Database Connection
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# Initialize Firebase only if not already initialized
if not firebase_admin._apps:
    # This uses the secret key you will add in Step 2
    cred = credentials.Certificate(os.environ["FIREBASE_KEY_PATH"])
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. THE HUNTER: Finding $50M+ Revenue Firms in UK/UAE/US
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        "q_keywords": "India Expansion, Renewable Energy, NGO Compliance, FDI",
        "locations": ["United Kingdom", "United Arab Emirates", "United States"],
        "person_titles": ["General Counsel", "Chief Legal Officer", "CEO", "Founder"],
        "organization_num_employees_ranges": ["200,10000"] 
    }
    try:
        response = requests.post(url, json=data)
        return response.json().get('people', [])
    except Exception as e:
        print(f"Apollo Error: {e}")
        return []

# 3. THE COUNSEL: Drafting the Retainer Pitch
def draft_retainer_email(lead):
    company = lead.get('organization', {}).get('name', 'your firm')
    industry = lead.get('organization', {}).get('industry', 'International Business')
    
    prompt = f"""
    Draft a candid, elite cold email for Tushar Nair, Supreme Court Advocate. 
    Recipient: {lead['name']}, Company: {company}, Sector: {industry}.
    
    TONE: Confident, peer-to-peer, authoritative. No 'Hope you are well'.
    
    STRATEGY:
    - Focus on 'Structural Resilience Retainers' for Indian governance.
    - Mention the April 1st, 2026 Electricity Rule 3 changes (for Energy) or the 2026 FCRA Bill (for NGOs).
    - Hook: Invite to 'The Big Dinner' in London/Dubai/Delhi.
    - CTA: 15-min briefing. https://calendly.com/tusharnair/15min
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Drafting error: {e}"

# 4. EXECUTION: Finding leads and pushing to your "App"
leads = get_leads()
if not leads:
    print("No leads found today. Checking again tomorrow.")
else:
    for lead in leads[:5]:
        email_draft = draft_retainer_email(lead)
        
        # PUSH TO FIRESTORE (Your App's Database)
        lead_data = {
            "name": lead['name'],
            "company": lead['organization']['name'],
            "title": lead['title'],
            "industry": lead.get('organization', {}).get('industry', 'N/A'),
            "draft": email_draft,
            "status": "New",
            "timestamp": firestore.SERVER_VALUE
        }
        
        db.collection("sentinel_leads").add(lead_data)
        print(f"Lead for {lead['name']} pushed to your Dashboard.")
