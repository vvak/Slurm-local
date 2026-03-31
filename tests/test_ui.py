"""Unit tests for slurm_cluster/ui.py"""

import sys
import threading
import time
import pytest
from io import StringIO
from unittest.mock import patch

import slurm_cluster.ui as ui_module
from slurm_cluster.ui import (
    _c,
    green, yellow, red, cyan, bold, dim,
    print_success, print_error, print_warning, print_info, print_step,
    print_banner, print_table,
    Spinner,
)


# ── Color functions ───────────────────────────────────────────────────────────

class TestColorFunctions:
    def test_c_with_color_enabled(self):
        with patch.object(ui_module, "USE_COLOR", True):
            result = _c("32", "hello")
        assert result == "\033[32mhello\033[0m"

    def test_c_without_color(self):
        with patch.object(ui_module, "USE_COLOR", False):
            result = _c("32", "hello")
        assert result == "hello"

    def test_green_with_color(self):
        with patch.object(ui_module, "USE_COLOR", True):
            assert green("ok") == "\033[32mok\033[0m"

    def test_yellow_with_color(self):
        with patch.object(ui_module, "USE_COLOR", True):
            assert yellow("warn") == "\033[33mwarn\033[0m"

    def test_red_with_color(self):
        with patch.object(ui_module, "USE_COLOR", True):
            assert red("err") == "\033[31merr\033[0m"

    def test_cyan_with_color(self):
        with patch.object(ui_module, "USE_COLOR", True):
            assert cyan("info") == "\033[36minfo\033[0m"

    def test_bold_with_color(self):
        with patch.object(ui_module, "USE_COLOR", True):
            assert bold("txt") == "\033[1mtxt\033[0m"

    def test_dim_with_color(self):
        with patch.object(ui_module, "USE_COLOR", True):
            assert dim("txt") == "\033[2mtxt\033[0m"

    def test_all_colors_return_plain_text_without_color(self):
        with patch.object(ui_module, "USE_COLOR", False):
            assert green("x") == "x"
            assert yellow("x") == "x"
            assert red("x") == "x"
            assert cyan("x") == "x"
            assert bold("x") == "x"
            assert dim("x") == "x"


# ── Print helpers ─────────────────────────────────────────────────────────────

class TestPrintHelpers:
    def test_print_success_contains_message(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_success("it worked")
        out = capsys.readouterr().out
        assert "it worked" in out

    def test_print_success_contains_checkmark(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_success("done")
        out = capsys.readouterr().out
        assert "✔" in out

    def test_print_error_goes_to_stderr(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_error("something failed")
        err = capsys.readouterr().err
        assert "something failed" in err

    def test_print_error_contains_x_mark(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_error("oops")
        err = capsys.readouterr().err
        assert "✘" in err

    def test_print_warning_contains_message(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_warning("heads up")
        out = capsys.readouterr().out
        assert "heads up" in out

    def test_print_warning_contains_symbol(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_warning("check this")
        out = capsys.readouterr().out
        assert "⚠" in out

    def test_print_info_contains_message(self, capsys):
        print_info("some info")
        out = capsys.readouterr().out
        assert "some info" in out

    def test_print_step_contains_message(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_step("step one")
        out = capsys.readouterr().out
        assert "step one" in out

    def test_print_step_contains_arrow(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_step("step")
        out = capsys.readouterr().out
        assert "▸" in out

    def test_print_banner_outputs_text(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_banner()
        out = capsys.readouterr().out
        assert "slurm-local" in out or "SLURM" in out


# ── Table ─────────────────────────────────────────────────────────────────────

class TestPrintTable:
    def test_headers_appear_in_output(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_table(["Name", "Value"], [["foo", "bar"]])
        out = capsys.readouterr().out
        assert "Name" in out
        assert "Value" in out

    def test_row_data_appears_in_output(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_table(["Name", "Value"], [["foo", "bar"]])
        out = capsys.readouterr().out
        assert "foo" in out
        assert "bar" in out

    def test_multiple_rows(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_table(["A", "B"], [["x1", "y1"], ["x2", "y2"]])
        out = capsys.readouterr().out
        assert "x1" in out
        assert "x2" in out
        assert "y1" in out
        assert "y2" in out

    def test_status_running_colored_green(self, capsys):
        with patch.object(ui_module, "USE_COLOR", True):
            print_table(["Name", "Status"], [["c1", "running"]])
        out = capsys.readouterr().out
        # running should be wrapped in green ANSI code
        assert "\033[32m" in out

    def test_status_exited_colored_red(self, capsys):
        with patch.object(ui_module, "USE_COLOR", True):
            print_table(["Name", "Status"], [["c1", "exited"]])
        out = capsys.readouterr().out
        assert "\033[31m" in out

    def test_status_not_found_colored_red(self, capsys):
        with patch.object(ui_module, "USE_COLOR", True):
            print_table(["Name", "Status"], [["c1", "not found"]])
        out = capsys.readouterr().out
        assert "\033[31m" in out

    def test_status_other_colored_yellow(self, capsys):
        with patch.object(ui_module, "USE_COLOR", True):
            print_table(["Name", "Status"], [["c1", "paused"]])
        out = capsys.readouterr().out
        assert "\033[33m" in out

    def test_non_status_column_not_colored(self, capsys):
        with patch.object(ui_module, "USE_COLOR", True):
            print_table(["Name", "Role"], [["c1", "running"]])
        out = capsys.readouterr().out
        # "running" in a non-status column should not be colored
        # The header "Role" != "status", so no green wrapping around "running"
        # We check by ensuring the value appears without the green code preceding it
        # (the bold header will have codes, but the cell value should be plain)
        lines = out.splitlines()
        data_lines = [l for l in lines if "running" in l and "Role" not in l and "Name" not in l]
        assert data_lines, "Expected a data line containing 'running'"
        for line in data_lines:
            # Should not have green (32) code immediately before "running"
            assert "\033[32mrunning" not in line

    def test_empty_rows(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_table(["Col1", "Col2"], [])
        out = capsys.readouterr().out
        assert "Col1" in out
        assert "Col2" in out

    def test_separator_line_present(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_table(["A", "B"], [["x", "y"]])
        out = capsys.readouterr().out
        assert "─" in out

    def test_column_width_fits_content(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            print_table(["Short"], [["a very long cell value"]])
        out = capsys.readouterr().out
        assert "a very long cell value" in out


# ── Spinner ───────────────────────────────────────────────────────────────────

class TestSpinner:
    def test_spinner_has_10_frames(self):
        assert len(Spinner.FRAMES) == 10

    def test_spinner_start_stop_no_color(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            spinner = Spinner("loading...")
            spinner.start()
            spinner.stop()
        out = capsys.readouterr().out
        assert "loading..." in out

    def test_spinner_context_manager_no_color(self, capsys):
        with patch.object(ui_module, "USE_COLOR", False):
            with Spinner("working"):
                pass
        out = capsys.readouterr().out
        assert "working" in out

    def test_spinner_context_manager_with_color(self):
        with patch.object(ui_module, "USE_COLOR", True):
            spinner = Spinner("spinning")
            spinner.start()
            time.sleep(0.05)  # let the thread spin briefly
            spinner.stop()
        # No assertion needed — just ensure no exceptions raised

    def test_spinner_thread_stops_on_exit(self):
        with patch.object(ui_module, "USE_COLOR", True):
            spinner = Spinner("test")
            spinner.start()
            assert spinner._thread is not None
            assert spinner._thread.is_alive()
            spinner.stop()
            # After stop, thread should have terminated
            spinner._thread.join(timeout=1)
            assert not spinner._thread.is_alive()

    def test_spinner_stop_event_set_after_stop(self):
        with patch.object(ui_module, "USE_COLOR", False):
            spinner = Spinner("msg")
            spinner.start()
            spinner.stop()
        assert spinner._stop.is_set()
