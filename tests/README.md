# Tests

Unit tests for `slurm-local`. All tests run without Docker or a live SLURM cluster — Docker SDK calls are mocked.

## Running

```bash
python3 -m pytest tests/
```

Verbose output:

```bash
python3 -m pytest tests/ -v
```

## Structure

| File | What it tests |
|------|---------------|
| `test_config.py` | `generate_slurm_conf()` and `generate_cgroup_conf()` — config content, node/partition definitions, auth settings |
| `test_jobs.py` | `SAMPLE_JOBS` — structure validation, SBATCH directives, per-job assertions |
| `test_ui.py` | Color functions, print helpers, `print_table` coloring/layout, `Spinner` threading |
| `test_cluster.py` | `SlurmCluster` — naming, Docker client errors, volume mounts, container checks, exec behavior, network/volume CRUD, job submission, logs, teardown |
| `test_cli.py` | Argument parsing, command dispatch to cluster methods, error handling |

## Dependencies

```bash
python3 -m pip install pytest
```

The `docker` package is also required (already listed in `install_requires`) but is mocked in all tests, so no Docker daemon is needed.
