"""Unit tests for slurm_cluster/jobs.py"""

import pytest
from slurm_cluster.jobs import SAMPLE_JOBS

EXPECTED_JOB_NAMES = {"hello", "array", "sleep", "resource", "deps", "multinode"}


class TestSampleJobsStructure:
    def test_sample_jobs_is_dict(self):
        assert isinstance(SAMPLE_JOBS, dict)

    def test_expected_jobs_present(self):
        assert set(SAMPLE_JOBS.keys()) == EXPECTED_JOB_NAMES

    def test_each_job_has_description(self):
        for name, job in SAMPLE_JOBS.items():
            assert "description" in job, f"Job '{name}' missing 'description'"
            assert isinstance(job["description"], str)
            assert len(job["description"]) > 0

    def test_each_job_has_script(self):
        for name, job in SAMPLE_JOBS.items():
            assert "script" in job, f"Job '{name}' missing 'script'"
            assert isinstance(job["script"], str)

    def test_each_script_starts_with_shebang(self):
        for name, job in SAMPLE_JOBS.items():
            script = job["script"].lstrip()
            assert script.startswith("#!/bin/bash"), (
                f"Job '{name}' script does not start with #!/bin/bash"
            )

    def test_each_script_has_job_name_directive(self):
        for name, job in SAMPLE_JOBS.items():
            # deps uses inline --job-name= in sbatch calls, not SBATCH directives
            if name == "deps":
                assert "--job-name=" in job["script"], (
                    f"Job '{name}' script missing --job-name argument"
                )
            else:
                assert "#SBATCH --job-name=" in job["script"], (
                    f"Job '{name}' script missing --job-name directive"
                )

    def test_each_script_has_output_directive(self):
        for name, job in SAMPLE_JOBS.items():
            # deps job uses sbatch --wrap internally, output is per-wrapped job
            if name == "deps":
                continue
            assert "#SBATCH --output=" in job["script"], (
                f"Job '{name}' script missing --output directive"
            )

    def test_output_paths_in_shared(self):
        for name, job in SAMPLE_JOBS.items():
            if "#SBATCH --output=" in job["script"]:
                # Find the output line and check it uses /shared/
                for line in job["script"].splitlines():
                    if line.startswith("#SBATCH --output="):
                        assert "/shared/" in line, (
                            f"Job '{name}' output not in /shared/: {line}"
                        )


class TestIndividualJobs:
    def test_hello_job(self):
        job = SAMPLE_JOBS["hello"]
        assert "ntasks=1" in job["script"]
        assert "--partition=debug" in job["script"]
        assert "--mem=64M" in job["script"]

    def test_array_job_has_array_directive(self):
        job = SAMPLE_JOBS["array"]
        assert "--array=1-5" in job["script"]

    def test_array_job_output_uses_array_placeholders(self):
        job = SAMPLE_JOBS["array"]
        # Array output should use %A (job ID) and %a (task ID)
        assert "%A" in job["script"]
        assert "%a" in job["script"]

    def test_sleep_job_is_long_running(self):
        job = SAMPLE_JOBS["sleep"]
        # Should have a time limit longer than the hello job (which is 1 min)
        assert "--time=00:10:00" in job["script"]

    def test_resource_job_requests_multiple_tasks(self):
        job = SAMPLE_JOBS["resource"]
        assert "--ntasks=4" in job["script"]

    def test_resource_job_uses_srun(self):
        job = SAMPLE_JOBS["resource"]
        assert "srun" in job["script"]

    def test_deps_job_submits_two_jobs(self):
        job = SAMPLE_JOBS["deps"]
        # Should have two sbatch calls
        sbatch_count = job["script"].count("sbatch")
        assert sbatch_count >= 2

    def test_deps_job_uses_afterok_dependency(self):
        job = SAMPLE_JOBS["deps"]
        assert "--dependency=afterok:" in job["script"]

    def test_deps_job_chains_job_b_on_job_a(self):
        job = SAMPLE_JOBS["deps"]
        # Job B depends on JOB_A variable
        assert "${JOB_A}" in job["script"] or "$JOB_A" in job["script"]


class TestMultinodeJob:
    def setup_method(self):
        self.job = SAMPLE_JOBS["multinode"]
        self.script = self.job["script"]

    # ── Structure ─────────────────────────────────────────────────────────────

    def test_requests_multiple_nodes(self):
        assert "--nodes=2" in self.script

    def test_requests_tasks_per_node(self):
        assert "--ntasks-per-node=2" in self.script

    def test_output_in_shared_subdir(self):
        # Output should go to /shared/ (job-specific subdir created at runtime)
        for line in self.script.splitlines():
            if line.startswith("#SBATCH --output="):
                assert "/shared/" in line
                break
        else:
            pytest.fail("No #SBATCH --output= directive found")

    def test_uses_srun_for_parallel_tasks(self):
        assert self.script.count("srun") >= 3  # one per parallel phase

    def test_creates_output_directory(self):
        assert 'mkdir -p "$OUTDIR"' in self.script

    def test_output_dir_keyed_on_job_id(self):
        assert "SLURM_JOB_ID" in self.script
        assert "multinode_${SLURM_JOB_ID}" in self.script

    # ── Phase 1: Discovery ────────────────────────────────────────────────────

    def test_phase1_reports_hostname(self):
        assert "hostname" in self.script

    def test_phase1_reports_local_task_id(self):
        assert "SLURM_LOCALID" in self.script

    def test_phase1_reports_global_task_id(self):
        assert "SLURM_PROCID" in self.script

    def test_phase1_writes_discovery_file(self):
        assert "phase1_discovery.txt" in self.script

    # ── Phase 2: CPU work ─────────────────────────────────────────────────────

    def test_phase2_uses_sieve_of_eratosthenes(self):
        assert "sieve" in self.script.lower()

    def test_phase2_sieve_upper_bound(self):
        assert "2000000" in self.script

    def test_phase2_expected_prime_count(self):
        assert "148933" in self.script

    def test_phase2_writes_per_task_prime_files(self):
        assert "phase2_primes_task" in self.script

    def test_phase2_aggregates_counts(self):
        # Controller sums per-task counts into TOTAL
        assert "TOTAL" in self.script
        assert "phase2_primes_task" in self.script

    # ── Phase 3: Barrier ──────────────────────────────────────────────────────

    def test_phase3_creates_barrier_directory(self):
        assert "BARRIER_DIR" in self.script
        assert "barrier" in self.script

    def test_phase3_tasks_write_tokens(self):
        assert "ready_task" in self.script

    def test_phase3_controller_waits_for_all_tokens(self):
        # Controller polls until token count matches task count
        assert "NTASKS" in self.script
        assert "FOUND" in self.script

    def test_phase3_has_timeout(self):
        assert "DEADLINE" in self.script or "timeout" in self.script.lower()

    # ── Phase 4: Aggregation ──────────────────────────────────────────────────

    def test_phase4_writes_report_file(self):
        assert "phase4_report.txt" in self.script

    def test_phase4_collects_prime_results(self):
        # Aggregation reads phase2 output files
        assert "phase2_primes" in self.script

    def test_phase4_collects_barrier_tokens(self):
        assert "ready_task" in self.script

    # ── Phase 5: Parallel I/O ─────────────────────────────────────────────────

    def test_phase5_each_task_writes_8mb(self):
        assert "8" in self.script
        # dd count=8 with bs=1M, or explicit 8 MB reference
        assert "count=8" in self.script or "8 MB" in self.script or "8MB" in self.script

    def test_phase5_uses_parallel_srun(self):
        # Phase 5 must use srun so all tasks write simultaneously
        lines = self.script.splitlines()
        phase5_start = next(
            (i for i, l in enumerate(lines) if "PHASE 5" in l), None
        )
        assert phase5_start is not None, "Phase 5 section not found"
        phase5_block = "\n".join(lines[phase5_start:])
        assert "srun" in phase5_block

    def test_phase5_reports_throughput(self):
        assert "throughput" in self.script.lower() or "MB/s" in self.script

    def test_phase5_writes_per_task_io_files(self):
        assert "phase5_io_task" in self.script
