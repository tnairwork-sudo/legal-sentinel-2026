import os
import json
import requests
from google import genai
import firebase_admin
from firebase_admin import credentials, firestore

# 1. 2026 MODERN AI SETUP

# Validate required environment variables before any API calls
required_env_vars = ["GEMINI_API_KEY", "APOLLO_API_KEY", "FIREBASE_KEY_PATH"]
missing_vars = [v for v in required_env_vars if not os.environ.get(v)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}. Set them before running the Sentinel.")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

if not firebase_admin._apps:
    key_dict = json.loads(os.environ["FIREBASE_KEY_PATH"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. THE MULTI-CHANNEL AGGREGATOR (FIXES 422 ERROR)
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    
    # Corrected formats for LinkedIn/AngelList indices
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        # Keywords specifically for Freelance/Doc Review/Expansion
        "q_keywords": "Contract Drafting, Legal Due Diligence, Document Review, Corporate Advisory, India Expansion, FDI compliance", 
        "locations": ["United Kingdom", "United Arab Emirates", "India", "Singapore", "United States"],
        "person_titles": ["General Counsel", "Founder", "CEO", "Head of Legal", "Operations Director"],
        # Uses standard Apollo strings to prevent 422 errors
        "organization_num_employees_ranges": ["11-50", "51-200", "201-500", "501-1000"]
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

# 3. THE "FIXER" PROPOSAL (GEMINI 3.0 FLASH)
def draft_strategy(lead):
    name = lead.get('name', 'Counsel')
    company = lead.get('organization', {}).get('name', 'your firm')
    
    prompt = f"""
    Draft a high-end, authoritative pitch for Tushar Nair, Supreme Court Advocate.
    Recipient: {name} at {company}.
    Services: High-velocity Doc Review, Custom Contract Drafting, Strategic Due Diligence, and Indian Regulatory Advisory.
    Tone: Savile Row luxury meets 'The Fixer'. Position Tushar as the elite partner for structural resilience.
    Constraint: Keep it under 200 words.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",  # Fixed: gemini-2.0-flash is not a valid model name
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"AI Draft Error for {name} at {company}: {e}")
        return f"AI Drafting logic standby: {e}"

# 4. MISSION EXECUTION
print("Sentinel scanning LinkedIn/AngelList/Glassdoor datasets...")
leads = get_leads()

if not leads:
    print("Vault Empty: No firms currently matching the 'Freelance/Advisory' triggers.")
else:
    print(f"Targets Acquired: {len(leads)}. Uploading top 8 to Command Center...")
    for lead in leads[:8]:
        company_name = lead.get('organization', {}).get('name', 'Global Venture')
        print(f"Analyzing {company_name}...")
        
        email_strategy = draft_strategy(lead)
        
        try:
            db.collection("sentinel_leads").add({
                "name": lead['name'],
                "company": company_name,
                "email": lead.get('email', ''),
                "draft": email_strategy,
                "service_tag": "Boutique Advisory",  # Categorizes the work for you
                # Feature 4: Lead Status Tracking fields
                "status": "new",                     # new | contacted | qualified | proposal_sent | converted | rejected
                "pipeline_stage": "discovery",       # discovery | outreach | proposal | negotiation | closed
                "notes": "",                         # Free-text notes / interaction log
                "last_contacted": None,              # Populated by outreach.py on first send
                "conversion_value": 0,               # USD value assigned when status → converted
                "email_status": "pending",           # pending | sent | failed | skipped (set by outreach.py)
                "timestamp": firestore.SERVER_TIMESTAMP  # Fixed: SERVER_VALUE is not valid; use SERVER_TIMESTAMP
            })
            print(f"DATA SECURED: {lead['name']} is live in the Command Center.")
        except Exception as e:
            print(f"Firestore Write Error for {lead['name']}: {e}")
