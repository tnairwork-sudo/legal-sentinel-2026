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

# Maximum number of leads to collect and process per run
MAX_LEADS_PER_RUN = 150

# 2. THE MULTI-CHANNEL AGGREGATOR (FIXES 422 ERROR)
def get_leads(keywords=None, locations=None, titles=None, employee_ranges=None):
    """Search Apollo for leads using the given parameters. Returns a list of people."""
    url = "https://api.apollo.io/v1/mixed_people/search"

    q_keywords = keywords or "Contract Drafting, Legal Due Diligence, Document Review, Corporate Advisory, India Expansion, FDI compliance"
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        "q_keywords": q_keywords,
        "locations": locations or ["United Kingdom", "United Arab Emirates", "India", "Singapore", "United States"],
        "person_titles": titles or ["General Counsel", "Founder", "CEO", "Head of Legal", "Operations Director"],
        # Uses standard Apollo strings to prevent 422 errors
        "organization_num_employees_ranges": employee_ranges or ["11-50", "51-200", "201-500", "501-1000"],
        "per_page": 100,
    }

    try:
        response = requests.post(url, json=data)
        if response.status_code != 200:
            print(f"Aggregator Error {response.status_code}: {response.text}")
            return []
        results = response.json().get('people', [])
        print(f"  → Apollo returned {len(results)} results for keywords: {q_keywords[:60]}...")
        return results
    except Exception as e:
        print(f"Network Error: {e}")
        return []


# Search configurations for multi-keyword strategy
SEARCH_CONFIGS = [
    {
        "keywords": "Contract Drafting, Legal Due Diligence, Document Review, Corporate Advisory, India Expansion, FDI compliance",
        "locations": ["United Kingdom", "United Arab Emirates", "India", "Singapore", "United States"],
        "titles": ["General Counsel", "Founder", "CEO", "Head of Legal", "Operations Director"],
        "employee_ranges": None,
    },
    {
        "keywords": "Mergers Acquisitions, Cross Border Transaction, Legal Counsel, Regulatory Compliance, International Trade",
        "locations": ["United Kingdom", "Germany", "France", "Netherlands", "Australia"],
        "titles": ["Chief Legal Officer", "Managing Director", "VP Legal", "Legal Director", "Compliance Officer"],
        "employee_ranges": None,
    },
    {
        "keywords": "Startup Legal, Venture Capital, Term Sheet, Intellectual Property, Licensing Agreement",
        "locations": ["India", "Singapore", "United States", "Canada", "Israel"],
        "titles": ["Founder", "Co-Founder", "CEO", "CTO", "General Counsel"],
        "employee_ranges": None,
    },
    {
        "keywords": "Private Equity, Corporate Restructuring, Due Diligence, M&A Advisory, Investment Agreement",
        "locations": ["United Arab Emirates", "Saudi Arabia", "Qatar", "Bahrain", "Kuwait"],
        "titles": ["Partner", "Managing Partner", "Investment Director", "Chief Executive Officer", "Head of Investments"],
        "employee_ranges": None,
    },
    {
        "keywords": "Employment Law, Labour Compliance, HR Advisory, Workforce Expansion, India Operations",
        "locations": ["India", "United Kingdom", "United States", "Singapore", "South Africa"],
        "titles": ["HR Director", "Chief People Officer", "Operations Director", "Founder", "CEO"],
        "employee_ranges": None,
    },
]

# Fallback broad search used when collected leads total < 100
FALLBACK_CONFIG = {
    "keywords": "Legal Services, Corporate Law, Business Advisory, Compliance, Contract Management",
    "locations": ["United Kingdom", "United Arab Emirates", "India", "Singapore", "United States",
                  "Germany", "France", "Australia", "Canada", "South Africa"],
    "titles": ["CEO", "Founder", "General Counsel", "Managing Director", "Chief Legal Officer",
               "Operations Director", "Compliance Director", "VP Legal", "Head of Legal"],
    "employee_ranges": ["1-10", "11-50", "51-200", "201-500", "501-1000"],
}


def collect_all_leads():
    """Run all search configurations and return a de-duplicated list of up to MAX_LEADS_PER_RUN leads."""
    all_leads = []
    seen_emails = set()

    def add_unique(leads):
        added = 0
        for lead in leads:
            email = lead.get('email', '')
            if email:
                # De-duplicate by email when available
                if email in seen_emails:
                    continue
                seen_emails.add(email)
            # Leads without an email are always included (different people may share a name)
            all_leads.append(lead)
            added += 1
        return added

    print("--- Multi-keyword search starting ---")
    for i, cfg in enumerate(SEARCH_CONFIGS, start=1):
        print(f"[Search {i}/{len(SEARCH_CONFIGS)}] Querying Apollo...")
        leads = get_leads(
            keywords=cfg["keywords"],
            locations=cfg["locations"],
            titles=cfg["titles"],
            employee_ranges=cfg["employee_ranges"],
        )
        added = add_unique(leads)
        print(f"  → {added} new unique leads added (running total: {len(all_leads)})")

    print(f"--- Primary searches complete: {len(all_leads)} unique leads gathered ---")

    # Fallback: if we still have fewer than 100 leads, run a broader search
    if len(all_leads) < 100:
        print(f"Lead count below 100 — triggering broad fallback search...")
        fallback_leads = get_leads(
            keywords=FALLBACK_CONFIG["keywords"],
            locations=FALLBACK_CONFIG["locations"],
            titles=FALLBACK_CONFIG["titles"],
            employee_ranges=FALLBACK_CONFIG["employee_ranges"],
        )
        added = add_unique(fallback_leads)
        print(f"  → Fallback added {added} leads (total now: {len(all_leads)})")

    # Second fallback: ultra-broad search if still below 100
    if len(all_leads) < 100:
        print(f"Still below 100 leads — running ultra-broad fallback...")
        ultra_leads = get_leads(
            keywords="Legal, Law, Counsel, Compliance, Advisory",
            locations=["United Kingdom", "United Arab Emirates", "India", "Singapore",
                       "United States", "Germany", "Australia", "Canada"],
            titles=["CEO", "Founder", "Director", "Manager", "Partner"],
            employee_ranges=["1-10", "11-50", "51-200", "201-500"],
        )
        added = add_unique(ultra_leads)
        print(f"  → Ultra-broad fallback added {added} leads (total now: {len(all_leads)})")

    return all_leads[:MAX_LEADS_PER_RUN]

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
leads = collect_all_leads()

if not leads:
    print("Vault Empty: No firms currently matching the 'Freelance/Advisory' triggers.")
else:
    print(f"Targets Acquired: {len(leads)}. Processing all found leads and uploading to Command Center...")
    secured_count = 0
    for lead in leads[:MAX_LEADS_PER_RUN]:
        # Validate lead quality: must have at least a name
        lead_name = lead.get('name', '').strip()
        if not lead_name:
            continue

        company_name = lead.get('organization', {}).get('name', 'Global Venture')
        print(f"Analyzing {company_name}...")
        
        email_strategy = draft_strategy(lead)
        
        try:
            db.collection("sentinel_leads").add({
                "name": lead_name,
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
            secured_count += 1
            print(f"DATA SECURED: {lead_name} is live in the Command Center.")
        except Exception as e:
            print(f"Firestore Write Error for {lead_name}: {e}")

    print(f"--- Mission Complete: {secured_count} leads secured to vault ---")
    if secured_count < 100:
        print(f"WARNING: Only {secured_count} leads secured today. Apollo API may have returned fewer results than expected.")
