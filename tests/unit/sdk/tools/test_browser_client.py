"""
测试 Browser Client
"""

import os
import unittest
from unittest.mock import patch

from agentarts.sdk.service.tools_http import (
    ControlBrowserHttpClient,
    DataBrowserHttpClient,
)
from agentarts.sdk.tools.browser import Browser

UUID = "9ca9f2a6-18e4-4777-b23b-8c21e978a1ad"


class TestBrowserClient(unittest.TestCase):
    @patch("agentarts.sdk.utils.constant.ENV_HUAWEICLOUD_SDK_AK")
    @patch("agentarts.sdk.utils.constant.ENV_HUAWEICLOUD_SDK_SK")
    @patch("agentarts.sdk.utils.constant.get_control_plane_endpoint")
    @patch("agentarts.sdk.utils.constant.get_browser_data_plane_endpoint")
    def setUp(self, *mocks):
        os.environ["HUAWEICLOUD_SDK_BROWSER_API_KEY"] = "test-key"
        self.client = Browser(region="test-region")

    # ── Control plane: Browser CRUD ─────────────────────────────────────

    @patch.object(ControlBrowserHttpClient, "create_browser")
    def test_create_browser(self, mock):
        mock.return_value = {"id": "b-1", "name": "test"}
        r = self.client.create_browser(
            name="test-browser", auth_type="API_KEY", api_key_name="my-key",
        )
        assert r["id"] == "b-1"
        mock.assert_called_once_with(
            request_params={"name": "test-browser", "auth_type": "API_KEY", "api_key_name": "my-key"},
        )

    def test_create_browser_bad_name(self):
        with self.assertRaises(ValueError):
            self.client.create_browser(name="A", auth_type="API_KEY", api_key_name="k")

    def test_create_browser_bad_auth_type(self):
        with self.assertRaises(ValueError):
            self.client.create_browser(name="test-browser", auth_type="X")

    def test_create_browser_api_key_needs_name(self):
        with self.assertRaises(ValueError):
            self.client.create_browser(name="test-browser", auth_type="API_KEY")

    @patch.object(ControlBrowserHttpClient, "list_browsers")
    def test_list_browsers(self, mock):
        mock.return_value = {"items": [], "total_count": 0}
        assert self.client.list_browsers()["total_count"] == 0

    @patch.object(ControlBrowserHttpClient, "list_browsers")
    def test_list_browsers_with_filters(self, mock):
        mock.return_value = {"items": [], "total_count": 0}
        self.client.list_browsers(limit=5, sort_key="updated_at", sort_dir="asc")
        params = mock.call_args.kwargs["request_params"]
        assert params["limit"] == 5
        assert params["sort_key"] == "updated_at"

    def test_list_browsers_bad_sort(self):
        with self.assertRaises(ValueError):
            self.client.list_browsers(sort_key="name")

    @patch.object(ControlBrowserHttpClient, "get_browser")
    def test_get_browser(self, mock):
        mock.return_value = {"id": UUID}
        assert self.client.get_browser(browser_id=UUID)["id"] == UUID

    def test_get_browser_bad_id(self):
        with self.assertRaises(ValueError):
            self.client.get_browser(browser_id="not-uuid")

    @patch.object(ControlBrowserHttpClient, "update_browser")
    def test_update_browser(self, mock):
        mock.return_value = {"id": UUID}
        r = self.client.update_browser(
            browser_id=UUID, observability={"logs": {"enabled": False}},
        )
        assert r["id"] == UUID

    def test_update_browser_bad_id(self):
        with self.assertRaises(ValueError):
            self.client.update_browser(browser_id="bad")

    @patch.object(ControlBrowserHttpClient, "delete_browser")
    def test_delete_browser(self, mock):
        assert self.client.delete_browser(browser_id=UUID) is True

    # ── Control plane: Profile CRUD ─────────────────────────────────────

    @patch.object(ControlBrowserHttpClient, "create_browser_profile")
    def test_create_profile(self, mock):
        mock.return_value = {"id": "p-1", "name": "test"}
        assert self.client.create_browser_profile(name="test-profile")["id"] == "p-1"

    def test_create_profile_bad_name(self):
        with self.assertRaises(ValueError):
            self.client.create_browser_profile(name="A")

    @patch.object(ControlBrowserHttpClient, "list_browser_profiles")
    def test_list_profiles(self, mock):
        mock.return_value = {"items": [], "total_count": 0}
        assert self.client.list_browser_profiles()["total_count"] == 0

    @patch.object(ControlBrowserHttpClient, "get_browser_profile")
    def test_get_profile(self, mock):
        mock.return_value = {"id": UUID}
        assert self.client.get_browser_profile(profile_id=UUID)["id"] == UUID

    @patch.object(ControlBrowserHttpClient, "delete_browser_profile")
    def test_delete_profile(self, mock):
        assert self.client.delete_browser_profile(profile_id=UUID) is True

    # ── Data plane: Session ─────────────────────────────────────────────

    def _start_session(self):
        with patch.object(DataBrowserHttpClient, "start_session") as m:
            m.return_value = {
                "browser_name": "my-browser",
                "session_id": "s-1",
                "streams": {
                    "automation_stream": {"stream_endpoint": "wss://auto.example.com"},
                    "live_view_stream": {"stream_endpoint": "wss://live.example.com"},
                },
            }
            self.client.start_session(
                browser_name="my-browser", session_id="s-1", session_name="my-session",
            )

    def test_start_session(self):
        self._start_session()
        assert self.client.session_id == "s-1"
        assert self.client.browser_name == "my-browser"
        assert self.client.automation_endpoint == "wss://auto.example.com"
        assert self.client.live_view_endpoint == "wss://live.example.com"

    def test_start_session_bad_name(self):
        with self.assertRaises(ValueError):
            self.client.start_session(browser_name="b", session_id="s", session_name="!!")

    def test_start_session_both_domains(self):
        with self.assertRaises(ValueError):
            self.client.start_session(
                browser_name="b", session_id="s", session_name="n",
                allowed_domains=["a.com"], blocked_domains=["b.com"],
            )

    def test_stop_session(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "stop_session"):
            self.client.stop_session()
        assert self.client.session_id is None
        assert self.client.browser_name is None

    def test_stop_session_no_op(self):
        assert self.client.stop_session() is True

    def test_get_session(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "get_session") as m:
            m.return_value = {"session_id": "s-1"}
            assert self.client.get_session()["session_id"] == "s-1"

    def test_get_session_no_session(self):
        with self.assertRaises(ValueError):
            self.client.get_session()

    # ── Data plane: Operations ──────────────────────────────────────────

    def test_invoke(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "invoke") as m:
            m.return_value = {"ok": True}
            assert self.client.invoke(type="navigate", action={"url": "https://x.com"})["ok"] is True

    def test_invoke_bad_type(self):
        self.client._session_id = "s-1"
        self.client._browser_name = "b"
        with self.assertRaises(ValueError):
            self.client.invoke(type="unknown_action", action={})

    def test_invoke_no_session(self):
        with self.assertRaises(ValueError):
            self.client.invoke(type="navigate", action={})

    def test_save_profile(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "save_profile") as m:
            m.return_value = {"ok": True}
            assert self.client.save_profile("p-1")["ok"] is True

    def test_update_stream(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "update_stream") as m:
            m.return_value = {"ok": True}
            assert self.client.update_stream("enabled")["ok"] is True

    def test_update_stream_bad_status(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.update_stream("paused")

    def test_take_control(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "update_stream") as m:
            m.return_value = {}
            self.client.take_control()
            assert m.call_args.kwargs["stream_status"] == "disabled"

    def test_release_control(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "update_stream") as m:
            m.return_value = {}
            self.client.release_control()
            assert m.call_args.kwargs["stream_status"] == "enabled"

    # ── Data plane: Stream URLs ─────────────────────────────────────────

    def test_generate_automation_url(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "build_ws_headers") as m:
            m.return_value = {"X-Auth": "test"}
            url, headers = self.client.generate_automation_url()
            assert url == "wss://auto.example.com"
            assert headers == {"X-Auth": "test"}

    def test_generate_live_view_url(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "build_ws_headers") as m:
            m.return_value = {"X-Auth": "test"}
            url, headers = self.client.generate_live_view_url()
            assert url == "wss://live.example.com"

    # ── Convenience methods ─────────────────────────────────────────────

    def test_left_mouse_click(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "invoke") as m:
            m.return_value = {"ok": True}
            self.client.left_mouse_click(100, 200)
            assert m.call_args.kwargs["type"] == "mouse_click"
            assert m.call_args.kwargs["action"] == {
                "x": 100, "y": 200, "button": "left", "click_count": 1,
            }

    def test_navigate(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "invoke") as m:
            m.return_value = {"ok": True}
            self.client.navigate("https://example.com")
            assert m.call_args.kwargs["type"] == "navigate"
            assert m.call_args.kwargs["action"]["url"] == "https://example.com"

    def test_screenshot_defaults(self):
        self._start_session()
        with patch.object(DataBrowserHttpClient, "invoke") as m:
            m.return_value = {"ok": True}
            self.client.screenshot()
            assert m.call_args.kwargs["type"] == "screenshot"
            a = m.call_args.kwargs["action"]
            assert a["format"] == "jpeg"
            assert a["quality"] == 80
            assert a["full_page"] is False

    def test_screenshot_rejects_bad_format(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.screenshot(format="bmp")

    def test_screenshot_rejects_bad_quality(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.screenshot(quality=0)

    def test_mouse_drag_rejects_bad_button(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.mouse_drag(100, 100, 200, 200, button="bad")

    def test_key_press_rejects_bad_presses(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.key_press("Enter", presses=0)

    def test_key_shortcut_rejects_empty(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.key_shortcut([])

    def test_key_shortcut_rejects_too_many(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.key_shortcut(["a", "b", "c", "d", "e", "f"])

    def test_wait_rejects_bad_duration(self):
        self._start_session()
        with self.assertRaises(ValueError):
            self.client.wait(0.01)
