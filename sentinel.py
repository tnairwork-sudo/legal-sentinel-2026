import os
import json
import requests
from google import genai
import firebase_admin
from firebase_admin import credentials, firestore

# 1. AUTHENTICATION & 2026 AI UPGRADE
# Switching to the modern 'google-genai' standard
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

if not firebase_admin._apps:
    # Decodes the Firebase Secret string from your GitHub environment
    key_dict = json.loads(os.environ["FIREBASE_KEY_PATH"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. THE MULTI-CHANNEL HUNTER (FIXES 422 ERROR)
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    
    # Corrected parameters for LinkedIn/AngelList/Glassdoor aggregated data
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        # Broadening to your new freelance/corporate services
        "q_keywords": "Contract Drafting, Legal Due Diligence, Doc Review, Corporate Advisory, India Expansion, FDI compliance", 
        "locations": ["United Kingdom", "United Arab Emirates", "India", "Singapore", "United States"],
        "person_titles": ["General Counsel", "Founder", "CEO", "Legal Manager", "Head of Legal", "Operations Director"],
        # Uses standard Apollo range strings to prevent 422 errors
        "organization_num_employees_ranges": ["11-50", "51-200", "201-500", "501-1000", "1001-5000"]
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code != 200:
            print(f"Aggregator Error {response.status_code}: {response.text}")
            return []
        return response.json().get('people', [])
    except Exception as e:
        print(f"Network Error: {e}")
        return []

# 3. THE "FIXER" PROPOSAL LOGIC
def draft_strategy(lead):
    name = lead.get('name', 'Counsel')
    company = lead.get('organization', {}).get('name', 'your firm')
    
    prompt = f"""
    Draft a high-end, authoritative pitch for Tushar Nair, Supreme Court Advocate.
    Recipient: {name} at {company}.
    Services Offered: High-velocity Document Review, Custom Contract Drafting, Strategic Due Diligence, and Indian Regulatory Advisory (FDI/Electricity).
    Tone: Savile Row luxury meets 'The Fixer'. Position Tushar as the elite partner for structural resilience in India.
    Constraint: Keep it cinematic and under 200 words.
    """
    
    try:
        # Using Gemini 3.1 Flash for 2026-grade precision
        response = client.models.generate_content(
            model="gemini-3.1-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"AI Drafting logic standby: {e}"

# 4. THE MISSION
print("Sentinel scanning global LinkedIn/AngelList indices...")
leads = get_leads()

if not leads:
    print("Vault Empty: No firms currently matching the 'Freelance/Advisory' triggers.")
else:
    print(f"Targets Acquired: {len(leads)}. Uploading top 8 to the Command Center...")
    for lead in leads[:8]:
        company_name = lead.get('organization', {}).get('name', 'Global Venture')
        print(f"Analyzing {company_name}...")
        
        email_strategy = draft_strategy(lead)
        
        # Pushes with a specific tag so your dashboard knows it's an advisory lead
        db.collection("sentinel_leads").add({
            "name": lead['name'],
            "company": company_name,
            "draft": email_strategy,
            "service_tag": "Boutique Advisory",
            "timestamp": firestore.SERVER_VALUE
        })
        print(f"DATA SECURED: {lead['name']} is live in the Command Center.")

print("Sentinel standby.")
