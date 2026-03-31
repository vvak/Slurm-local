"""Core SLURM cluster management using Docker SDK."""

import os
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from .ui import (
    print_success,
    print_error,
    print_info,
    print_warning,
    print_step,
    print_table,
    Spinner,
)
from .config import generate_slurm_conf, generate_cgroup_conf
from .jobs import SAMPLE_JOBS

DOCKER_DIR = Path(__file__).parent.parent / "docker"
IMAGE_NAME = "slurm-local:latest"


class SlurmCluster:
    def __init__(self, name: str = "slurmlocal", num_workers: int = 2):
        self.name = name
        self.num_workers = num_workers
        self.network_name = f"{name}_net"
        self.controller_name = f"{name}_controller"
        self.worker_names = [f"{name}_worker{i+1}" for i in range(num_workers)]
        self.munge_vol = f"{name}_munge"
        self.conf_vol = f"{name}_conf"
        self.shared_vol = f"{name}_shared"

        self._docker = self._get_docker_client()

    # ── Docker client ─────────────────────────────────────────────────────────

    def _get_docker_client(self):
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return client
        except ImportError:
            print_error("Python 'docker' package not found. Run: pip install docker")
            raise SystemExit(1)
        except Exception as e:
            print_error(
                f"Cannot connect to Docker: {e}\n"
                "Make sure Docker is running and accessible."
            )
            raise SystemExit(1)

    # ── Image ─────────────────────────────────────────────────────────────────

    def build_image(self):
        print_step("Building SLURM Docker image (this takes a few minutes)...")
        try:
            _, logs = self._docker.images.build(
                path=str(DOCKER_DIR),
                tag=IMAGE_NAME,
                rm=True,
            )
            for chunk in logs:
                if "stream" in chunk:
                    line = chunk["stream"].strip()
                    if line:
                        print(f"  {line}")
            print_success(f"Image built: {IMAGE_NAME}")
        except Exception as e:
            print_error(f"Image build failed: {e}")
            raise

    def _ensure_image(self):
        try:
            self._docker.images.get(IMAGE_NAME)
            print_info(f"Using existing image: {IMAGE_NAME}")
        except Exception:
            print_info(f"Image '{IMAGE_NAME}' not found — building now...")
            self.build_image()

    # ── Network & volumes ─────────────────────────────────────────────────────

    def _create_network(self):
        try:
            self._docker.networks.get(self.network_name)
            print_info(f"Network '{self.network_name}' already exists.")
        except Exception:
            self._docker.networks.create(self.network_name, driver="bridge")
            print_info(f"Created network: {self.network_name}")

    def _create_volumes(self):
        for vol_name in [self.munge_vol, self.conf_vol, self.shared_vol]:
            try:
                self._docker.volumes.get(vol_name)
                print_info(f"Volume '{vol_name}' already exists.")
            except Exception:
                self._docker.volumes.create(vol_name)
                print_info(f"Created volume: {vol_name}")

    def _remove_network(self):
        try:
            net = self._docker.networks.get(self.network_name)
            net.remove()
            print_info(f"Removed network: {self.network_name}")
        except Exception:
            pass

    def _remove_volumes(self):
        for vol_name in [self.munge_vol, self.conf_vol, self.shared_vol]:
            try:
                vol = self._docker.volumes.get(vol_name)
                vol.remove(force=True)
                print_info(f"Removed volume: {vol_name}")
            except Exception:
                pass

    # ── Config injection ──────────────────────────────────────────────────────

    def _inject_munge_key(self):
        """Generate a munge key and place it in the munge volume."""
        print_step("Generating munge key...")

        key = os.urandom(1024)

        # -i is required so Docker forwards our stdin pipe into the container.
        # Without it, cat reads EOF immediately and writes a 0-byte file.
        cmd = [
            "docker", "run", "--rm", "-i",
            "-v", f"{self.munge_vol}:/etc/munge",
            "busybox",
            "sh", "-c",
            "cat > /etc/munge/munge.key && chmod 400 /etc/munge/munge.key",
        ]
        result = subprocess.run(cmd, input=key, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to write munge key: {result.stderr.decode().strip()}"
            )

        print_success("Munge key generated.")

    def _inject_slurm_conf(self):
        """Write slurm.conf and cgroup.conf into the config volume."""
        print_step("Writing SLURM configuration...")

        worker_short_names = [f"worker{i+1}" for i in range(self.num_workers)]
        node_names = ",".join(worker_short_names)

        slurm_conf = generate_slurm_conf(
            controller_host="controller",
            node_names=worker_short_names,
            cluster_name=self.name,
        )
        cgroup_conf = generate_cgroup_conf()

        # Write configs into the conf volume
        conf_script = f"""
mkdir -p /etc/slurm
cat > /etc/slurm/slurm.conf << 'SLURMCONF'
{slurm_conf}
SLURMCONF
cat > /etc/slurm/cgroup.conf << 'CGROUPCONF'
{cgroup_conf}
CGROUPCONF
chmod 644 /etc/slurm/slurm.conf /etc/slurm/cgroup.conf
"""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.conf_vol}:/etc/slurm",
            "busybox",
            "sh", "-c", conf_script,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print_success("SLURM configuration written.")

    # ── Container management ──────────────────────────────────────────────────

    def _common_volumes(self):
        return {
            self.munge_vol: {"bind": "/etc/munge", "mode": "rw"},
            self.conf_vol: {"bind": "/etc/slurm", "mode": "ro"},
            self.shared_vol: {"bind": "/shared", "mode": "rw"},
        }

    def _start_controller(self):
        print_step("Starting SLURM controller...")
        try:
            existing = self._docker.containers.get(self.controller_name)
            if existing.status == "running":
                print_info("Controller already running.")
                return
            existing.remove(force=True)
        except Exception:
            pass

        container = self._docker.containers.run(
            IMAGE_NAME,
            name=self.controller_name,
            hostname="controller",
            environment={
                "SLURM_ROLE": "controller",
                "SLURM_NODE_NAME": "controller",
            },
            volumes=self._common_volumes(),
            network=self.network_name,
            detach=True,
            privileged=True,
        )
        print_success(f"Controller started: {self.controller_name}")
        return container

    def _start_worker(self, worker_name: str, short_name: str):
        try:
            existing = self._docker.containers.get(worker_name)
            if existing.status == "running":
                print_info(f"Worker '{worker_name}' already running.")
                return
            existing.remove(force=True)
        except Exception:
            pass

        container = self._docker.containers.run(
            IMAGE_NAME,
            name=worker_name,
            hostname=short_name,
            environment={
                "SLURM_ROLE": "worker",
                "SLURM_NODE_NAME": short_name,
            },
            volumes=self._common_volumes(),
            network=self.network_name,
            detach=True,
            privileged=True,
        )
        print_success(f"Worker started: {worker_name} (hostname: {short_name})")
        return container

    def _wait_for_cluster(self, timeout: int = 120):
        print_step("Waiting for cluster to become ready...")
        deadline = time.time() + timeout
        _resume_attempted = False
        with Spinner("Waiting for slurmctld and slurmd daemons...") as sp:
            while time.time() < deadline:
                # Bail out early if the controller container itself has stopped.
                if not self._container_running(self.controller_name):
                    sp.stop()
                    print_error("Controller container stopped unexpectedly.")
                    self._print_container_logs(self.controller_name)
                    return False

                try:
                    # %n (lowercase) emits one line per node, making it easy to count.
                    result = self._exec_on_controller(
                        "sinfo --noheader -o '%n %T' 2>/dev/null", raise_on_error=False
                    )
                    if result:
                        idle_count = sum(
                            1 for line in result.splitlines()
                            if line.strip() and line.strip().split()[-1] == "idle"
                        )
                        if idle_count >= self.num_workers:
                            sp.stop()
                            print_success("Cluster is ready!")
                            return True
                    # Not all nodes idle yet — nudge any that are down/drain/unknown.
                    if not _resume_attempted:
                        node_list = ",".join(f"worker{i+1}" for i in range(self.num_workers))
                        self._exec_on_controller(
                            f"scontrol update NodeName={node_list} State=RESUME 2>/dev/null || true",
                            raise_on_error=False,
                        )
                        _resume_attempted = True
                except Exception:
                    pass
                time.sleep(3)
        print_warning("Timed out waiting for cluster — it may still be starting.")
        print_info("  Check logs:   slurm-local logs")
        print_info("  Check status: slurm-local status")
        return False

    def _print_container_logs(self, name: str, tail: int = 30):
        """Print the last N log lines from a container to help diagnose failures."""
        try:
            c = self._docker.containers.get(name)
            logs = c.logs(tail=tail).decode("utf-8", errors="replace").strip()
            if logs:
                print_info(f"\nLast {tail} lines from '{name}' logs:")
                for line in logs.splitlines():
                    print(f"    {line}")
        except Exception:
            pass

    # ── Exec helpers ─────────────────────────────────────────────────────────

    def _exec_on_controller(self, cmd: str, raise_on_error: bool = True) -> str:
        result = subprocess.run(
            ["docker", "exec", self.controller_name, "bash", "-c", cmd],
            capture_output=True,
            text=True,
        )
        if raise_on_error and result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def _container_running(self, name: str) -> bool:
        try:
            c = self._docker.containers.get(name)
            return c.status == "running"
        except Exception:
            return False

    def _assert_cluster_running(self):
        if not self._container_running(self.controller_name):
            print_error("Cluster is not running. Start it with: slurm-local up")
            raise SystemExit(1)

    # ── Public commands ───────────────────────────────────────────────────────

    def up(self):
        print_info(f"Starting SLURM cluster '{self.name}' with {self.num_workers} worker(s)...")

        self._ensure_image()
        self._create_network()
        self._create_volumes()
        self._inject_munge_key()
        self._inject_slurm_conf()
        self._start_controller()

        print_step("Starting worker nodes...")
        for i, worker_name in enumerate(self.worker_names):
            short_name = f"worker{i+1}"
            self._start_worker(worker_name, short_name)

        ready = self._wait_for_cluster()

        print()
        if ready:
            print_success("🎉 SLURM cluster is up!")
            print_info("  Open a shell:       slurm-local shell")
            print_info("  Submit sample jobs: slurm-local submit")
            print_info("  Check status:       slurm-local status")
            print_info("  Tear down:          slurm-local down")
        else:
            print_error("Cluster did not become ready. Run 'slurm-local logs' to diagnose.")
            raise SystemExit(1)

    def down(self):
        print_info(f"Stopping cluster '{self.name}'...")
        all_containers = [self.controller_name] + self.worker_names

        for cname in all_containers:
            try:
                c = self._docker.containers.get(cname)
                c.remove(force=True)
                print_info(f"Removed: {cname}")
            except Exception:
                pass

        self._remove_network()
        self._remove_volumes()
        print_success("Cluster stopped and removed.")

    def status(self):
        self._assert_cluster_running()

        print_info(f"\n── Cluster: {self.name} ──────────────────────────────")

        # Container status
        rows = []
        all_containers = [self.controller_name] + self.worker_names
        for cname in all_containers:
            try:
                c = self._docker.containers.get(cname)
                role = "controller" if cname == self.controller_name else "worker"
                rows.append([cname, role, c.status, c.attrs["NetworkSettings"]["Networks"].get(self.network_name, {}).get("IPAddress", "N/A")])
            except Exception:
                rows.append([cname, "?", "not found", "N/A"])

        print_table(["Container", "Role", "Status", "IP"], rows)

        # SLURM info
        print_info("\n── SLURM Node Info (sinfo) ─────────────────────────")
        sinfo = self._exec_on_controller("sinfo 2>/dev/null || echo '(sinfo unavailable)'", raise_on_error=False)
        print(sinfo)

        print_info("\n── Job Queue (squeue) ──────────────────────────────")
        squeue = self._exec_on_controller("squeue 2>/dev/null || echo '(no jobs)'", raise_on_error=False)
        print(squeue or "(empty)")

    def submit_sample_job(self, job_name: str = "all"):
        self._assert_cluster_running()

        jobs_to_run = SAMPLE_JOBS if job_name == "all" else {
            k: v for k, v in SAMPLE_JOBS.items() if k == job_name
        }

        if not jobs_to_run:
            print_error(f"Unknown job: {job_name}")
            return

        print_info(f"\nSubmitting {len(jobs_to_run)} sample job(s) to SLURM...\n")

        for jname, job in jobs_to_run.items():
            print_step(f"Submitting: {jname} — {job['description']}")

            # Write script to shared volume via controller
            script_path = f"/shared/{jname}.sh"
            escaped = job["script"].replace("'", "'\\''")
            write_cmd = f"cat > {script_path} << 'JOBSCRIPT'\n{job['script']}\nJOBSCRIPT\nchmod +x {script_path}"
            self._exec_on_controller(write_cmd)

            # Submit
            result = self._exec_on_controller(
                f"sbatch {script_path} 2>&1", raise_on_error=False
            )
            if "Submitted" in result:
                print_success(f"  {result}")
            else:
                print_warning(f"  {result}")

        print_info("\nCheck job status with: slurm-local status")
        print_info("View output files in the shared volume (exec into controller and check /shared/)")

    def shell(self):
        self._assert_cluster_running()
        print_info(f"Opening shell on {self.controller_name}...")
        print_info("  Try: sinfo, squeue, sbatch /shared/<job>.sh, srun hostname")
        print_info("  Type 'exit' to leave.\n")
        os.execvp("docker", ["docker", "exec", "-it", self.controller_name, "bash"])

    def logs(self, node: Optional[str] = None):
        self._assert_cluster_running()
        if node:
            # Find matching container
            target = None
            for cname in [self.controller_name] + self.worker_names:
                if node in cname:
                    target = cname
                    break
            if not target:
                print_error(f"No container matching '{node}' found.")
                return
        else:
            target = self.controller_name

        print_info(f"Logs for {target} (Ctrl+C to stop):\n")
        os.execvp("docker", ["docker", "logs", "-f", "--tail", "100", target])
