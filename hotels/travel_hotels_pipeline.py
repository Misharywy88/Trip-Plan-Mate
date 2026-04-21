# travel_hotels_pipeline.py

import os, json, ast, re
from dotenv import load_dotenv
from serpapi import GoogleSearch
from anthropic import Anthropic

# --------------------------------------------------------------------
# 1. SETUP
# --------------------------------------------------------------------
load_dotenv()

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

client = Anthropic(api_key=CLAUDE_API_KEY)


# --------------------------------------------------------------------
# 2. HELPER — GENERIC SAFE PARSER
# --------------------------------------------------------------------
def safe_parse(text):
    """Tries to safely parse stringified Python or JSON data."""
    if not isinstance(text, str):
        return text

    s = text.strip()
    if s.startswith("params"):
        s = s.split("=", 1)[1].strip()

    for parser in (ast.literal_eval, json.loads):
        try:
            return parser(s)
        except Exception:
            continue

    m = re.search(r'(\{.*\}|\[.*\])', s, re.DOTALL)
    if m:
        content = m.group(1)
        for parser in (ast.literal_eval, json.loads):
            try:
                return parser(content)
            except Exception:
                continue

    return None


# --------------------------------------------------------------------
# 3. LLM FUNCTION — GENERATE SEARCH PARAMETERS
# --------------------------------------------------------------------
def get_hotel_request(user_input):
    try:
        with open("hotels/prompts/hotels_request_gen_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        print("hotels_request_gen_prompt.txt not found")
        return None

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}]
    )

    raw = response.content[0].text.strip()
    return safe_parse(raw)


# --------------------------------------------------------------------
# 4. FETCH HOTELS FROM SERPAPI
# --------------------------------------------------------------------
def fetch_hotels(params):
    params["api_key"] = SERPAPI_KEY
    search = GoogleSearch(params)
    allHotelsData = search.get_dict()

    with open("hotels/JSONs/hotels.json", "w", encoding="utf-8") as f:
        json.dump(allHotelsData, f, indent=2)

    clean_hotels = []
    for hotel in allHotelsData.get("properties", []):
        clean_hotels.append({
            "id": hotel.get("property_token"),
            "name": hotel.get("name"),
            "price": hotel.get("rate_per_night", {}).get("extracted_lowest"),
            "stars": hotel.get("extracted_hotel_class"),
            "rating": hotel.get("overall_rating"),
            "reviews": hotel.get("reviews"),
            "location_rating": hotel.get("location_rating"),
            "coordinates": hotel.get("gps_coordinates"),
            "amenities": hotel.get("amenities", []),
            "link": hotel.get("link"),
            "sponsored": hotel.get("sponsored")
        })

    with open("hotels/JSONs/hotels_filtered.json", "w", encoding="utf-8") as f:
        json.dump(clean_hotels, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(clean_hotels)} hotels to hotels_filtered.json")
    return clean_hotels, allHotelsData


# --------------------------------------------------------------------
# 5. LLM FUNCTION — SELECT BEST HOTELS
# --------------------------------------------------------------------
def top_hotels(hotels, preferences, top_n=5):
    try:
        with open("hotels/prompts/top_hotels_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        print("top_hotels_prompt.txt not found")
        return []

    user_input = (
        f"Here is the list of hotels: {json.dumps(hotels, ensure_ascii=False)}\n"
        f"User preferences: {preferences}\n"
        f"Please select the top {top_n} hotels that best match these preferences "
        f"and return only a Python dictionary in the specified format."
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}]
    )

    raw = response.content[0].text.strip()
    parsed = safe_parse(raw)

    if isinstance(parsed, dict) and "top_hotels" in parsed:
        return parsed["top_hotels"]
    elif isinstance(parsed, list):
        return parsed
    else:
        print("Failed to parse LLM output.")
        print(raw)
        return []



# --------------------------------------------------------------------
# 6. RUNNER FUNCTION
# --------------------------------------------------------------------

def run_hotels(user_text: str):
    print("🔹 Generating search parameters...")
    params = get_hotel_request(user_text)
    if not params:
        raise SystemExit("❌ Failed to generate search parameters.")

    # If params is a string, try to convert it to a dict safely
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = ast.literal_eval(params)

    os.makedirs("hotels/JSONs", exist_ok=True)
    with open("hotels/JSONs/hotel_params.json", "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)
        
    print("✅ Hotel parameters saved to hotels/JSONs/hotel_params.json")

    # Fetch hotels from Google Hotels API
    print("\n🔹 Fetching hotel results from Google Hotels...")
    hotelsEssentialDetails, hotelsFullData = fetch_hotels(params)
    
    if not hotelsEssentialDetails:
        raise SystemExit("❌ No hotels found in API response.")

    # Ask LLM to pick top matches
    print("\n🔹 Selecting best hotels using LLM...")
    topHotels = top_hotels(hotelsEssentialDetails, user_text)
    if not topHotels:
        raise SystemExit("❌ Failed to get best hotels from LLM.")

    # Match top hotels to their detailed info (use hotelsEssentialDetails which is the list of cleaned hotels)
    top_ids = {th.get("id") for th in topHotels if th.get("id")}
    
    # Extract the IDs of the top hotels
    top_ids = {th.get("id") for th in topHotels if th.get("id")}

    # Filter the full hotel properties
    topHotelsFullDetails = [
        prop
        for prop in hotelsFullData.get("properties", [])
        if prop.get("property_token") in top_ids
    ]

    # if topHotelsFullDetails:
    #     print(json.dumps(topHotelsFullDetails[0], indent=2, ensure_ascii=False))

    return topHotelsFullDetails
    