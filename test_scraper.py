import requests
from bs4 import BeautifulSoup

url = "https://gall.dcinside.com/mgallery/board/lists/?id=thesingularity"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

post_id = "1226921"
post_url = f"https://gall.dcinside.com/mgallery/board/view/?id=thesingularity&no={post_id}"

response = requests.get(post_url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

content_elem = soup.select_one('.write_div')
content = content_elem.get_text(separator='\n', strip=True) if content_elem else "No content"

print(f"Content length: {len(content)}")
print(content[:500])
