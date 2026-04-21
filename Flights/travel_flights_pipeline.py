# travel_flights_pipeline.py

import os, json, ast, re, time
from dotenv import load_dotenv
from serpapi import GoogleSearch
from anthropic import Anthropic

# --------------------------------------------------
# 1. SETUP
# --------------------------------------------------
load_dotenv()

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
client = Anthropic(api_key=CLAUDE_API_KEY)


# --------------------------------------------------
# 2. HELPERS
# --------------------------------------------------
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


# --------------------------------------------------
# 3. LLM: Generate Search Parameters
# --------------------------------------------------
def get_flight_request(user_input):
    try:
        with open("flights/prompts/flights_request_gen_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        print("flights_request_gen_prompt.txt not found")
        return None

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}]
    )

    raw = response.content[0].text.strip()
    return safe_parse(raw)

# --------------------------------------------------
# 4. API CALL: Generic Fetch
# --------------------------------------------------
def fetch_flights(params, filename):
    params["api_key"] = SERPAPI_KEY
    # print("Search Parameters: \n" + json.dumps(params, indent=2, ensure_ascii=False))

    search = GoogleSearch(params)
    data = search.get_dict()

    os.makedirs("Flights/JSONs", exist_ok=True)
    with open(f"Flights/JSONs/{filename}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Saved {filename}.json with {len(data)} best flights.")
    return data


# --------------------------------------------------
# 5. LLM: Choose Best Flights
# --------------------------------------------------
def top_flights(flights_list, preferences, top_n=1, return_full_data=False):
    """
    LLM selects top flights with optional full data return.
    """
    if not flights_list:
        return []

    with open("flights/prompts/flights_prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    user_input = f"Here is the list of flights: {json.dumps(flights_list, ensure_ascii=False)}\n"
    user_input += f"User preferences: {preferences}\n"
    user_input += f"Please select the top {top_n} flights."

    if return_full_data:
        user_input += " Include all original fields in the output, do not remove anything. Only add a 'reason' field."
    else:
        user_input += " Return only essential fields needed for further processing (like departure_token or booking_token)."

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}]
    )

    raw = response.content[0].text.strip()
    parsed = safe_parse(raw)

    # Always return a list
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        # If LLM wrapped results in {'final_flights': [...]}, unwrap
        return parsed.get("final_flights", [parsed])
    return []


# --------------------------------------------------
# 6. DATA CLEANING: Reduce Payload for LLM
# --------------------------------------------------

def clean_flight_data_for_llm(serpapi_response, keep_fields=None):
    """
    Reduce flight data payload for LLM by keeping only important fields.
    
    Args:
        serpapi_response (dict): Raw response from SerpAPI.
        keep_fields (list): List of top-level or leg-level fields to always keep (tokens, IDs, logos, etc.).
        
    Returns:
        list: Cleaned list of flight itineraries suitable for LLM input.
    """
    if keep_fields is None:
        keep_fields = ["departure_token", "booking_token", "airline_logo"]
    
    flights_data = serpapi_response.get("other_flights", [])
    cleaned = []

    for flight in flights_data:
        new_flight = {}

        # Keep essential top-level fields
        for key in ["total_duration", "price", "type", "layovers", "carbon_emissions"] + keep_fields:
            if key in flight:
                new_flight[key] = flight[key]

        # Keep minimal info for each flight leg
        new_flight["flights"] = []
        for leg in flight.get("flights", []):
            minimal_leg = {}
            for k in ["airline", "flight_number", "departure_airport", "arrival_airport",
                      "duration", "travel_class", "airplane", "often_delayed_by_over_30_min"] + keep_fields:
                if k in leg:
                    minimal_leg[k] = leg[k]
            new_flight["flights"].append(minimal_leg)

        cleaned.append(new_flight)

    return cleaned

def run_flights(user_text):
    start = time.time()
    
    # ---- PHASE 1: Outbound Flights ----
    print("🔹 Phase 1: Fetch outbound flights")
    try:
        base_params = get_flight_request(user_text)
        if not base_params:
            raise ValueError("Failed to get flight request parameters")
    except Exception as e:
        print(f"❌ Error in generating flight request: {e}")
        return None

    try:
        outbound_data = fetch_flights(base_params, "outbound")
        cleaned_outbound = clean_flight_data_for_llm(outbound_data, keep_fields=["departure_token"])
        top_outbounds_wrapped = top_flights(cleaned_outbound, user_text, top_n=1, return_full_data=False)
        if not top_outbounds_wrapped:
            raise ValueError("No outbound flights selected by LLM")
    except Exception as e:
        print(f"❌ Error fetching or selecting outbound flights: {e}")
        return None

    # Unwrap 'final_flights' safely
    try:
        top_outbounds = top_outbounds_wrapped
        if isinstance(top_outbounds_wrapped, list) and len(top_outbounds_wrapped) == 1:
            item = top_outbounds_wrapped[0]
            if isinstance(item, dict) and "final_flights" in item:
                top_outbounds = item["final_flights"]

        if not top_outbounds:
            raise ValueError("No outbound flights found after unwrapping 'final_flights'")

        chosen_outbound = top_outbounds[0]
        dep_token = chosen_outbound.get("departure_token")
        if not dep_token:
            raise ValueError("No departure_token found in outbound flight")
    except Exception as e:
        print(f"❌ Error processing outbound flight data: {e}")
        return None

    # ---- PHASE 2: Return Flights ----
    print("\n🔹 Phase 2: Fetch return flights")
    try:
        return_params = dict(base_params)
        return_params["departure_token"] = dep_token

        return_data = fetch_flights(return_params, "return")
        cleaned_return = clean_flight_data_for_llm(return_data, keep_fields=["booking_token"])
        top_returns_wrapped = top_flights(cleaned_return, user_text, top_n=1, return_full_data=False)
        if not top_returns_wrapped:
            raise ValueError("No return flights selected by LLM")
    except Exception as e:
        print(f"❌ Error fetching or selecting return flights: {e}")
        return None

    # Unwrap return flights safely
    try:
        top_returns = top_returns_wrapped
        if isinstance(top_returns_wrapped, list) and len(top_returns_wrapped) == 1:
            item = top_returns_wrapped[0]
            if isinstance(item, dict) and "final_flights" in item:
                top_returns = item["final_flights"]

        if not top_returns:
            raise ValueError("No return flights found after unwrapping 'final_flights'")

        chosen_return = top_returns[0]
        booking_token = chosen_return.get("booking_token")
        if not booking_token:
            raise ValueError("No booking_token found in return flight")
    except Exception as e:
        print(f"❌ Error processing return flight data: {e}")
        return None

    # ---- PHASE 3: Booking Flights ----
    print("\n🔹 Phase 3: Fetch booking details")
    try:
        booking_params = dict(base_params)
        booking_params["booking_token"] = booking_token

        booking_data = fetch_flights(booking_params, "booking")
    except Exception as e:
        print(f"❌ Error fetching booking data: {e}")
        return None

    print(f"\n✅ Finished full round-trip flow in {time.time() - start:.2f}s")
    return booking_data
