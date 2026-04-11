import os
import requests
import google.generativeai as genai

# 1. CONFIGURATION: Setting up the AI (Tushar's Digital Strategy)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# 2. THE HUNTER: Searching for Decision Makers in UK/UAE/US
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        "q_keywords": "General Counsel, India Entry, FDI Strategy, Compliance",
        "locations": ["United Kingdom", "United Arab Emirates", "United States"],
        "person_titles": ["General Counsel", "Chief Legal Officer", "Managing Director", "Founder"],
        "organization_num_employees_ranges": ["500,10000"] # Target mid-to-large firms with retainer budgets
    }
    try:
        response = requests.post(url, json=data)
        return response.json().get('people', [])
    except Exception as e:
        print(f"Error fetching leads: {e}")
        return []

# 3. THE COUNSEL: Drafting the Retainer-First Pitch
def draft_candid_email(lead):
    company = lead.get('organization', {}).get('name', 'your firm')
    industry = lead.get('organization', {}).get('industry', 'International Business')
    
    prompt = f"""
    Draft a high-end, candid cold email for Tushar Nair, a Supreme Court Advocate. 
    Recipient: {lead['name']}, Company: {company}, Sector: {industry}.
    
    TONE: Confident, peer-to-peer, elite, non-salesy. Avoid 'Hope you are well'.
    
    STRATEGIC CONTEXT (2026):
    - Mention the April 1st, 2026 Electricity Rule 3 substitution (for Energy/Infra firms).
    - Mention the March 25, 2026 FCRA Amendment Bill (for Foundations/NGOs).
    - For others: Mention the May 1st India-UK FTA implementation risk.
    
    THE PITCH (Retainer Focus):
    - Offer a 'Structural Resilience Retainer' for ongoing Indian governance. 
    - Position as 'External General Counsel' for their Indian assets.
    - Mention Supreme Court pedigree and direct access via 'The Big Dinner' network.
    
    CALL TO ACTION:
    - Invite to a 15-minute advisory briefing or 'The Big Dinner' in London/Dubai.
    - Calendar Link: https://calendly.com/tusharnair/15min
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Drafting error: {e}"

# 4. EXECUTION: Run the daily scan
leads = get_leads()
if not leads:
    print("No high-value leads found today. System checking for broader criteria tomorrow.")
else:
    for lead in leads[:5]: # Processes the top 5 strategic leads daily
        print(f"\n--- STRATEGIC DRAFT FOR: {lead['name']} ({lead['organization']['name']}) ---")
        print(draft_candid_email(lead))
        print("-" * 50)
