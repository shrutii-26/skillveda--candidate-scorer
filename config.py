import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GROQ_MODEL_FAST = "llama-3.1-8b-instant"
GROQ_MODEL_STRONG = "llama-3.1-8b-instant"

SHORTLIST_SIZE = 50
TOP_N = 20
MIN_SCORE_THRESHOLD = 50  # show more candidates if fewer than TOP_N score above this
MIN_RETRIEVAL_SCORE = 0.10
BROADENING_THRESHOLD = 10
