"""Navigation Agent TUI application using Textual framework."""
import asyncio
import io
import threading
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, RichLog
from textual.binding import Binding

import memory_tools
import session_manager
import config
from config import SPACE_ID, OPENAI_MODEL_NAME


class TUIStdoutBridge(io.TextIOBase):
    """Thread-safe stdout bridge that redirects print() to RichLog."""

    def __init__(self, app: "NavAgentApp"):
        """Initialize bridge with app reference and thread lock."""
        self.app = app
        self.lock = threading.Lock()

    def write(self, s: str) -> int:
        """Write string to chat log with thread safety."""
        if not s.strip():
            return len(s)
        with self.lock:
            try:
                chat_log = self.app.query_one("#chat_log", RichLog)
                # Use dim style for SDK prints to distinguish from user/agent messages
                chat_log.write(f"[dim]{s.strip()}[/]")
            except Exception:
                # App might be closed, ignore
                pass
        return len(s)

    def flush(self):
        """No-op flush for compatibility."""
        pass


class SessionSelectScreen(ModalScreen[tuple[Optional[str], Optional[str], bool]]):
    """Modal screen for session selection."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Previous", show=False),
        Binding("ctrl+t", "focus_title_input", "Title Input"),
    ]

    def __init__(self):
        """Initialize session list and selection state."""
        super().__init__()
        self.sessions = session_manager.list_sessions()
        self._selected_index = 0

    def compose(self) -> ComposeResult:
        """Build session selection dialog with list, input, and buttons."""
        with Container(id="session-dialog"):
            yield Label("Select Session", id="dialog-title")

            # Create list view with options
            items = []

            # Option 1: New session
            items.append(ListItem(Label("[bold green]+ Create New Session[/]")))

            # Existing sessions
            for s in self.sessions:
                title = s.get("title", "untitled")
                ts = s.get("last_active", "?")
                count = s.get("message_count", 0)
                items.append(
                    ListItem(Label(f"[cyan]{title}[/] [dim](last: {ts}, msgs: {count})[/]"))
                )

            yield ListView(*items, id="session-list")

            # Title input (for new session title, or new name for renaming)
            yield Input(
                placeholder="Type new name to rename selected session",
                id="title-input",
            )

            with Container(id="button-row"):
                yield Button("Confirm", variant="primary", id="confirm-btn")
                yield Button("Rename", variant="warning", id="rename-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Track cursor position as user navigates with arrow keys."""
        self._selected_index = event.list_view.index or 0

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection - Enter on item triggers confirm directly."""
        self._selected_index = event.list_view.index or 0
        # Directly confirm selection on Enter (no need to click button)
        self._confirm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-btn":
            self.dismiss((None, None, False))
        elif event.button.id == "confirm-btn":
            self._confirm()
        elif event.button.id == "rename-btn":
            self._rename()

    def _confirm(self) -> None:
        """Confirm selection and dismiss."""
        idx = self._selected_index
        title_input = self.query_one("#title-input", Input)
        title = title_input.value.strip()

        if idx == 0:
            # Create new session
            session = session_manager.create_new_session(title)
            self.dismiss((session["session_id"], session["title"], True))
        else:
            # Resume existing session
            session_idx = idx - 1  # offset for "new session" option
            if 0 <= session_idx < len(self.sessions):
                s = self.sessions[session_idx]
                self.dismiss((s["session_id"], s["title"], False))
            else:
                self.notify("Invalid selection", severity="error")

    def _rename(self) -> None:
        """Rename the selected session."""
        idx = self._selected_index
        title_input = self.query_one("#title-input", Input)
        new_title = title_input.value.strip()

        # Validation
        if idx == 0:
            self.notify("Cannot rename 'Create New Session'", severity="warning")
            return

        if not new_title:
            self.notify("Please enter a new name", severity="warning")
            return

        session_idx = idx - 1  # offset for "new session" option
        if not (0 <= session_idx < len(self.sessions)):
            self.notify("Invalid selection", severity="error")
            return

        # Perform rename
        session_id = self.sessions[session_idx]["session_id"]
        session_manager.update_session_title(session_id, new_title)

        # Update local data
        self.sessions[session_idx]["title"] = new_title[:50]

        # Update ListView display
        list_view = self.query_one("#session-list", ListView)
        # ListView children are indexed; rebuild the label for the renamed item
        # idx is the position in the list (0 = "Create New Session", 1..N = sessions)
        children = list(list_view.children)
        if idx < len(children):
            item = children[idx]
            # Find the Label widget inside the ListItem
            label = item.query_one(Label)
            s = self.sessions[session_idx]
            ts = s.get("last_active", "?")
            count = s.get("message_count", 0)
            label.update(f"[cyan]{new_title[:50]}[/] [dim](last: {ts}, msgs: {count})[/]")

        # Clear input and show success
        title_input.value = ""
        self.notify(f"Renamed to: {new_title[:50]}")

        # Keep focus on the list for further navigation
        list_view.focus()

    def action_cancel(self) -> None:
        """Cancel and dismiss."""
        self.dismiss((None, None, False))

    def action_focus_title_input(self) -> None:
        """Focus the title input field."""
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

    def on_key(self, event) -> None:
        """Handle key events to ensure Tab navigation works."""
        if event.key == "tab":
            # Move focus to next widget
            self.focus_next()
            event.prevent_default()
            event.stop()
        elif event.key == "shift+tab":
            # Move focus to previous widget
            self.focus_previous()
            event.prevent_default()
            event.stop()


class NavAgentApp(App):
    """Navigation Agent TUI application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #chat_log {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }

    #user_input {
        margin: 0 1;
    }

    #session-dialog {
        width: 80;
        height: auto;
        max-height: 80%;
        border: thick $primary 80%;
        background: $surface;
        padding: 1;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #session-list {
        height: 15;
        margin-bottom: 1;
    }

    #title-input {
        margin-bottom: 1;
    }

    #button-row {
        layout: horizontal;
        height: auto;
        align: center middle;
    }

    #button-row Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
    ]

    def __init__(self, debug: bool = False):
        """Initialize app state for session management and agent interaction."""
        super().__init__()
        # Use _debug to avoid conflict with App.debug property
        self._debug = debug
        self._agent = None
        self._checkpointer = None
        self._store = None
        self._thread_config = None
        self._session_id = None
        self._session_title = None
        self._message_count = 0
        self._title_auto_set = False

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header(show_clock=False)
        yield RichLog(id="chat_log", auto_scroll=True, wrap=True, markup=True)
        yield Input(id="user_input", placeholder="Type your message (or quit/exit)")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize app after mount."""
        chat_log = self.query_one("#chat_log", RichLog)

        # Show banner
        chat_log.write("[bold blue]Navigation Agent Demo[/]")
        chat_log.write(f"[dim]Space ID:   {SPACE_ID}[/]")
        chat_log.write(f"[dim]Model:      {OPENAI_MODEL_NAME}[/]")
        amap_status = "set" if config.AMAP_KEY else "NOT set (using mock data)"
        chat_log.write(f"[dim]AMap Key:   {amap_status}[/]")
        chat_log.write("")

        # Push session selection screen
        self.push_screen(SessionSelectScreen(), self._on_session_selected)

    def _on_session_selected(
        self, result: tuple[Optional[str], Optional[str], bool]
    ) -> None:
        """Handle session selection result."""
        session_id, session_title, is_new = result

        if session_id is None:
            # User cancelled
            self.exit()
            return

        self._session_id = session_id
        self._session_title = session_title

        # For resumed sessions, don't auto-set title on first message
        if not is_new:
            self._title_auto_set = True
            # Load existing message count from sessions.json
            for s in session_manager.list_sessions():
                if s["session_id"] == session_id:
                    self._message_count = s.get("message_count", 0)
                    break

        chat_log = self.query_one("#chat_log", RichLog)

        # Validate session if resuming
        if not is_new:
            if not session_manager.validate_session(session_id):
                chat_log.write(
                    f"[yellow]Session {session_id[:8]}... not found in current space.[/]"
                )
                chat_log.write("[yellow]Creating a new session...[/]")
                new_session = session_manager.create_new_session(session_title)
                self._session_id = new_session["session_id"]
                self._session_title = new_session["title"]
                self._message_count = 0  # Reset for new session
                chat_log.write(f"[green]New session created: {self._session_id[:8]}...[/]")
            else:
                chat_log.write(f"[green]Resuming session: {session_title}[/]")
                # Show recent message history
                self._show_message_history(chat_log, self._session_id)
        else:
            chat_log.write(f"[green]New session: {self._session_title}[/]")

        chat_log.write(f"[dim]Session ID: {self._session_id}[/]")
        chat_log.write("")
        chat_log.write("[dim]Type 'quit' or 'exit' to stop.[/]")
        chat_log.write("")

        # Set session for memory tools
        memory_tools.set_current_session(self._session_id)

        # Build agent
        self._build_agent()

        # Focus input
        self.query_one("#user_input", Input).focus()

    def _show_message_history(self, chat_log: RichLog, session_id: str) -> None:
        """Fetch and display recent messages from the session."""
        from message_utils import fetch_session_history

        try:
            history = fetch_session_history(session_id)

            if not history:
                chat_log.write("[dim]No message history found.[/]")
                return

            # Display messages (oldest first, newest last)
            chat_log.write("[dim]--- Recent Messages ---[/]")
            for role, content in history:
                if role == 'user':
                    chat_log.write(f"[cyan]you:[/] {content}")
                elif role == 'assistant':
                    chat_log.write(f"[green]agent:[/] {content}")

            chat_log.write("[dim]--- End History ---[/]")
            chat_log.write("")

        except Exception as e:
            chat_log.write(f"[yellow]Could not load message history: {e}[/]")
            if self._debug:
                import traceback
                chat_log.write(f"[dim]{traceback.format_exc()}[/]")
            chat_log.write("")

    def _build_agent(self) -> None:
        """Build the LangGraph agent."""
        from nav_agent import build_agent

        self._agent, self._checkpointer, self._store = build_agent()
        self._thread_config = {
            "configurable": {
                "thread_id": self._session_id,
                "actor_id": config.ACTOR_ID,
                "assistant_id": config.ASSISTANT_ID,
            }
        }

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        text = event.value.strip()
        event.input.value = ""  # Clear input

        if not text:
            return

        # Check for quit commands
        if text.lower() in ("quit", "exit", "q"):
            self.exit()
            return

        # Auto-set title on first message
        if not self._title_auto_set:
            self._title_auto_set = True
            new_title = text[:30]
            session_manager.update_session_title(self._session_id, new_title)
            self._session_title = new_title

        # Run agent in background worker
        self.run_worker(self._send_message(text), exclusive=True)

    async def _send_message(self, text: str) -> None:
        """Send message to agent and display response."""
        chat_log = self.query_one("#chat_log", RichLog)
        input_widget = self.query_one("#user_input", Input)

        # Disable input while processing
        input_widget.disabled = True

        try:
            # Display user message
            chat_log.write(f"[cyan]you:[/] {text}")

            # Invoke agent in thread (avoid blocking TUI event loop)
            result = await asyncio.to_thread(self._invoke_agent_sync, text)

            # Display agent response
            if "error" in result:
                chat_log.write(f"[red]agent: {result['error']}[/]")
            else:
                reply = result.get("reply", "")
                chat_log.write(f"[green]agent:[/] {reply}")

            self._message_count += 1

        except Exception as e:
            chat_log.write(f"[red]Error: {str(e)}[/]")

        finally:
            # Re-enable input
            input_widget.disabled = False
            input_widget.focus()

    def _invoke_agent_sync(self, text: str) -> dict:
        """Synchronously invoke agent.

        This runs in a worker thread via asyncio.to_thread().
        """
        from langchain_core.messages import HumanMessage

        try:
            result = self._agent.invoke(
                {"messages": [HumanMessage(content=text)]},
                config=self._thread_config,
            )

            # Extract reply from result
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                reply = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                return {"reply": reply}
            else:
                return {"reply": "(no response)"}

        except Exception as e:
            return {"error": str(e)}

    def action_clear_log(self) -> None:
        """Clear the chat log."""
        chat_log = self.query_one("#chat_log", RichLog)
        chat_log.clear()

    def on_unmount(self) -> None:
        """Cleanup on app exit."""
        if self._session_id and self._message_count > 0:
            try:
                session_manager.update_session(self._session_id, self._message_count)
            except Exception:
                pass

        if self._checkpointer:
            try:
                self._checkpointer.close()
            except Exception:
                pass

        if self._store:
            try:
                self._store.close()
            except Exception:
                pass
