import requests

url = "http://127.0.0.1:8000/chat"
payload = {
    "profile_id": "athlete_test_user",
    "message": "Give me a solid high-protein routine for a full body plan."
}

print("Sending test request to LangGraph Orchestrator...")
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(response.json())
except Exception as e:
    print(f"Connection failed: {e}")