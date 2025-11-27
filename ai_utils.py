import requests
import re
from collections import Counter

LLM_URL = "http://192.168.56.1:1234/v1/chat/completions"


# -----------------------------------------------------------
# Local LLM summarizer using llama.cpp / LLM-Studio
# -----------------------------------------------------------

def advanced_ai_summary(text, min_length=30, max_length=120):
    if len(text) < 100:
        return "Text too short to summarize."

    prompt = f"""
Summarize the following text clearly and concisely.
Aim for {min_length}-{max_length} words.

Text:
{text}
"""

    payload = {
        "model": "qwen2.5-coder-14b",   # matches your local model name
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 512
    }

    try:
        response = requests.post(LLM_URL, json=payload)
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"Error contacting local LLM: {e}"


# -----------------------------------------------------------
# Sentiment analysis (lightweight)
# -----------------------------------------------------------

positive_words = {"good", "great", "excellent", "positive", "happy", "success", "benefit"}
negative_words = {"bad", "terrible", "sad", "negative", "failure", "harm", "angry"}

def sentiment_weight(text):
    words = re.findall(r"\b\w+\b", text.lower())
    score = 0
    for w in words:
        if w in positive_words:
            score += 1
        elif w in negative_words:
            score -= 1
    return score

def sentiment_details(text):
    score = sentiment_weight(text)
    if score > 3:
        mood = "Strongly Positive"
    elif score > 0:
        mood = "Positive"
    elif score == 0:
        mood = "Neutral"
    elif score > -3:
        mood = "Negative"
    else:
        mood = "Strongly Negative"
    return f"{mood} (score {score})"


# -----------------------------------------------------------
# Keyword extraction (GUI uses this)
# -----------------------------------------------------------

def keyword_density(text, top_n=5):
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    freq = Counter(words)
    return [w for w, c in freq.most_common(top_n)]
