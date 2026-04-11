import os
import requests
import google.generativeai as genai

# 1. THE BRAIN: Tells Gemini to think like Tushar Nair (Supreme Court Advocate)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# 2. THE HUNTER: Searches for UK/UAE Energy & NGO firms expanding in India
def get_leads():
    url = "https://api.apollo.io/v1/mixed_people/search"
    data = {
        "api_key": os.environ["APOLLO_API_KEY"],
        "q_keywords": "General Counsel, India Entry, Compliance",
        "locations": ["United Kingdom", "United Arab Emirates", "United States"],
        "person_titles": ["CEO", "General Counsel", "Managing Director"]
    }
    return requests.post(url, json=data).json().get('people', [])

# 3. THE COUNSEL: Drafts the candid, elite email
def draft_email(lead):
    company = lead.get('organization', {}).get('name', 'your company')
    industry = lead.get('organization', {}).get('industry', 'International Business')
    
    prompt = f"""
    Draft a cold email for Tushar Nair (Supreme Court Advocate). 
    Recipient: {lead['name']}, Company: {company}, Sector: {industry}.
    
    TONE: Candid, elite, authoritative. 
    STRATEGY: 
    - For Energy: Mention the April 1st, 2026 Electricity Rule 3 changes regarding 'Subsidiary Consolidation' risks.
    - For NGOs: Mention the March 25, 2026 FCRA Bill and the 'Designated Authority' asset-seizure powers.
    - Positioning: Reference 'The Big Dinner' (elite networking) and Supreme Court practice.
    - CTA: 15-min briefing link: https://calendly.com/tusharnair/15min
    """
    response = model.generate_content(prompt)
    return response.text

# 4. EXECUTION
leads = get_leads()
for lead in leads[:3]: # Processes 3 high-quality leads daily
    print(f"--- DRAFT FOR {lead['name']} AT {lead['organization']['name']} ---")
    print(draft_email(lead))
