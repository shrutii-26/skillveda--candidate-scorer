import json
from openai import OpenAI
import config

client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)

KNOWN_LOCATIONS = [
    "bangalore",
    "chennai",
    "delhi ncr",
    "gurgaon",
    "hyderabad",
    "kolkata",
    "mumbai",
    "noida",
    "pune",
    "remote",
]

KNOWN_INDUSTRIES = [
    "computer software",
    "consumer goods",
    "e-learning",
    "financial services",
    "hospital & health care",
    "information technology and services",
    "insurance",
    "internet",
    "logistics and supply chain",
    "management consulting",
    "marketing and advertising",
    "real estate",
    "retail",
    "telecommunications",
]

SYSTEM_PROMPT = f"""You are a recruitment assistant. Convert a plain-English hiring \
requirement into structured JSON.

Output ONLY valid JSON — no markdown fences, no explanation, nothing else.

Schema:
{{
  "title": "<best single job title>",
  "min_experience": <integer or null>,
  "industries": [<lowercase strings>],
  "locations": [<lowercase strings>],
  "skills": [<lowercase strings>]
}}

Rules:
- title: one job title string
- min_experience: years number if mentioned, else null
- industries: map to closest from: {json.dumps(KNOWN_INDUSTRIES)}. "fintech" → "financial services". Empty list if not mentioned.
- locations: map to closest from: {json.dumps(KNOWN_LOCATIONS)}. "Delhi"/"New Delhi" → "delhi ncr". "Bengaluru" → "bangalore". Empty list if not mentioned.
- skills: lowercase list of tools, technologies, domain keywords. Empty list if none mentioned.
"""


def parse_requirement(requirement: str) -> dict:
    response = client.chat.completions.create(
        model=config.GROQ_MODEL_STRONG,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": requirement},
        ],
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    parsed = json.loads(raw)
    parsed.setdefault("title", "")
    parsed.setdefault("min_experience", None)
    parsed.setdefault("industries", [])
    parsed.setdefault("locations", [])
    parsed.setdefault("skills", [])
    parsed["title"] = parsed["title"].lower().strip()
    parsed["industries"] = [i.lower().strip() for i in parsed["industries"]]
    parsed["locations"] = [l.lower().strip() for l in parsed["locations"]]
    parsed["skills"] = [s.lower().strip() for s in parsed["skills"]]
    return parsed
