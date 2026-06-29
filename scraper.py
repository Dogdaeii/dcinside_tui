import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

class DCScraper:
    def __init__(self, gallery_id: str, board_type: str = "mgallery"):
        self.gallery_id = gallery_id
        self.board_type = board_type
        if board_type == "board":
            self.base_url = "https://gall.dcinside.com/board"
        elif board_type == "mini":
            self.base_url = "https://gall.dcinside.com/mini/board"
        else:
            self.base_url = "https://gall.dcinside.com/mgallery/board"
            
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.gallery_name = ""

    @staticmethod
    def parse_url(url: str):
        """Parse DCInside URL and return (gallery_id, board_type)."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        gallery_id = qs.get("id", [""])[0]
        
        board_type = "mgallery"
        if "/mini/board" in parsed.path:
            board_type = "mini"
        elif "/mgallery/board" in parsed.path:
            board_type = "mgallery"
        elif "/board" in parsed.path:
            board_type = "board"
            
        return gallery_id, board_type

    def fetch_gallery_info(self) -> str:
        """Fetch and return gallery name."""
        url = f"{self.base_url}/lists/?id={self.gallery_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title else ""
            name = title.split(" - ")[0].replace(" 갤러리", "").strip() if title else self.gallery_id
            self.gallery_name = name
            return name
        except requests.RequestException:
            return self.gallery_id

    def get_post_list(self, page: int = 1, search_type: str = "", keyword: str = "") -> List[Dict]:
        url = f"{self.base_url}/lists/?id={self.gallery_id}&page={page}"
        if search_type and keyword:
            url += f"&s_type={search_type}&s_keyword={keyword}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        posts = []
        trs = soup.select('table.gall_list tbody tr.us-post')
        
        for tr in trs:
            gall_num = tr.select_one('.gall_num')
            if not gall_num or not gall_num.text.strip().isdigit():
                continue
            gall_num = gall_num.text.strip()
            
            tit_elem = tr.select_one('.gall_tit a:not(.reply_numbox)')
            if not tit_elem:
                continue
            
            title = tit_elem.text.strip()
            
            # Comments count
            reply_elem = tr.select_one('.gall_tit a.reply_numbox .reply_num')
            comments = reply_elem.text.strip() if reply_elem else ""
            
            writer_elem = tr.select_one('.gall_writer')
            writer = writer_elem.get('data-nick', writer_elem.text.strip()) if writer_elem else "Unknown"
            
            date_elem = tr.select_one('.gall_date')
            date = date_elem.get('title', date_elem.text.strip()) if date_elem else ""
            
            count_elem = tr.select_one('.gall_count')
            views = count_elem.text.strip() if count_elem else "0"
            
            recommend_elem = tr.select_one('.gall_recommend')
            recommends = recommend_elem.text.strip() if recommend_elem else "0"
            
            posts.append({
                "id": gall_num,
                "title": title,
                "comments": comments,
                "writer": writer,
                "date": date,
                "views": views,
                "recommends": recommends
            })
            
        return posts

    def get_post_content(self, post_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/view/?id={self.gallery_id}&no={post_id}"
        
        # Need a session to persist cookies if any, though regular requests might work.
        session = requests.Session()
        try:
            response = session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_elem = soup.select_one('.write_div')
        if not content_elem:
            return None
            
        # Clean up scripts
        for script in content_elem.select('script'):
            script.decompose()
            
        # Extract images
        for img in content_elem.select('img'):
            src = img.get('data-original') or img.get('src')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://gall.dcinside.com' + src
                # Use Markdown link syntax
                img.replace_with(f"\n[📷 이미지 보기]({src})\n")
                
        # Extract videos
        for video in content_elem.select('video'):
            source = video.select_one('source')
            src = source.get('src') if source else video.get('src')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                video.replace_with(f"\n[🎥 영상/움짤 보기]({src})\n")

        # Extract iframes (youtube etc)
        for iframe in content_elem.select('iframe'):
            src = iframe.get('src')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                iframe.replace_with(f"\n[🔗 외부 링크 보기]({src})\n")

        # Extract regular links. Some terminals keep the mouse cursor as an
        # I-beam, so make links visually explicit inside the text itself.
        for anchor in content_elem.select('a[href]'):
            href = anchor.get('href')
            if not href:
                continue
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://gall.dcinside.com' + href

            label = anchor.get_text(' ', strip=True) or '링크 열기'
            if label == href:
                label = '링크 열기'
            anchor.replace_with(f"\n[↗ {label}]({href})\n")
                
        content = content_elem.get_text(separator='\n\n', strip=True)
        
        # Fetch comments
        import re
        import json
        e_s_n_o_match = re.search(r'id="e_s_n_o"\s+name="e_s_n_o"\s+value="([^"]+)"', response.text)
        if e_s_n_o_match:
            e_s_n_o = e_s_n_o_match.group(1)
            comment_url = "https://gall.dcinside.com/board/comment/"
            data = {
                "id": self.gallery_id,
                "no": post_id,
                "cmt_id": self.gallery_id,
                "cmt_no": post_id,
                "focus_cno": "",
                "focus_pno": "",
                "e_s_n_o": e_s_n_o,
                "client_id": "1", 
                "cpage": "1"
            }
            post_headers = self.headers.copy()
            post_headers["X-Requested-With"] = "XMLHttpRequest"
            try:
                resp = session.post(comment_url, data=data, headers=post_headers, timeout=10)
                cmt_data = json.loads(resp.text)
                if cmt_data and "comments" in cmt_data and cmt_data["comments"]:
                    content += "\n\n---\n### 댓글\n"
                    for cmt in cmt_data["comments"]:
                        if not cmt.get("name"): # skip deleted or empty
                            continue
                        # If depth > 0, it's a reply
                        prefix = "    └ " if cmt.get("depth", 0) > 0 else ""
                        name = cmt.get("name", "Unknown")
                        memo = cmt.get("memo", "")
                        date = cmt.get("reg_date", "")
                        content += f"{prefix}**{name}** ({date}): {memo}\n\n"
            except Exception:
                pass
        
        return {
            "id": post_id,
            "url": url,
            "content": content
        }
