"""Sample SLURM job scripts for testing various SLURM features."""

SAMPLE_JOBS = {
    "hello": {
        "description": "Simple hello world job",
        "script": """#!/bin/bash
#SBATCH --job-name=hello
#SBATCH --output=/shared/hello_%j.out
#SBATCH --error=/shared/hello_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=64M
#SBATCH --time=00:01:00
#SBATCH --partition=debug

echo "============================================"
echo " Hello from SLURM!"
echo "============================================"
echo "Job ID:       $SLURM_JOB_ID"
echo "Job Name:     $SLURM_JOB_NAME"
echo "Node:         $(hostname)"
echo "Partition:    $SLURM_JOB_PARTITION"
echo "Tasks:        $SLURM_NTASKS"
echo "CPUs/task:    $SLURM_CPUS_PER_TASK"
echo "Submit dir:   $SLURM_SUBMIT_DIR"
echo "Start time:   $(date)"
echo ""
echo "Available nodes in cluster:"
sinfo --noheader -o "%N %T %C"
echo ""
echo "Done!"
""",
    },

    "array": {
        "description": "Array job (5 tasks) — tests job arrays",
        "script": """#!/bin/bash
#SBATCH --job-name=array_test
#SBATCH --output=/shared/array_%A_%a.out
#SBATCH --error=/shared/array_%A_%a.err
#SBATCH --array=1-5
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32M
#SBATCH --time=00:02:00
#SBATCH --partition=debug

echo "========================================"
echo " Array Job Task"
echo "========================================"
echo "Array Job ID:   $SLURM_ARRAY_JOB_ID"
echo "Array Task ID:  $SLURM_ARRAY_TASK_ID"
echo "Node:           $(hostname)"
echo "Start time:     $(date)"
echo ""

# Simulate different work per task
WORK_SECONDS=$((SLURM_ARRAY_TASK_ID * 2))
echo "Simulating $WORK_SECONDS seconds of work for task $SLURM_ARRAY_TASK_ID..."
sleep $WORK_SECONDS

echo "Task $SLURM_ARRAY_TASK_ID complete at $(date)"
""",
    },

    "sleep": {
        "description": "Long-running sleep job — useful for testing squeue/scancel",
        "script": """#!/bin/bash
#SBATCH --job-name=long_sleep
#SBATCH --output=/shared/sleep_%j.out
#SBATCH --error=/shared/sleep_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32M
#SBATCH --time=00:10:00
#SBATCH --partition=debug

echo "Starting long sleep job (PID: $$)"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo ""
echo "This job sleeps for 5 minutes."
echo "Use 'squeue' to see it running."
echo "Use 'scancel $SLURM_JOB_ID' to cancel it."
echo ""

for i in $(seq 1 30); do
    echo "[$(date +%H:%M:%S)] Tick $i / 30 — still running..."
    sleep 10
done

echo "Sleep job finished."
""",
    },

    "resource": {
        "description": "Multi-task resource test — tests scheduling across nodes",
        "script": """#!/bin/bash
#SBATCH --job-name=resource_test
#SBATCH --output=/shared/resource_%j.out
#SBATCH --error=/shared/resource_%j.err
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=32M
#SBATCH --time=00:02:00
#SBATCH --partition=debug

echo "========================================"
echo " Resource Allocation Test"
echo "========================================"
echo "Job ID:          $SLURM_JOB_ID"
echo "Requested tasks: $SLURM_NTASKS"
echo "Node list:       $SLURM_JOB_NODELIST"
echo "Nodes used:      $SLURM_JOB_NUM_NODES"
echo "CPUs total:      $SLURM_NPROCS"
echo ""

echo "Running srun to print hostname from each task:"
srun --label hostname

echo ""
echo "Node info at time of job:"
sinfo -N --noheader -o "%N %T %C %m"
echo ""
echo "Resource test complete."
""",
    },

    "deps": {
        "description": "Dependency chain — Job B waits for Job A to finish",
        "script": """#!/bin/bash
# This script submits two jobs where job B depends on job A.
# It is run on the CONTROLLER to chain submissions.

echo "========================================"
echo " Job Dependency Chain Demo"
echo "========================================"

# ── Job A ────────────────────────────────────────────────────────────────────
JOB_A=$(sbatch --parsable \
    --job-name=dep_job_A \
    --output=/shared/dep_A_%j.out \
    --ntasks=1 --cpus-per-task=1 --mem=32M \
    --time=00:02:00 --partition=debug \
    --wrap="echo 'Job A (ID: $SLURM_JOB_ID) starting'; sleep 10; echo 'Job A done at $(date)'")

echo "Submitted Job A: $JOB_A"

# ── Job B (depends on A) ──────────────────────────────────────────────────────
JOB_B=$(sbatch --parsable \
    --job-name=dep_job_B \
    --output=/shared/dep_B_%j.out \
    --ntasks=1 --cpus-per-task=1 --mem=32M \
    --time=00:02:00 --partition=debug \
    --dependency=afterok:${JOB_A} \
    --wrap="echo 'Job B (ID: $SLURM_JOB_ID) starting — Job A finished!'; echo 'Completed at $(date)'")

echo "Submitted Job B: $JOB_B (depends on $JOB_A)"
echo ""
echo "Current queue:"
squeue -o "%.10i %-15j %-8T %-12R" 2>/dev/null || squeue
echo ""
echo "Job A will run first. Job B will only start after Job A succeeds."
echo "Watch with: squeue"
""",
    },
}
