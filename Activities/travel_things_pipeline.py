# travel_tripadvisor_pipeline.py

import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    """
    Extremely robust JSON extractor that:
    - Removes markdown code fences
    - Extracts the largest JSON array or object
    - Parses even if Claude adds noise before/after
    """
    if not isinstance(text, str):
        return text

    s = text.strip()

    s = re.sub(r"```(?:json)?", "", s).replace("```", "").strip()

    try:
        return json.loads(s)
    except Exception:
        pass

    arrays = re.findall(r'\[[\s\S]*?]', s, flags=re.MULTILINE)
    if arrays:
        best = max(arrays, key=len)
        try:
            return json.loads(best)
        except Exception:
            pass

    objs = re.findall(r'\{[\s\S]*?}', s, flags=re.MULTILINE)
    if objs:
        best = max(objs, key=len)
        try:
            return json.loads(best)
        except Exception:
            pass

    s2 = re.sub(r",(\s*[\]}])", r"\1", s)
    try:
        return json.loads(s2)
    except:
        pass

    return None


# --------------------------------------------------------------------
# 3. FIX CITY NAME VIA LLM
# --------------------------------------------------------------------
def fix_city_name(user_input):
    try:
        with open("Activities/prompts/fix_city_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        print("fix_city_prompt.txt not found")
        return {"city": user_input}

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}]
    )

    raw = response.content[0].text.strip()
    parsed = safe_parse(raw)
    if parsed and isinstance(parsed, dict) and "city" in parsed:
        return parsed
    return {"city": user_input}

# --------------------------------------------------------------------
# 4. FETCH ACTIVITIES / RESTAURANTS
# --------------------------------------------------------------------
def fetch_tripadvisor(city, ssrc="A", limit=50):
    """ssrc: A=Things to Do, r=Restaurants"""
    params = {
        "engine": "tripadvisor",
        "q": city,
        "ssrc": ssrc,
        "limit": limit,
        "api_key": SERPAPI_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    print(f"Fetched {len(results.get('locations', []))} items for city: {city}, ssrc: {ssrc}")

    return results.get("locations", [])

# --------------------------------------------------------------------
# 5. LLM FUNCTION — SELECT TOP ITEMS
# --------------------------------------------------------------------
def select_top_items(items, preferences, top_n=10):
    try:
        with open("Activities/prompts/top_items_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        print("top_items_prompt.txt not found")
        return []

    # Send strict JSON input to LLM
    user_input = json.dumps({
        "items": items,
        "preferences": preferences,
        "top_n": top_n
    }, ensure_ascii=False)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}]
        )
    except Exception as e:
        print(f"❌ LLM request failed: {e}")
        return []

    raw = response.content[0].text.strip()
    parsed = safe_parse(raw)

   
    if isinstance(parsed, list):
        return parsed[:top_n]
    else:
        print("Failed to parse LLM output.")
        return []

# --------------------------------------------------------------------
# 6. WORKER FUNCTIONS FOR THREADS
# --------------------------------------------------------------------
def process_activities(city, user_percentages):
    activities = fetch_tripadvisor(city, ssrc="A", limit=50)
    if not activities:
        return []
    return select_top_items(activities, user_percentages, top_n=3)

def process_restaurants(city, user_percentages):
    restaurants = fetch_tripadvisor(city, ssrc="r", limit=50)
    if not restaurants:
        return []
    return select_top_items(restaurants, user_percentages, top_n=3)

# --------------------------------------------------------------------
# 7. RUNNER FUNCTION — PARALLEL
# --------------------------------------------------------------------
def run_tripadvisor(city_input, user_percentages):
    # Fix city name first
    print("🔹 Fixing city name...")
    city = fix_city_name(city_input).get("city", city_input)
    print(f"✅ City fixed: {city}")

    results = {"activities": [], "restaurants": []}

    # Run activities & restaurants in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(process_activities, city, user_percentages): "activities",
            executor.submit(process_restaurants, city, user_percentages): "restaurants"
        }

        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
                print(f"✅ {key} processed, {len(results[key])} items")
            except Exception as e:
                print(f"❌ Error processing {key}: {e}")
                results[key] = []

    return results

