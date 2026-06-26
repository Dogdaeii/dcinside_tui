import requests
from bs4 import BeautifulSoup
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Referer": "https://gall.dcinside.com/"
}
url = "https://gall.dcinside.com/mgallery/board/view/?id=running&no=499158"

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

form = soup.find('form', id='comment_write')
if form:
    inputs = form.find_all('input')
    for i in inputs:
        print(i.get('name'), i.get('value'))
else:
    print("Form not found")

print("Checking for block_key in script tags...")
for script in soup.find_all('script'):
    if script.string and '_bnt_st' in script.string:
        print("Found bnt_st script!")
        
