import json
import sys
import urllib.request
import urllib.error
import os
import time

from farmflow import settings


def generate_farm_plan(farm_data: dict) -> dict:
    """Call Gemini API to generate a complete farm plan."""
    
    prompt = f"""You are an expert agricultural advisor for East African smallholder farmers.

A farmer has provided the following details:
- Name: {farm_data['farmer_name']}
- Location: {farm_data['location']}, Kenya
- Land Size: {farm_data['land_size']} acres
- Crop: {farm_data['crop']}
- Soil Type: {farm_data['soil_type']}
- Season: {farm_data['season']}
- Budget: KES {farm_data['budget']}
- Notes: {farm_data.get('additional_notes', 'None')}

Generate a comprehensive farm plan. Respond ONLY with a valid JSON object (no markdown, no preamble) with exactly these keys:

{{
  "planting_schedule": [
    {{"week": 1, "activity": "Land preparation", "details": "...", "cost_kes": 2000}},
    ...
  ],
  "input_requirements": [
    {{"item": "DAP Fertilizer", "quantity": "50kg", "purpose": "Basal application", "cost_kes": 3500}},
    ...
  ],
  "weather_risks": [
    {{"risk": "Late onset rains", "probability": "Medium", "mitigation": "...", "impact": "High"}},
    ...
  ],
  "purchase_orders": [
    {{"supplier_type": "Agro-dealer", "items": ["DAP 50kg x2", "Certified seed 10kg"], "estimated_total_kes": 8000, "timing": "Week 1", "notes": "..."}},
    ...
  ],
  "ai_summary": "A 3-4 sentence executive summary of the plan, key recommendations, and expected yield/profit outlook."
}}

Be specific to Kenya/East Africa. Use realistic KES prices for 2024. Include 6-10 planting schedule items covering the full season, 5-8 input requirements, 3-5 weather risks, and 2-3 purchase orders.
"""
    
    

    payload = json.dumps({
    "contents": [{
        "parts": [{"text": prompt}]
    }],
    "systemInstruction": {
            "parts": [{
                "text": (
                    "You are a strict JSON generator. You must output a single valid JSON object. "
                    "Never include conversational preamble, markdown blocks, or trailing commas. "
                    "If you include quotes inside a text field value, you must escape them with a backslash (\\\")."
                )
            }]
        },
    "generationConfig": {
        "responseMimeType": "application/json"
    }

    }).encode("utf-8")

  

    # Pick up the Gemini API key from environment variables
    API_KEY = settings.GEMINI_API_KEY
    
    # Gemini API endpoint structure using the state-of-the-art gemini-2.5-flash model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )


    try:
        # CRITICAL FIX: Set timeout=15 seconds. This breaks any 5-minute endless loading loops!
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(raw)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ Gemini API HTTP Error ({e.code}): {error_body}", file=sys.stderr)
        # Display the real error message on screen
        return {"error": f"Gemini Rejected Request: {error_body}"}

    except Exception as e:
        print(f"❌ System Network Exception: {str(e)}", file=sys.stderr)
        return {"error": f"Failed due to network exception: {str(e)}"}



    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            #raw = data["content"][0]["text"].strip()
            # Extract raw text out of Gemini's specific response tree structure
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Strip markdown fences if present
            
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            
            cleaned_json_string = raw.strip()
            return json.loads(cleaned_json_string)
        
    except json.JSONDecodeError as je:
        # Catch exactly where it failed so you can inspect the raw text if it hits again
        print(f"❌ JSON Parsing failed at line {je.lineno}, col {je.colno}: {je.msg}", file=sys.stderr)
        print(f"📋 Raw text body attempted to parse:\n{raw}", file=sys.stderr)
        return {"error": f"Internal formatting validation error: {je.msg}"}

    except Exception as e:
        print(f"❌ System Exception: {str(e)}", file=sys.stderr)
        return {"error": f"Failed due to system network exception: {str(e)}"}    
   
        # Return structured fallback on error
        return {
            "planting_schedule": [
                {"week": 1, "activity": "Land preparation", "details": "Clear land, plough and harrow to fine tilth", "cost_kes": 3000},
                {"week": 2, "activity": "Soil testing & liming", "details": "Test pH, apply agricultural lime if needed", "cost_kes": 1500},
                {"week": 3, "activity": "Planting", "details": f"Plant {farm_data['crop']} seeds at recommended spacing", "cost_kes": 2000},
                {"week": 5, "activity": "Top dressing", "details": "Apply CAN fertilizer for vegetative growth", "cost_kes": 4000},
                {"week": 8, "activity": "Weeding", "details": "Manual or herbicide weeding", "cost_kes": 2500},
                {"week": 12, "activity": "Pest scouting", "details": "Scout for pests and apply pesticide if threshold exceeded", "cost_kes": 1500},
                {"week": 16, "activity": "Harvesting", "details": "Harvest at optimal maturity for maximum yield", "cost_kes": 3500},
            ],
            "input_requirements": [
                {"item": "Certified Seeds", "quantity": "10kg", "purpose": "Planting material", "cost_kes": 2500},
                {"item": "DAP Fertilizer", "quantity": "50kg", "purpose": "Basal dressing", "cost_kes": 3800},
                {"item": "CAN Fertilizer", "quantity": "50kg", "purpose": "Top dressing", "cost_kes": 3200},
                {"item": "Herbicide", "quantity": "1L", "purpose": "Weed control", "cost_kes": 1200},
                {"item": "Pesticide", "quantity": "500ml", "purpose": "Pest control", "cost_kes": 900},
            ],
            "weather_risks": [
                {"risk": "Drought stress", "probability": "Medium", "mitigation": "Mulch conserve soil moisture, irrigate if possible", "impact": "High"},
                {"risk": "Flooding / waterlogging", "probability": "Low", "mitigation": "Ensure proper drainage channels", "impact": "Medium"},
                {"risk": "Fall Armyworm", "probability": "High", "mitigation": "Scout weekly, apply pesticide at first sign", "impact": "High"},
            ],
            "purchase_orders": [
                {"supplier_type": "Certified Agro-dealer", "items": ["Certified seeds 10kg", "DAP 50kg"], "estimated_total_kes": 6300, "timing": "Week 1", "notes": "Buy only certified/treated seeds"},
                {"supplier_type": "Agro-dealer / Cooperative", "items": ["CAN 50kg", "Herbicide 1L", "Pesticide 500ml"], "estimated_total_kes": 5300, "timing": "Week 4", "notes": "Check for cooperative discounts"},
            ],
            "ai_summary": f"This plan covers a {farm_data['land_size']}-acre {farm_data['crop']} farm in {farm_data['location']} for the {farm_data['season']} season. With a budget of KES {farm_data['budget']}, focus on quality certified seeds and timely fertilizer application. Monitor closely for pests, especially Fall Armyworm. Expected gross income depends on market prices at harvest — link with local cooperatives early for better prices."
        }
