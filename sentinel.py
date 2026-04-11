import os
import json
import requests
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

# 1. AUTHENTICATION
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

if not firebase_admin._apps:
    key_dict = json.loads(os.environ["FIREBASE_KEY_PATH"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. THE MULTI-CHANNEL SEARCH
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    
    # BROADENED CRITERIA: Captures Startup (AngelList), Corporate (LinkedIn), and Job Seekers (Glassdoor)
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        # Keywords for Freelance, Due Diligence, and Advisory
        "q_keywords": "Contract Drafting, Legal Due Diligence, Document Review, Corporate Advisory, FDI India, Electricity Law, Fundraising, Startup Legal", 
        "locations": ["United Kingdom", "United Arab Emirates", "India", "Singapore", "United States"],
        "person_titles": ["General Counsel", "Founder", "CEO", "Legal Manager", "Head of Legal", "Operations Director"],
        # Focusing on Mid-to-Large firms for Retainers, and Startups for Advisory
        "organization_num_employees_ranges": ["10,5000"] 
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json().get('people', [])
    except Exception as e:
        print(f"Aggregator Error: {e}")
        return []

# 3. THE "BOUTIQUE ADVOCATE" PROPOSAL (Gemini)
def draft_strategy(lead):
    name = lead.get('name', 'Counsel')
    company = lead.get('organization', {}).get('name', 'your firm')
    
    # Positioning you as a Supreme Court Advocate for elite freelance/corporate work
    prompt = f"""
    Draft a high-end, authoritative outreach for Tushar Nair, Supreme Court Advocate.
    Recipient: {name} at {company}.
    Services to Pitch: 
    1. High-velocity Document Review & Contract Drafting.
    2. Strategic Due Diligence for Indian expansions or FDI.
    3. Specialized Electricity Law & Philanthropy Advisory.
    Context: It is April 2026. Mention structural resilience and regulatory compliance.
    Tone: Sophisticated, Savile Row aesthetic, 'The fixer' energy. 
    Constraint: Keep it under 250 words.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Strategic draft failed: {e}"

# 4. THE EXECUTION
print("Sentinel is scanning Global Channels (LinkedIn/AngelList/Corporate)...")
leads = get_leads()

if not leads:
    print("Vault empty: No firms currently matching the 'Expansion' or 'Advisory' triggers.")
else:
    print(f"Targets Acquired: {len(leads)}. Filtering for Tier-1 Opportunities...")
    for lead in leads[:8]: # Increased to 8 leads per run
        company_name = lead.get('organization', {}).get('name', 'Global Venture')
        print(f"Infiltrating {company_name}...")
        
        email_strategy = draft_strategy(lead)
        
        db.collection("sentinel_leads").add({
            "name": lead['name'],
            "company": company_name,
            "draft": email_strategy,
            "service_tag": "Corporate/Freelance", # Helps your dashboard label them
            "timestamp": firestore.SERVER_VALUE
        })
        print(f"DATA SECURED: {lead['name']} uploaded to Command Center.")

print("Sentinel standby.")
