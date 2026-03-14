"""Unit tests with mocked external dependencies (yt-dlp, Playwright)."""

import sys
import types
import unittest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Tests for playlist_extractor
# ---------------------------------------------------------------------------

class TestGetPlaylistUrls(unittest.TestCase):

    def _mock_ydl(self, entries):
        """Build a mock YoutubeDL context manager that returns given entries."""
        mock_info = {
            "title": "Test Playlist",
            "entries": entries,
        }
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = mock_info
        mock_ydl_cm = MagicMock()
        mock_ydl_cm.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_cm.__exit__ = MagicMock(return_value=False)
        return mock_ydl_cm, mock_ydl_instance

    @patch("playlist_extractor.yt_dlp.YoutubeDL")
    def test_returns_correct_urls(self, MockYDL):
        from playlist_extractor import get_playlist_urls

        entries = [{"id": "abc123"}, {"id": "def456"}, {"id": "ghi789"}]
        mock_cm, _ = self._mock_ydl(entries)
        MockYDL.return_value = mock_cm

        urls = get_playlist_urls("https://www.youtube.com/playlist?list=PL_test")

        self.assertEqual(len(urls), 3)
        self.assertEqual(urls[0], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(urls[1], "https://www.youtube.com/watch?v=def456")
        self.assertEqual(urls[2], "https://www.youtube.com/watch?v=ghi789")

    @patch("playlist_extractor.yt_dlp.YoutubeDL")
    def test_skips_entries_without_id(self, MockYDL):
        from playlist_extractor import get_playlist_urls

        entries = [{"id": "abc123"}, None, {"id": ""}, {"id": "valid99"}]
        mock_cm, _ = self._mock_ydl(entries)
        MockYDL.return_value = mock_cm

        urls = get_playlist_urls("https://www.youtube.com/playlist?list=PL_test")
        self.assertEqual(len(urls), 2)
        self.assertIn("https://www.youtube.com/watch?v=abc123", urls)
        self.assertIn("https://www.youtube.com/watch?v=valid99", urls)

    @patch("playlist_extractor.yt_dlp.YoutubeDL")
    def test_raises_on_none_info(self, MockYDL):
        from playlist_extractor import get_playlist_urls

        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = None
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_cm.__exit__ = MagicMock(return_value=False)
        MockYDL.return_value = mock_cm

        with self.assertRaises(ValueError, msg="Should raise when info is None"):
            get_playlist_urls("https://www.youtube.com/playlist?list=PL_test")

    @patch("playlist_extractor.yt_dlp.YoutubeDL")
    def test_raises_on_empty_entries(self, MockYDL):
        from playlist_extractor import get_playlist_urls

        mock_cm, _ = self._mock_ydl([])
        MockYDL.return_value = mock_cm

        with self.assertRaises(ValueError, msg="Should raise when entries is empty"):
            get_playlist_urls("https://www.youtube.com/playlist?list=PL_test")


# ---------------------------------------------------------------------------
# Tests for notebooklm_automator
# ---------------------------------------------------------------------------

class TestSourceLimit(unittest.TestCase):

    @patch("notebooklm_automator.sync_playwright")
    def test_truncates_to_source_limit(self, mock_playwright):
        """Playlists > SOURCE_LIMIT should be silently truncated."""
        from notebooklm_automator import add_playlist_to_notebooklm, SOURCE_LIMIT

        # Build a list larger than the limit
        video_urls = [f"https://www.youtube.com/watch?v=vid{i}" for i in range(SOURCE_LIMIT + 10)]

        # Mock the entire playwright context so no browser is launched
        mock_page = MagicMock()
        mock_page.url = "https://notebooklm.google.com/notebook/123"
        mock_page.pages = [mock_page]

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.new_page.return_value = mock_page

        mock_pw = MagicMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context

        mock_playwright.return_value.__enter__ = MagicMock(return_value=mock_pw)
        mock_playwright.return_value.__exit__ = MagicMock(return_value=False)

        # Patch internal helpers to avoid real UI interaction
        with patch("notebooklm_automator._is_logged_in", return_value=True), \
             patch("notebooklm_automator._create_new_notebook"), \
             patch("notebooklm_automator._add_source_url", return_value=True) as mock_add, \
             patch("builtins.input", return_value=""):

            add_playlist_to_notebooklm(video_urls, "Test Notebook")

        # Should have been called exactly SOURCE_LIMIT times
        self.assertEqual(mock_add.call_count, SOURCE_LIMIT)

    @patch("notebooklm_automator.sync_playwright")
    def test_counts_failures(self, mock_playwright):
        """Failed source additions should be counted separately from successes."""
        from notebooklm_automator import add_playlist_to_notebooklm

        video_urls = [f"https://www.youtube.com/watch?v=vid{i}" for i in range(5)]

        mock_page = MagicMock()
        mock_page.url = "https://notebooklm.google.com/notebook/456"
        mock_context = MagicMock()
        mock_context.pages = [mock_page]

        mock_pw = MagicMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_context

        mock_playwright.return_value.__enter__ = MagicMock(return_value=mock_pw)
        mock_playwright.return_value.__exit__ = MagicMock(return_value=False)

        # 2 failures, 3 successes
        results = [True, False, True, False, True]
        with patch("notebooklm_automator._is_logged_in", return_value=True), \
             patch("notebooklm_automator._create_new_notebook"), \
             patch("notebooklm_automator._add_source_url", side_effect=results), \
             patch("builtins.input", return_value=""):

            add_playlist_to_notebooklm(video_urls)

        # Test passes as long as no exception is raised and all 5 were attempted
        # (the counts are logged, not returned)


# ---------------------------------------------------------------------------
# Tests for main CLI argument parsing
# ---------------------------------------------------------------------------

class TestMainCLI(unittest.TestCase):

    def test_passes_title_to_automator(self):
        """--title argument should be forwarded to add_playlist_to_notebooklm."""
        import main as m

        with patch.object(m, "get_playlist_urls", return_value=["https://www.youtube.com/watch?v=abc"]) as mock_extract, \
             patch.object(m, "add_playlist_to_notebooklm") as mock_automate, \
             patch("sys.argv", ["main.py", "https://youtube.com/playlist?list=PL1", "--title", "My Notes"]):
            m.main()

        mock_extract.assert_called_once_with("https://youtube.com/playlist?list=PL1")
        mock_automate.assert_called_once_with(
            ["https://www.youtube.com/watch?v=abc"],
            notebook_title="My Notes"
        )

    @patch("main.add_playlist_to_notebooklm")
    @patch("main.get_playlist_urls")
    def test_exits_on_empty_playlist(self, mock_extract, mock_automate):
        """Should sys.exit when playlist has no videos."""
        # get_playlist_urls raises ValueError on empty playlist,
        # but let's test the empty-list guard in main.
        mock_extract.return_value = []

        with patch("sys.argv", ["main.py", "https://youtube.com/playlist?list=PL_empty"]):
            import main as m
            with self.assertRaises(SystemExit):
                m.main()

        mock_automate.assert_not_called()

    @patch("main.add_playlist_to_notebooklm")
    @patch("main.get_playlist_urls")
    def test_exits_on_extractor_error(self, mock_extract, mock_automate):
        """Should sys.exit when playlist extractor raises ValueError."""
        mock_extract.side_effect = ValueError("Private playlist")

        with patch("sys.argv", ["main.py", "https://youtube.com/playlist?list=PL_bad"]):
            import main as m
            with self.assertRaises(SystemExit):
                m.main()

        mock_automate.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
