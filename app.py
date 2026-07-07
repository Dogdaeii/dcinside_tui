import json
import os
import sys
import subprocess
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, DataTable, Markdown, Static, Input, OptionList, Label, Link
from textual.widgets.option_list import Option
from textual.containers import Container, ScrollableContainer, Vertical
from textual.binding import Binding
from textual.worker import Worker, WorkerState
from textual import work
from textual import events

from scraper import DCScraper
from themes import SKINS, register_all_themes

GALLERIES_FILE = "galleries.json"
SETTINGS_FILE = "settings.json"
WINDOW_COLUMNS = 140
WINDOW_ROWS = 66
DEFAULT_GALLERIES = [
    {"name": "특이점이 온다", "id": "thesingularity", "type": "mgallery", "url": "https://gall.dcinside.com/mgallery/board/lists?id=thesingularity"},
    {"name": "러닝 마이너", "id": "running", "type": "mgallery", "url": "https://gall.dcinside.com/mgallery/board/lists?id=running"}
]

def request_terminal_size(columns: int = WINDOW_COLUMNS, rows: int = WINDOW_ROWS) -> None:
    if not sys.stdout.isatty():
        return
    sys.stdout.write(f"\033[8;{rows};{columns}t")
    sys.stdout.flush()

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
        
def get_installed_browsers():
    browsers = ["Default"]
    apps_dir = "/Applications"
    if os.path.exists(apps_dir):
        apps = os.listdir(apps_dir)
        known_browsers = {
            "Safari.app": "Safari",
            "Google Chrome.app": "Google Chrome",
            "Firefox.app": "Firefox",
            "Microsoft Edge.app": "Microsoft Edge",
            "Brave Browser.app": "Brave Browser",
            "Opera.app": "Opera",
            "Vivaldi.app": "Vivaldi",
            "Arc.app": "Arc",
            "Whale.app": "Naver Whale",
        }
        for app in apps:
            if app in known_browsers:
                browsers.append(known_browsers[app])
    return browsers

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"theme": "NASA 콘솔", "browser": "Default"}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
            if "browser" not in settings:
                settings["browser"] = "Default"
            return settings
    except:
        return {"theme": "NASA 콘솔", "browser": "Default"}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

class BrowserSelectScreen(ModalScreen):
    """Modal screen for selecting a browser."""
    
    CSS = """
    BrowserSelectScreen {
        align: center middle;
    }
    #browser_dialog {
        padding: 1 2;
        width: 40;
        height: 20;
        border: solid $primary;
        background: $surface;
    }
    """
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Cancel"),
        Binding("w", "app.pop_screen", "Cancel"),
        Binding("ㅠ", "app.pop_screen", "Cancel", show=False)
    ]
    
    def compose(self) -> ComposeResult:
        with Vertical(id="browser_dialog"):
            yield Label("브라우저 선택", classes="title")
            yield OptionList(id="browser_list")
            
    def on_mount(self) -> None:
        option_list = self.query_one("#browser_list", OptionList)
        active_browser = self.app.active_browser
        browsers = get_installed_browsers()
        for idx, name in enumerate(browsers):
            option_list.add_option(Option(name, id=name))
            if name == active_browser:
                option_list.highlighted = idx
                
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        browser_name = event.option_id
        self.app.set_browser(browser_name)
        self.app.pop_screen()


class ThemeSelectScreen(ModalScreen):
    """Modal screen for selecting a theme."""
    
    CSS = """
    ThemeSelectScreen {
        align: center middle;
    }
    #theme_dialog {
        padding: 1 2;
        width: 40;
        height: 20;
        border: solid $primary;
        background: $surface;
    }
    """
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Cancel"),
        Binding("t", "app.pop_screen", "Cancel"),
        Binding("ㅅ", "app.pop_screen", "Cancel", show=False)
    ]
    
    def compose(self) -> ComposeResult:
        with Vertical(id="theme_dialog"):
            yield Label("스킨 선택", classes="title")
            yield OptionList(id="theme_list")
            
    def on_mount(self) -> None:
        option_list = self.query_one("#theme_list", OptionList)
        active_skin = self.app.active_skin
        for idx, name in enumerate(SKINS.keys()):
            option_list.add_option(Option(name, id=name))
            if name == active_skin:
                option_list.highlighted = idx
                
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        theme_name = event.option_id
        self.app.set_theme(theme_name)
        self.app.pop_screen()

class GallerySelectScreen(Screen):
    """Screen for selecting or adding a gallery."""
    
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("ㅂ", "app.quit", "Quit", show=False),
        Binding("t", "app.toggle_theme_screen", "Theme(t)"),
        Binding("ㅅ", "app.toggle_theme_screen", "Theme(t)", show=False),
        Binding("w", "app.toggle_browser_screen", "Browser(w)"),
        Binding("ㅠ", "app.toggle_browser_screen", "Browser(w)", show=False)
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
        Binding("ㅂ", "app.quit", "Quit", show=False),
        Binding("t", "app.toggle_theme_screen", "Theme(t)"),
        Binding("ㅅ", "app.toggle_theme_screen", "Theme(t)", show=False),
        Binding("w", "app.toggle_browser_screen", "Browser(w)"),
        Binding("ㅠ", "app.toggle_browser_screen", "Browser(w)", show=False),
        Binding("r", "refresh_list", "Refresh"),
        Binding("ㄱ", "refresh_list", "Refresh", show=False),
        Binding("/", "search", "Search"),
        Binding("p", "prev", "Prev Page"),
        Binding("ㅔ", "prev", "Prev Page", show=False),
        Binding("n", "next", "Next Page"),
        Binding("ㅜ", "next", "Next Page", show=False),
        Binding("o", "open_original_post", "Original", show=False),
        Binding("ㅐ", "open_original_post", "Original", show=False),
        Binding("escape", "back", "Gallery(Esc)"),
        Binding("b", "back", "Back", show=False),
        Binding("ㅠ", "back", "Back", show=False),
    ]

    def __init__(self, gallery_info: dict):
        super().__init__()
        self.gallery_info = gallery_info
        self.scraper = DCScraper(gallery_info["id"], gallery_info["type"])
        self.current_post = None
        self.posts_data = []
        self.search_keyword = ""
        self.current_page = 1
        self.current_post_url = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="loading")
        yield Input(placeholder="검색어 입력 후 Enter (제목+내용)", id="search_input")
        yield DataTable(id="post_list")
        with ScrollableContainer(id="post_viewer"):
            yield Static(id="post_header")
            yield Link("↗ 원글 열기", id="original_post_link", classes="-hidden", tooltip="브라우저에서 원글을 엽니다")
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
            self.current_post_url = ""
            
            self.app.bind("p", "prev", description="Prev Page", show=True)
            self.app.bind("n", "next", description="Next Page", show=True)
            self.app.bind("r", "refresh_list", description="Refresh", show=True)
            self.app.bind("/", "search", description="Search", show=True)
            self.app.bind("escape", "back", description="Gallery(Esc)", show=True)
            self.app.bind("t", "app.toggle_theme_screen", description="Theme(t)", show=True)
            self.app.bind("b", "app.toggle_browser_screen", description="Browser(w)", show=True)
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
        self.current_post_url = result.get("url", "")
        
        post_meta = next((p for p in self.posts_data if p["id"] == result["id"]), None)
        if post_meta:
            header_text = (
                f"제목: {post_meta['title']}\n"
                f"작성자: {post_meta['writer']} | 조회: {post_meta['views']} | 추천: {post_meta['recommends']}\n"
                f"💡 단축키: [ b 또는 Esc : 목록으로 ]  [ p : 이전 글 ]  [ n : 다음 글 ]  [ o : 원글 열기 ]  [ 드래그 선택 후 Cmd+C : 복사 ]"
            )
            self.query_one("#post_header", Static).update(header_text)
            
        markdown_view = self.query_one("#post_content", Markdown)
        original_url = result.get("url", "")
        original_link = self.query_one("#original_post_link", Link)
        if original_url:
            original_link.url = original_url
            original_link.remove_class("-hidden")
        else:
            original_link.add_class("-hidden")
        markdown_view.update(result["content"])
        
        self.query_one(DataTable).add_class("-hidden")
        viewer = self.query_one("#post_viewer")
        viewer.add_class("-active")
        
        self.app.bind("p", "prev", description="Prev Post", show=True)
        self.app.bind("n", "next", description="Next Post", show=True)
        self.app.bind("r", "refresh_list", description="Refresh", show=False)
        self.app.bind("/", "search", description="Search", show=False)
        self.app.bind("t", "app.toggle_theme_screen", description="Theme", show=False)
        self.app.bind("b", "app.toggle_browser_screen", description="Browser", show=False)
        self.app.bind("escape", "back", description="List(Esc)", show=True)
        self.refresh_bindings()
        
        viewer.focus()

    def action_open_original_post(self) -> None:
        if not self.current_post_url:
            self.notify("원글 주소가 없습니다.", severity="warning")
            return
        self.app.open_url(self.current_post_url)

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
        media_extensions = (".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webm")
        is_media_url = "dcimg" in url or url.lower().split("?")[0].endswith(media_extensions)
        if is_media_url:
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
    Screen {
        pointer: pointer;
    }
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
    #original_post_link {
        margin: 0 0 1 0;
        padding: 0 1;
        color: $accent;
        text-style: bold underline;
        background: $accent 10%;
        border-left: thick $accent;
        pointer: pointer;
    }
    #original_post_link:hover {
        color: $text;
        background: $accent 55%;
    }
    #original_post_link.-hidden {
        display: none;
    }
    #post_content MarkdownBlock:hover {
        color: $text;
        background: $accent 25%;
        pointer: pointer;
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
        register_all_themes(self)
        settings = load_settings()
        self.active_skin = settings.get("theme", "NASA 콘솔")
        self.set_theme(self.active_skin)
        self.active_browser = settings.get("browser", "Default")
        self.push_screen(GallerySelectScreen())
        self._set_pointer_shape("pointer")

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if getattr(self.screen, "_selecting", False):
            self._set_pointer_shape("text")
            return
        self._set_pointer_shape("pointer")
        
    def switch_to_gallery(self, gallery_info: dict):
        self.push_screen(PostListScreen(gallery_info))

    def action_toggle_theme_screen(self):
        self.push_screen(ThemeSelectScreen())

    def set_theme(self, theme_name: str):
        try:
            idx = list(SKINS.keys()).index(theme_name)
            self.theme = f"theme_{idx}"
        except ValueError:
            pass
        
        self.active_skin = theme_name
        
        # Save settings
        settings = load_settings()
        settings["theme"] = theme_name
        save_settings(settings)

    def action_toggle_browser_screen(self):
        self.push_screen(BrowserSelectScreen())

    def set_browser(self, browser_name: str):
        self.active_browser = browser_name
        settings = load_settings()
        settings["browser"] = browser_name
        save_settings(settings)

    def open_url(self, url: str) -> None:
        if hasattr(self, 'active_browser') and self.active_browser != "Default":
            subprocess.Popen(["open", "-a", self.active_browser, url])
        else:
            super().open_url(url)

if __name__ == "__main__":
    request_terminal_size()
    app = DCInsideApp()
    app.run(mouse=True)
