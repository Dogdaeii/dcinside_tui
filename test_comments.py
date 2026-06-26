import requests
from bs4 import BeautifulSoup

url = "https://gall.dcinside.com/mgallery/board/view/?id=thesingularity&no=1226921"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": url
}

session = requests.Session()
response = session.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

import re
print("Response length:", len(response.text))
if len(response.text) < 1000:
    print("Response text:", response.text)
e_s_n_o_match = re.search(r'id="e_s_n_o"\s+name="e_s_n_o"\s+value="([^"]+)"', response.text)
if e_s_n_o_match:
    e_s_n_o = e_s_n_o_match.group(1)
    print("Found e_s_n_o via regex:", e_s_n_o)
else:
    print("e_s_n_o not found")
    exit()

# Now let's try to fetch comments
comment_url = "https://gall.dcinside.com/board/comment/"
data = {
    "id": "thesingularity",
    "no": "1226921",
    "cmt_id": "thesingularity",
    "cmt_no": "1226921",
    "focus_cno": "",
    "focus_pno": "",
    "e_s_n_o": e_s_n_o,
    "client_id": "1", 
    "cpage": "1"
}

post_headers = headers.copy()
post_headers["X-Requested-With"] = "XMLHttpRequest"
resp = session.post(comment_url, data=data, headers=post_headers)
print("Comment response status:", resp.status_code)
import json
try:
    print("Comment response keys:", json.loads(resp.text).keys())
    print("Comment data:", json.dumps(json.loads(resp.text), ensure_ascii=False)[:500])
except Exception as e:
    print("Not JSON:", resp.text[:500])
