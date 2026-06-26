from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Markdown, Static, Input
from textual.containers import Container, ScrollableContainer
from textual.binding import Binding
from textual.worker import Worker, WorkerState
from textual import work

from scraper import DCScraper

class PostViewer(Container):
    """Container for viewing a post."""
    def compose(self) -> ComposeResult:
        yield Static(id="post_header")
        yield Markdown(id="post_content")

class DCInsideApp(App):
    """A Textual app to view DCInside gallery."""
    
    CSS = """
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
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_list", "Refresh"),
        Binding("/", "search", "Search"),
        Binding("p", "prev", "Prev Page"),
        Binding("n", "next", "Next Page"),
        Binding("escape", "back_to_list", "Back(Esc)"),
        Binding("b", "back_to_list", "Back", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.scraper = DCScraper("thesingularity")
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
            yield Markdown(id="post_content")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "DCInside Viewer - 특이점이 온다"
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
        self.sub_title = f"페이지 {self.current_page}"

    def action_refresh_list(self) -> None:
        """Refresh the post list."""
        if self.query_one("#post_viewer").has_class("-active"):
            return
            
        self.query_one("#loading").add_class("-active")
        self.fetch_posts(keyword=self.search_keyword, page=self.current_page)

    def action_back_to_list(self) -> None:
        """Go back to the post list or cancel search."""
        search_input = self.query_one("#search_input", Input)
        if search_input.has_class("-active"):
            search_input.remove_class("-active")
            self.query_one(DataTable).focus()
            return

        if not self.query_one("#post_viewer").has_class("-active"):
            return

        self.query_one("#post_viewer").remove_class("-active")
        self.query_one(DataTable).remove_class("-hidden")
        self.current_post = None
        
        # Update bindings display
        self.app.bind("p", "prev", description="Prev Page", show=True)
        self.app.bind("n", "next", description="Next Page", show=True)
        self.app.bind("r", "refresh_list", description="Refresh", show=True)
        self.app.bind("/", "search", description="Search", show=True)
        self.refresh_bindings()
        
        self.query_one(DataTable).focus()

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
        
        # Find post metadata for header
        post_meta = next((p for p in self.posts_data if p["id"] == result["id"]), None)
        if post_meta:
            header_text = (
                f"제목: {post_meta['title']}\n"
                f"작성자: {post_meta['writer']} | 조회: {post_meta['views']} | 추천: {post_meta['recommends']}\n"
                f"💡 단축키: [ b 또는 Esc : 목록으로 ]  [ ← : 이전 글 ]  [ → : 다음 글 ]"
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
        if not self.posts_data:
            return
        idx = next((i for i, p in enumerate(self.posts_data) if p["id"] == self.current_post), -1)
        if idx > 0:
            next_post_id = self.posts_data[idx - 1]["id"]
            self.query_one("#loading").add_class("-active")
            self.fetch_content(next_post_id)

    def _next_post(self) -> None:
        if not self.posts_data:
            return
        idx = next((i for i, p in enumerate(self.posts_data) if p["id"] == self.current_post), -1)
        if 0 <= idx < len(self.posts_data) - 1:
            next_post_id = self.posts_data[idx + 1]["id"]
            self.query_one("#loading").add_class("-active")
            self.fetch_content(next_post_id)

    def action_search(self) -> None:
        """Toggle search input."""
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


if __name__ == "__main__":
    app = DCInsideApp()
    app.run()
