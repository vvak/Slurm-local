"""Unit tests for slurm_cluster/cli.py"""

import sys
import pytest
from unittest.mock import MagicMock, patch, call
from slurm_cluster import cli


def make_mock_cluster():
    mock = MagicMock()
    return mock


def parse(args):
    """Parse args without executing — returns the parsed namespace."""
    with patch("slurm_cluster.cli.print_banner"):
        parser = _build_parser()
    return parser.parse_args(args)


def _build_parser():
    """Rebuild the parser from cli.main without calling args.func."""
    import argparse
    parser = argparse.ArgumentParser(prog="slurm-local")
    parser.add_argument("--cluster-name", default="slurmlocal")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    p_up = subparsers.add_parser("up")
    p_up.add_argument("--nodes", type=int, default=2, metavar="N")
    p_up.set_defaults(func=cli.cmd_up)

    p_down = subparsers.add_parser("down")
    p_down.set_defaults(func=cli.cmd_down)

    p_status = subparsers.add_parser("status")
    p_status.set_defaults(func=cli.cmd_status)

    p_submit = subparsers.add_parser("submit")
    p_submit.add_argument("--job", default="all",
                          choices=["all", "hello", "array", "deps", "resource", "sleep"])
    p_submit.set_defaults(func=cli.cmd_submit)

    p_shell = subparsers.add_parser("shell")
    p_shell.set_defaults(func=cli.cmd_shell)

    p_logs = subparsers.add_parser("logs")
    p_logs.add_argument("--node", default=None, metavar="NODE")
    p_logs.set_defaults(func=cli.cmd_logs)

    p_build = subparsers.add_parser("build")
    p_build.set_defaults(func=cli.cmd_build)

    return parser


# ── Argument parsing ──────────────────────────────────────────────────────────

class TestArgumentParsing:
    def test_up_default_nodes(self):
        args = parse(["up"])
        assert args.nodes == 2

    def test_up_custom_nodes(self):
        args = parse(["up", "--nodes", "4"])
        assert args.nodes == 4

    def test_default_cluster_name(self):
        args = parse(["up"])
        assert args.cluster_name == "slurmlocal"

    def test_custom_cluster_name(self):
        args = parse(["--cluster-name", "mycluster", "up"])
        assert args.cluster_name == "mycluster"

    def test_submit_default_job(self):
        args = parse(["submit"])
        assert args.job == "all"

    def test_submit_specific_job(self):
        for job in ["hello", "array", "deps", "resource", "sleep"]:
            args = parse(["submit", "--job", job])
            assert args.job == job

    def test_submit_invalid_job_raises(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["submit", "--job", "invalid"])

    def test_logs_default_node_is_none(self):
        args = parse(["logs"])
        assert args.node is None

    def test_logs_with_node(self):
        args = parse(["logs", "--node", "worker1"])
        assert args.node == "worker1"

    def test_command_is_set(self):
        args = parse(["up"])
        assert args.command == "up"


# ── Command dispatch ──────────────────────────────────────────────────────────

class TestCommandDispatch:
    def _run_cmd(self, argv):
        with patch("slurm_cluster.cli.print_banner"):
            with patch("slurm_cluster.cluster.SlurmCluster._get_docker_client", return_value=MagicMock()):
                with patch.object(sys, "argv", ["slurm-local"] + argv):
                    cli.main()

    def test_cmd_up_calls_cluster_up(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "up"]):
                    cli.main()
        mock_cluster.up.assert_called_once()

    def test_cmd_up_passes_nodes(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster) as MockCls:
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "up", "--nodes", "3"]):
                    cli.main()
        MockCls.assert_called_once_with(name="slurmlocal", num_workers=3)

    def test_cmd_down_calls_cluster_down(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "down"]):
                    cli.main()
        mock_cluster.down.assert_called_once()

    def test_cmd_status_calls_cluster_status(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "status"]):
                    cli.main()
        mock_cluster.status.assert_called_once()

    def test_cmd_submit_calls_submit_sample_job(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "submit", "--job", "hello"]):
                    cli.main()
        mock_cluster.submit_sample_job.assert_called_once_with(job_name="hello")

    def test_cmd_shell_calls_cluster_shell(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "shell"]):
                    cli.main()
        mock_cluster.shell.assert_called_once()

    def test_cmd_logs_calls_cluster_logs(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "logs", "--node", "worker2"]):
                    cli.main()
        mock_cluster.logs.assert_called_once_with(node="worker2")

    def test_cmd_build_calls_build_image(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "build"]):
                    cli.main()
        mock_cluster.build_image.assert_called_once()

    def test_cluster_name_passed_through(self):
        mock_cluster = make_mock_cluster()
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster) as MockCls:
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "--cluster-name", "custom", "down"]):
                    cli.main()
        MockCls.assert_called_once_with(name="custom")


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_keyboard_interrupt_exits_with_1(self):
        mock_cluster = make_mock_cluster()
        mock_cluster.up.side_effect = KeyboardInterrupt
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "up"]):
                    with pytest.raises(SystemExit) as exc_info:
                        cli.main()
        assert exc_info.value.code == 1

    def test_generic_exception_exits_with_1(self):
        mock_cluster = make_mock_cluster()
        mock_cluster.down.side_effect = RuntimeError("something broke")
        with patch("slurm_cluster.cli.SlurmCluster", return_value=mock_cluster):
            with patch("slurm_cluster.cli.print_banner"):
                with patch.object(sys, "argv", ["slurm-local", "down"]):
                    with pytest.raises(SystemExit) as exc_info:
                        cli.main()
        assert exc_info.value.code == 1

    def test_missing_subcommand_exits(self):
        with patch("slurm_cluster.cli.print_banner"):
            with patch.object(sys, "argv", ["slurm-local"]):
                with pytest.raises(SystemExit):
                    cli.main()
