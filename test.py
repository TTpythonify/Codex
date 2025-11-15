import requests

piston_url = "http://localhost:2000"  # your Piston container port mapped to host
try:
    r = requests.get(piston_url)
    print(r.status_code)
    print(r.text[:500])  # prints the first 500 chars
except Exception as e:
    print("Error:", e)
