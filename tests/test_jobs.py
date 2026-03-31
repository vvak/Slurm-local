"""Unit tests for slurm_cluster/jobs.py"""

import pytest
from slurm_cluster.jobs import SAMPLE_JOBS

EXPECTED_JOB_NAMES = {"hello", "array", "sleep", "resource", "deps"}


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
