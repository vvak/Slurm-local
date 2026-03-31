# slurm-local

A Python CLI tool that spins up a fully functional **local SLURM cluster** inside Docker containers — for testing job scripts, partitions, dependencies, and SLURM configurations without needing access to a real HPC cluster.

---

## Features

- **One command startup** — `slurm-local up` builds the image and launches the cluster
- **Configurable worker nodes** — spin up 1–N worker nodes
- **Auto-generated `slurm.conf`** — sensible defaults, ready to customise
- **5 sample workloads** included:
  - `hello` — simple single-task job
  - `array` — job array (5 tasks)
  - `sleep` — long-running job (good for testing `squeue`/`scancel`)
  - `resource` — multi-task job spread across nodes
  - `deps` — job dependency chain (B waits for A)
- **Interactive shell** — `slurm-local shell` drops you into the controller
- **Live logs** — `slurm-local logs` tails container output

---

## Requirements

- **Python 3.8+**
- **Docker** (running and accessible to your user)
- Internet access to pull `rockylinux:9` on first run

---

## Installation

```bash
# Clone / download the project
cd slurm-local

# Install (creates 'slurm-local' command)
pip install -e .

# Or run directly without installing:
python slurm-local --help
```

---

## Quick Start

```bash
# Start a cluster with 2 worker nodes (default)
slurm-local up

# Start with 4 workers
slurm-local up --nodes 4

# Check cluster and job status
slurm-local status

# Submit all sample workloads
slurm-local submit

# Submit a specific job
slurm-local submit --job array

# Open an interactive shell on the controller
slurm-local shell

# Inside the shell — try SLURM commands:
sinfo                          # see nodes and partitions
squeue                         # see running/pending jobs
sbatch /shared/hello.sh        # submit a job
srun --ntasks=2 hostname       # run interactively
scancel <jobid>                # cancel a job

# View logs
slurm-local logs               # controller logs
slurm-local logs --node worker1

# Tear everything down
slurm-local down
```

---

## Sample Jobs

| Job name | Description |
|---|---|
| `hello` | Basic job — prints environment, node info |
| `array` | Array job with 5 tasks (`--array=1-5`) |
| `sleep` | Runs for 5 minutes — good for `squeue`/`scancel` testing |
| `resource` | Requests 4 tasks, uses `srun` to print node names |
| `deps` | Submits two jobs where B depends on A (`--dependency=afterok`) |

Output files are written to `/shared/` inside the cluster (a Docker volume shared across all nodes).

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Docker Network                     │
│                                                     │
│  ┌──────────────────┐    ┌──────────────┐           │
│  │   controller     │    │   worker1    │           │
│  │  (slurmctld)     │◄──►│  (slurmd)    │           │
│  │                  │    └──────────────┘           │
│  │                  │    ┌──────────────┐           │
│  │                  │◄──►│   worker2    │           │
│  └──────────────────┘    │  (slurmd)    │           │
│                           └──────────────┘           │
│                                                     │
│  Shared volumes:                                    │
│    munge_vol  → /etc/munge  (auth key)              │
│    conf_vol   → /etc/slurm  (slurm.conf)            │
│    shared_vol → /shared     (job scripts + output)  │
└─────────────────────────────────────────────────────┘
```

Each container runs Rocky Linux 9 with SLURM and Munge installed from the EPEL repository.

---

## Customising SLURM Config

The generated `slurm.conf` lives in a Docker volume (`slurmlocal_conf`). To customise it:

1. `slurm-local shell`
2. Inside: `cat /etc/slurm/slurm.conf` to view current config
3. Edit `slurm_cluster/config.py` to change defaults before `up`

Or mount your own config file by modifying the volume mounts in `cluster.py`.

---

## Commands Reference

```
slurm-local up [--nodes N] [--cluster-name NAME]
slurm-local down [--cluster-name NAME]
slurm-local status [--cluster-name NAME]
slurm-local submit [--job JOB] [--cluster-name NAME]
slurm-local shell [--cluster-name NAME]
slurm-local logs [--node NODE] [--cluster-name NAME]
slurm-local build
```

---

## Known Limitations

| Limitation | Notes |
|---|---|
| No real CPU/memory enforcement | SLURM's cgroups don't truly isolate in Docker |
| No GPU support | Requires `--gpus` and nvidia-container-toolkit if needed |
| No MPI fabric | TCP only; InfiniBand not available |
| `systemd` not running | Daemons are started directly in the entrypoint |
| ARM (Apple M-series) | Rocky Linux 9 has ARM images — should work on M1/M2 Macs |

---

## Project Structure

```
slurm-local/
├── slurm-local          # Main entry point script
├── setup.py             # pip install config
├── README.md
├── docker/
│   ├── Dockerfile       # Rocky Linux 9 + SLURM + Munge
│   └── entrypoint.sh    # Container startup script
└── slurm_cluster/
    ├── __init__.py
    ├── cli.py           # argparse CLI commands
    ├── cluster.py       # Docker cluster management
    ├── config.py        # slurm.conf / cgroup.conf generators
    ├── jobs.py          # Sample job script definitions
    └── ui.py            # Terminal colors, spinner, tables
```
