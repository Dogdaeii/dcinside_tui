import json
import os
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Markdown, Static, Input, OptionList, Label
from textual.widgets.option_list import Option
from textual.containers import Container, ScrollableContainer, Vertical
from textual.binding import Binding
from textual.worker import Worker, WorkerState
from textual import work

from scraper import DCScraper

GALLERIES_FILE = "galleries.json"
DEFAULT_GALLERIES = [
    {"name": "특이점이 온다", "id": "thesingularity", "type": "mgallery", "url": "https://gall.dcinside.com/mgallery/board/lists?id=thesingularity"},
    {"name": "러닝 마이너", "id": "running", "type": "mgallery", "url": "https://gall.dcinside.com/mgallery/board/lists?id=running"}
]

def load_galleries():
    if not os.path.exists(GALLERIES_FILE):
        save_galleries(DEFAULT_GALLERIES)
        return DEFAULT_GALLERIES
    try:
        with open(GALLERIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_GALLERIES

def save_galleries(galleries):
    with open(GALLERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(galleries, f, ensure_ascii=False, indent=2)

class GallerySelectScreen(Screen):
    """Screen for selecting or adding a gallery."""
    
    BINDINGS = [
        Binding("q", "app.quit", "Quit")
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="gallery_select_container"):
            yield Label("디시인사이드 갤러리 선택", classes="title")
            yield OptionList(id="gallery_list")
            yield Label("새 갤러리 추가 (주소 또는 ID 입력 후 Enter)", classes="subtitle")
            yield Input(placeholder="예: https://gall.dcinside.com/mgallery/board/lists?id=thesingularity", id="new_gallery_input")
        yield Footer()
        
    def on_mount(self) -> None:
        self.title = "디시인사이드 뷰어"
        self.sub_title = "v1.0.0 | Built by Jaden Lee"
        self.galleries = load_galleries()
        self.update_list()
        self.focus_list()

    def on_screen_resume(self) -> None:
        self.title = "디시인사이드 뷰어"
        self.sub_title = "v1.0.0 | Built by Jaden Lee"
        self.focus_list()

    def focus_list(self) -> None:
        lst = self.query_one("#gallery_list", OptionList)
        lst.focus()
        if lst.option_count > 0 and lst.highlighted is None:
            lst.highlighted = 0
        
    def update_list(self):
        option_list = self.query_one("#gallery_list", OptionList)
        option_list.clear_options()
        for idx, gal in enumerate(self.galleries):
            option_list.add_option(Option(f"{gal['name']} 갤러리 ({gal['id']})", id=str(idx)))
            
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = int(event.option_id)
        selected = self.galleries[idx]
        self.app.switch_to_gallery(selected)

    @work(exclusive=True, thread=True)
    def add_new_gallery(self, url: str):
        # Parse URL
        if "http" not in url:
            gallery_id, board_type = url, "mgallery"
            full_url = f"https://gall.dcinside.com/mgallery/board/lists?id={gallery_id}"
        else:
            gallery_id, board_type = DCScraper.parse_url(url)
            full_url = url
            
        if not gallery_id:
            self.app.call_from_thread(self.app.notify, "유효한 갤러리 주소가 아닙니다.", severity="error")
            return
            
        scraper = DCScraper(gallery_id, board_type)
        name = scraper.fetch_gallery_info()
        
        new_gal = {"name": name, "id": gallery_id, "type": board_type, "url": full_url}
        
        for g in self.galleries:
            if g["id"] == gallery_id and g["type"] == board_type:
                self.app.call_from_thread(self.app.switch_to_gallery, g)
                return
                
        self.galleries.append(new_gal)
        save_galleries(self.galleries)
        
        self.app.call_from_thread(self.update_list)
        self.app.call_from_thread(self.app.switch_to_gallery, new_gal)
        
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "new_gallery_input":
            url = event.value.strip()
            if url:
                self.add_new_gallery(url)
                event.input.value = ""

class PostListScreen(Screen):
    """Main screen for browsing a specific gallery."""
    
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("r", "refresh_list", "Refresh"),
        Binding("/", "search", "Search"),
        Binding("p", "prev", "Prev Page"),
        Binding("n", "next", "Next Page"),
        Binding("escape", "back", "Gallery(Esc)"),
        Binding("b", "back", "Back", show=False),
    ]

    def __init__(self, gallery_info: dict):
        super().__init__()
        self.gallery_info = gallery_info
        self.scraper = DCScraper(gallery_info["id"], gallery_info["type"])
        self.current_post = None
        self.posts_data = []
        self.search_keyword = ""
        self.current_page = 1

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="loading")
        yield Input(placeholder="검색어 입력 후 Enter (제목+내용)", id="search_input")
        yield DataTable(id="post_list")
        with ScrollableContainer(id="post_viewer"):
            yield Static(id="post_header")
            yield Markdown(id="post_content", open_links=False)
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"{self.gallery_info['name']} 갤러리"
        self.sub_title = "v1.0.0 | Built by Jaden Lee"
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("ID", "Title", "Comments", "Writer", "Date", "Views", "Rec")
        
        self.action_refresh_list()

    @work(exclusive=True, thread=True)
    def fetch_posts(self, keyword: str = "", page: int = 1) -> list:
        if keyword:
            return self.scraper.get_post_list(page=page, search_type="search_subject_memo", keyword=keyword)
        return self.scraper.get_post_list(page=page)

    def on_worker_state_changed(self, event: WorkerState) -> None:
        if event.worker.name == "fetch_posts":
            if event.state == event.state.SUCCESS:
                self.update_table(event.worker.result)
                self.query_one("#loading").remove_class("-active")
            elif event.state == event.state.ERROR:
                self.query_one("#loading").remove_class("-active")
                self.notify("Failed to fetch posts", severity="error")
        elif event.worker.name == "fetch_content":
            if event.state == event.state.SUCCESS:
                self.show_post(event.worker.result)
                self.query_one("#loading").remove_class("-active")
            elif event.state == event.state.ERROR:
                self.query_one("#loading").remove_class("-active")
                self.notify("Failed to fetch content", severity="error")

    def update_table(self, posts: list) -> None:
        self.posts_data = posts
        table = self.query_one(DataTable)
        table.clear()
        for post in posts:
            table.add_row(
                post["id"],
                post["title"],
                f"[{post['comments']}]" if post['comments'] else "",
                post["writer"],
                post["date"],
                post["views"],
                post["recommends"],
                key=post["id"]
            )
        self.sub_title = f"페이지 {self.current_page} | v1.0.0 | Built by Jaden Lee"
        table.focus()

    def action_refresh_list(self) -> None:
        if self.query_one("#post_viewer").has_class("-active"):
            return
        self.query_one("#loading").add_class("-active")
        self.fetch_posts(keyword=self.search_keyword, page=self.current_page)

    def action_back(self) -> None:
        search_input = self.query_one("#search_input", Input)
        if search_input.has_class("-active"):
            search_input.remove_class("-active")
            self.query_one(DataTable).focus()
            return

        if self.query_one("#post_viewer").has_class("-active"):
            self.query_one("#post_viewer").remove_class("-active")
            self.query_one(DataTable).remove_class("-hidden")
            self.current_post = None
            
            self.app.bind("p", "prev", description="Prev Page", show=True)
            self.app.bind("n", "next", description="Next Page", show=True)
            self.app.bind("r", "refresh_list", description="Refresh", show=True)
            self.app.bind("/", "search", description="Search", show=True)
            self.app.bind("escape", "back", description="Gallery(Esc)", show=True)
            self.refresh_bindings()
            
            self.query_one(DataTable).focus()
            return

        # If neither search nor post is open, go back to Gallery Select
        self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        post_id = event.row_key.value
        self.query_one("#loading").add_class("-active")
        self.fetch_content(post_id)

    @work(exclusive=True, thread=True)
    def fetch_content(self, post_id: str) -> dict:
        return self.scraper.get_post_content(post_id)

    def show_post(self, result: dict) -> None:
        if not result:
            self.notify("Content not found", severity="error")
            return
            
        self.current_post = result["id"]
        
        post_meta = next((p for p in self.posts_data if p["id"] == result["id"]), None)
        if post_meta:
            header_text = (
                f"제목: {post_meta['title']}\n"
                f"작성자: {post_meta['writer']} | 조회: {post_meta['views']} | 추천: {post_meta['recommends']}\n"
                f"💡 단축키: [ b 또는 Esc : 목록으로 ]  [ p : 이전 글 ]  [ n : 다음 글 ]"
            )
            self.query_one("#post_header", Static).update(header_text)
            
        markdown_view = self.query_one("#post_content", Markdown)
        markdown_view.update(result["content"])
        
        self.query_one(DataTable).add_class("-hidden")
        viewer = self.query_one("#post_viewer")
        viewer.add_class("-active")
        
        self.app.bind("p", "prev", description="Prev Post", show=True)
        self.app.bind("n", "next", description="Next Post", show=True)
        self.app.bind("r", "refresh_list", description="Refresh", show=False)
        self.app.bind("/", "search", description="Search", show=False)
        self.app.bind("escape", "back", description="List(Esc)", show=True)
        self.refresh_bindings()
        
        viewer.focus()

    def action_prev(self) -> None:
        if self.query_one("#post_viewer").has_class("-active"):
            self._prev_post()
        else:
            self._prev_page()

    def action_next(self) -> None:
        if self.query_one("#post_viewer").has_class("-active"):
            self._next_post()
        else:
            self._next_page()

    def _prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.action_refresh_list()
            
    def _next_page(self) -> None:
        self.current_page += 1
        self.action_refresh_list()

    def _prev_post(self) -> None:
        if not self.posts_data: return
        idx = next((i for i, p in enumerate(self.posts_data) if p["id"] == self.current_post), -1)
        if idx > 0:
            next_post_id = self.posts_data[idx - 1]["id"]
            self.query_one("#loading").add_class("-active")
            self.fetch_content(next_post_id)

    def _next_post(self) -> None:
        if not self.posts_data: return
        idx = next((i for i, p in enumerate(self.posts_data) if p["id"] == self.current_post), -1)
        if 0 <= idx < len(self.posts_data) - 1:
            next_post_id = self.posts_data[idx + 1]["id"]
            self.query_one("#loading").add_class("-active")
            self.fetch_content(next_post_id)

    def action_search(self) -> None:
        if self.query_one("#post_viewer").has_class("-active"):
            return
        search_input = self.query_one("#search_input", Input)
        if search_input.has_class("-active"):
            search_input.remove_class("-active")
            self.query_one(DataTable).focus()
        else:
            search_input.add_class("-active")
            search_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search_input":
            self.search_keyword = event.value
            self.current_page = 1
            self.query_one("#search_input").remove_class("-active")
            self.query_one(DataTable).focus()
            self.query_one("#loading").add_class("-active")
            self.fetch_posts(keyword=self.search_keyword, page=self.current_page)

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        url = event.href
        if "dcinside.com" in url or "dcimg" in url:
            self.query_one("#loading").add_class("-active")
            self.download_and_open_media(url)
        else:
            self.app.open_url(url)

    @work(exclusive=False, thread=True)
    def download_and_open_media(self, url: str) -> None:
        import requests, tempfile, subprocess, os
        try:
            get_bounds_script = """
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                tell process frontApp
                    set termBounds to position of front window
                    set termSize to size of front window
                end tell
                return (item 1 of termBounds as string) & "," & (item 2 of termBounds as string) & "," & (item 1 of termSize as string) & "," & (item 2 of termSize as string)
            end tell
            """
            result = subprocess.run(["osascript", "-e", get_bounds_script], capture_output=True, text=True)
            term_bounds = result.stdout.strip().split(',')
            termX, termY, termW, termH = map(int, term_bounds)
        except Exception:
            termX, termY, termW, termH = None, None, None, None

        headers = self.scraper.headers.copy()
        headers["Referer"] = "https://gall.dcinside.com/"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            ext = ".jpg"
            if ".png" in url: ext = ".png"
            elif ".gif" in url: ext = ".gif"
            elif ".mp4" in url: ext = ".mp4"
            fd, path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, 'wb') as f:
                f.write(resp.content)
            subprocess.run(["open", path])
            if termX is not None:
                position_script = f"""
                delay 0.5
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    tell process frontApp
                        set prevSize to size of front window
                        set prevW to item 1 of prevSize
                        set targetX to {termX} + {termW} - prevW
                        set targetY to {termY}
                        set position of front window to {{targetX, targetY}}
                    end tell
                end tell
                """
                subprocess.Popen(["osascript", "-e", position_script])
            self.app.call_from_thread(self.notify, "미디어를 열었습니다.")
            self.app.call_from_thread(self.query_one("#loading").remove_class, "-active")
        except Exception as e:
            self.app.call_from_thread(self.notify, f"미디어 열기 실패: {str(e)}", severity="error")
            self.app.call_from_thread(self.query_one("#loading").remove_class, "-active")

class DCInsideApp(App):
    """A Textual app to view DCInside gallery."""
    
    CSS = """
    #gallery_select_container {
        padding: 2 4;
    }
    .title {
        text-style: bold;
        padding-bottom: 1;
    }
    .subtitle {
        margin-top: 2;
        padding-bottom: 1;
    }
    OptionList {
        height: 1fr;
        border: solid $primary;
    }
    DataTable {
        height: 100%;
    }
    #post_viewer {
        display: none;
        height: 100%;
        overflow-y: auto;
        padding: 1 4;
        background: $surface;
    }
    #post_header {
        text-style: bold;
        padding-bottom: 1;
        margin-bottom: 1;
        border-bottom: solid $primary;
    }
    #post_viewer.-active {
        display: block;
    }
    DataTable.-hidden {
        display: none;
    }
    #loading {
        display: none;
        dock: top;
        height: auto;
        content-align: center middle;
    }
    #loading.-active {
        display: block;
    }
    #search_input {
        display: none;
        dock: bottom;
    }
    #search_input.-active {
        display: block;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(GallerySelectScreen())
        
    def switch_to_gallery(self, gallery_info: dict):
        self.push_screen(PostListScreen(gallery_info))

if __name__ == "__main__":
    app = DCInsideApp()
    app.run()
