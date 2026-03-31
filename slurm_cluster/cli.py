"""CLI entry point for slurm-local."""

import argparse
import sys
from .cluster import SlurmCluster
from .ui import print_banner, print_success, print_error, print_info, print_warning


def cmd_up(args):
    cluster = SlurmCluster(name=args.cluster_name, num_workers=args.nodes)
    cluster.up()


def cmd_down(args):
    cluster = SlurmCluster(name=args.cluster_name)
    cluster.down()


def cmd_status(args):
    cluster = SlurmCluster(name=args.cluster_name)
    cluster.status()


def cmd_submit(args):
    cluster = SlurmCluster(name=args.cluster_name)
    cluster.submit_sample_job(job_name=args.job)


def cmd_shell(args):
    cluster = SlurmCluster(name=args.cluster_name)
    cluster.shell()


def cmd_logs(args):
    cluster = SlurmCluster(name=args.cluster_name)
    cluster.logs(node=args.node)


def cmd_build(args):
    cluster = SlurmCluster(name="build")
    cluster.build_image()


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        prog="slurm-local",
        description="Spin up a local Docker-based SLURM cluster for testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  slurm-local up                        # Start cluster with 2 worker nodes
  slurm-local up --nodes 4              # Start with 4 worker nodes
  slurm-local status                    # Show cluster and job status
  slurm-local submit                    # Submit all sample workloads
  slurm-local submit --job array        # Submit only the array job
  slurm-local shell                     # Open shell on controller
  slurm-local logs                      # Show controller logs
  slurm-local logs --node worker1       # Show worker1 logs
  slurm-local down                      # Tear down the cluster
        """,
    )

    parser.add_argument(
        "--cluster-name",
        default="slurmlocal",
        help="Name prefix for cluster containers (default: slurmlocal)",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # up
    p_up = subparsers.add_parser("up", help="Start the SLURM cluster")
    p_up.add_argument(
        "--nodes",
        type=int,
        default=2,
        metavar="N",
        help="Number of worker nodes (default: 2)",
    )
    p_up.set_defaults(func=cmd_up)

    # down
    p_down = subparsers.add_parser("down", help="Stop and remove the cluster")
    p_down.set_defaults(func=cmd_down)

    # status
    p_status = subparsers.add_parser("status", help="Show cluster and job status")
    p_status.set_defaults(func=cmd_status)

    # submit
    p_submit = subparsers.add_parser("submit", help="Submit sample workloads")
    p_submit.add_argument(
        "--job",
        default="all",
        choices=["all", "hello", "array", "deps", "resource", "sleep"],
        help="Which sample job to submit (default: all)",
    )
    p_submit.set_defaults(func=cmd_submit)

    # shell
    p_shell = subparsers.add_parser("shell", help="Open a shell on the controller node")
    p_shell.set_defaults(func=cmd_shell)

    # logs
    p_logs = subparsers.add_parser("logs", help="Show container logs")
    p_logs.add_argument(
        "--node",
        default=None,
        metavar="NODE",
        help="Node name to show logs for (default: controller)",
    )
    p_logs.set_defaults(func=cmd_logs)

    # build
    p_build = subparsers.add_parser("build", help="(Re)build the Docker image")
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args()

    try:
        args.func(args)
    except KeyboardInterrupt:
        print_warning("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)
