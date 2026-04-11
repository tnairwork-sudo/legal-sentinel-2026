import os
import json
import requests
from google import genai
import firebase_admin
from firebase_admin import credentials, firestore

# 1. AUTHENTICATION & MODERN AI SETUP
# Switching to the 2026 'google-genai' standard
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

if not firebase_admin._apps:
    key_dict = json.loads(os.environ["FIREBASE_KEY_PATH"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. THE CORRECTED SEARCH (FIXES 422 ERROR)
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    
    # Corrected Apollo Range Formats: Standard strings like "21-50"
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        "q_keywords": "Contract Drafting, Legal Due Diligence, Doc Review, Corporate Advisory, FDI India", 
        "locations": ["United Kingdom", "United Arab Emirates", "India", "Singapore", "United States"],
        "person_titles": ["General Counsel", "Founder", "CEO", "Head of Legal", "Operations Director"],
        "organization_num_employees_ranges": ["11-50", "51-100", "101-200", "201-500", "501-1000"]
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json().get('people', [])
    except Exception as e:
        # This will now capture and print the specific reason for 422 errors if they persist
        print(f"Aggregator Error Detail: {e}")
        return []

# 3. THE FIXED AI DRAFTING (Gemini 3.0 Flash)
def draft_strategy(lead):
    name = lead.get('name', 'Counsel')
    company = lead.get('organization', {}).get('name', 'the firm')
    
    prompt = f"""
    Draft a high-end outreach for Tushar Nair, Supreme Court Advocate.
    Recipient: {name} at {company}.
    Services: High-velocity Doc Review, Custom Contract Drafting, and Strategic Due Diligence for April 2026 compliance.
    Vibe: Savile Row luxury fixer. 
    Pitch: A flexible advisory retainer for global resilience.
    """
    
    try:
        # Using the new 2026 'google-genai' syntax
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Optimized for speed and quality
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Drafting logic failed: {e}"

# 4. EXECUTION
print("Sentinel is scanning Global Channels (LinkedIn/AngelList/Corporate)...")
leads = get_leads()

if not leads:
    print("Vault empty: No firms currently matching the triggers.")
else:
    print(f"Targets Acquired: {len(leads)}. Processing top 8...")
    for lead in leads[:8]:
        company_name = lead.get('organization', {}).get('name', 'Venture Firm')
        print(f"Securing {company_name}...")
        
        email_strategy = draft_strategy(lead)
        
        db.collection("sentinel_leads").add({
            "name": lead['name'],
            "company": company_name,
            "draft": email_strategy,
            "service_tag": "Corporate Advisory",
            "timestamp": firestore.SERVER_VALUE
        })
        print(f"VAULT UPDATED: {lead['name']} is live in Command Center.")

print("Sentinel standby.")
