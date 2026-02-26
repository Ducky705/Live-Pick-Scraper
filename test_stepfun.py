import os
import requests
import json

def test_stepfun():
    api_key = os.getenv("OPENROUTER_API_KEY")
    prompt = """
You are an expert sports betting analyst. Extract all sports picks from this message context and output JSON.

Rules:
- Output {"picks": [ { "capper_name", "sport", "bet_type", "selection", "line", "odds", "units" } ] }
- Extract every single pick.
- For parlays, try to separate the legs if possible or combine them into Bet Type "Parlay".

Message ID: 2022722061203050528
Text:
#Porterpicks College bb 🏀🚀

Iowa state -7
Samford +4(buying 1/2) 
Miss valley +17(buying 1/2)
Vandy/Auburn o143.5
Florida a&m/ Alabama St o138

#Betsharper 

Clemson +13.5
Florida/Georgia o158.5
Seton  Hall+10.5
Michigan/South Carolina o152.5
    """

    payload = {
        "model": "stepfun/step-3.5-flash:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-scraper.local",
        "X-Title": "CapperSuite",
    }
    
    print("Requesting StepFun...")
    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
    
    print("Status:", resp.status_code)
    try:
        j = resp.json()
        if "choices" in j:
            print(j["choices"][0]["message"]["content"])
        else:
            print(j)
    except:
        print(resp.text)

if __name__ == "__main__":
    test_stepfun()
