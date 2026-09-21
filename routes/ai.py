#libraries 

from flask import Blueprint, request, jsonify, session
from db import mongo_db
from groq import Groq
import os
import json
import re
from dotenv import load_dotenv


load_dotenv()

ai_bp = Blueprint("ai", __name__)

def get_client():
    return Groq(api_key=os.getenv("GROQ_KEY"))

def ask_ai(prompt):
    client   = get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=4000 )
    return response.choices[0].message.content.strip()

def parse_json(raw):
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Could not parse JSON")

#Full Trip Planner (ai based)
@ai_bp.route("/ai/trip-plan", methods=["POST"])
def trip_plan():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    data        = request.get_json()
    destination = data.get("destination", "")
    days        = data.get("days", 3)
    budget      = data.get("budget", 15000)
    month       = data.get("month", "")
    from_city   = data.get("from_city", "Lahore")
    interests   = data.get("interests", "general sightseeing")

    existing_posts = list(mongo_db["posts"].find(
        {"destination.name": {"$regex": destination, "$options": "i"}},
        {"title": 1, "body": 1, "budget_breakdown": 1}
    ).limit(5))

    community_insights = ""
    if existing_posts:
        community_insights = "\n\nReal traveler experiences from our community:\n"
        for p in existing_posts:
            community_insights += f"- {p.get('title','')}: {p.get('body','')[:150]}\n"
            if p.get("budget_breakdown", {}).get("total"):
                community_insights += f"  Budget spent: {p['budget_breakdown']['total']} PKR\n"

    prompt = f"""You are an expert Pakistani travel planner with deep knowledge of      
local conditions, prices, weather, and routes across Pakistan.

Trip Details:
- Destination: {destination}
- Duration: {days} days
- Total Budget: {budget} PKR
- Travel Month: {month}
- Departing From: {from_city}
- Interests: {interests}
{community_insights}

Create a comprehensive realistic trip plan. Consider actual weather, 2025 PKR prices,
best routes, day by day activities, accommodation, food, packing and safety.

Respond ONLY with a valid JSON object. No markdown, no extra text, just raw JSON:
{{
    "destination": "{destination}",
    "duration": "{days} days",
    "travel_month": "{month}",
    "from_city": "{from_city}",
    "weather_summary": "weather description for {month}",
    "weather_suitable": true,
    "best_months": ["April", "May", "September"],
    "route": {{
        "options": [
            {{
                "mode": "Bus",
                "description": "route description",
                "duration": "travel time",
                "cost_pkr": 2000
            }}
        ],
        "recommended": "recommended option"
    }},
    "budget_breakdown": {{
        "total": {budget},
        "transport": 3000,
        "accommodation": 5000,
        "food": 3000,
        "activities": 2000,
        "misc": 2000,
        "notes": "budget saving tips"
    }},
    "itinerary": [
        {{
            "day": 1,
            "title": "Arrival Day",
            "morning": "morning activities",
            "afternoon": "afternoon activities",
            "evening": "evening activities",
            "accommodation": "hotel name",
            "estimated_cost": 3000
        }}
    ],
    "accommodation": [
        {{
            "name": "hotel name",
            "type": "guest house",
            "price_per_night_pkr": 2000,
            "rating": "good",
            "notes": "any notes"
        }}
    ],
    "food": [
        {{
            "dish": "dish name",
            "where": "restaurant name",
            "price_pkr": 500
        }}
    ],
    "packing_list": {{
        "clothing": ["warm jacket", "trekking boots"],
        "gear": ["camera", "power bank"],
        "documents": ["CNIC", "permit if needed"],
        "medicines": ["altitude sickness pills"]
    }},
    "safety_tips": ["tip1", "tip2"],
    "permits_required": ["any permit"],
    "emergency_contacts": {{
        "rescue": "1122",
        "police": "15",
        "hospital": "local hospital"
    }},
    "community_tips": "{len(existing_posts)} travelers from Velora visited this destination"
}}"""

    try:
        raw    = ask_ai(prompt)
        result = parse_json(raw)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# AI Analysis of Post
@ai_bp.route("/ai/analyze-post", methods=["POST"])
def analyze_post():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    data  = request.get_json()
    title = data.get("title", "")
    body  = data.get("body", "")
    dest  = data.get("destination", "")

    prompt = f"""Analyze this travel post and return ONLY a JSON object, no extra text:

Title: {title}
Destination: {dest}
Description: {body}

Return this exact JSON:
{{
    "summary": "2-3 sentence summary",
    "tags": ["tag1", "tag2", "tag3"],
    "budget_category": "budget OR mid-range OR luxury",
    "highlights": ["highlight1", "highlight2"],
    "tip": "one practical travel tip"
}}"""

    try:
        raw    = ask_ai(prompt)
        result = parse_json(raw)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#Budget Estimator
@ai_bp.route("/ai/estimate-budget", methods=["POST"])
def estimate_budget():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    data        = request.get_json()
    destination = data.get("destination", "")
    days        = data.get("days", 3)

    posts = list(mongo_db["posts"].find(
        {"destination.name": {"$regex": destination, "$options": "i"}},
        {"budget_breakdown": 1}
    ).limit(5))

    budget_data = [
        str(p["budget_breakdown"]["total"])
        for p in posts
        if p.get("budget_breakdown", {}).get("total")
    ]

    context = f"Real budgets from Velora travelers: {', '.join(budget_data)} PKR" \
        if budget_data else "No existing budget data yet."

    prompt = f"""You are a Pakistan travel budget expert.
Estimate a realistic budget for a {days}-day trip to {destination}.
{context}

Return ONLY this JSON, no extra text:
{{
    "total_estimate": 15000,
    "currency": "PKR",
    "breakdown": {{
        "transport": 4000,
        "food": 3000,
        "stay": 5000,
        "activities": 2000,
        "misc": 1000
    }},
    "tips": "one money saving tip"
}}"""

    try:
        raw    = ask_ai(prompt)
        result = parse_json(raw)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500