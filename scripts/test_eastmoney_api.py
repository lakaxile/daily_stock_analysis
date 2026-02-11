import requests
import json

def test_url(name, fs_param):
    url = "http://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": 20,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f62",
        "fs": fs_param,
        "fields": "f12,f14,f3,f62"
    }
    print(f"Testing {name} with fs={fs_param}...")
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if data.get('data') and data['data'].get('diff'):
            print(f"✅ Success! Found {len(data['data']['diff'])} items.")
            print(data['data']['diff'][:2])
            return True
        else:
            print(f"❌ Failed. Response: {str(data)[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    return False

# Patterns to test for "Stocks in Block BK0478"
patterns = [
    "b:BK0478",
    "b:BK0478+f:!50",
    "b:BK0478+f:!50+f:!60",  # Sometimes verified
    "m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2+b:BK0478",  # Complex filter
]

for p in patterns:
    if test_url(p, p):
        break
