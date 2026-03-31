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

    "multinode": {
        "description": "Multi-node parallel job — 5 structured phases using srun across all workers",
        "script": r"""#!/bin/bash
#SBATCH --job-name=multinode_parallel
#SBATCH --output=/shared/multinode_%j.out
#SBATCH --error=/shared/multinode_%j.err
#SBATCH --ntasks-per-node=2
#SBATCH --nodes=2
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=128M
#SBATCH --time=00:05:00
#SBATCH --partition=debug

OUTDIR="/shared/multinode_${SLURM_JOB_ID}"
mkdir -p "$OUTDIR"

NTASKS=$((SLURM_JOB_NUM_NODES * SLURM_NTASKS_PER_NODE))

echo "============================================================"
echo " Multi-Node Parallel Job"
echo "============================================================"
echo "Job ID:       $SLURM_JOB_ID"
echo "Nodes:        $SLURM_JOB_NUM_NODES  ($SLURM_JOB_NODELIST)"
echo "Tasks/node:   $SLURM_NTASKS_PER_NODE"
echo "Total tasks:  $NTASKS"
echo "Output dir:   $OUTDIR"
echo "Start:        $(date)"
echo ""

# ── Phase 1: Discovery ───────────────────────────────────────────────────────
echo "------------------------------------------------------------"
echo "PHASE 1 — Task Discovery (srun placement)"
echo "------------------------------------------------------------"
srun --label bash -c '
    echo "node=$(hostname) localid=$SLURM_LOCALID globalid=$SLURM_PROCID pid=$$"
' | tee "$OUTDIR/phase1_discovery.txt"
echo ""

# ── Phase 2: CPU work — Sieve of Eratosthenes ────────────────────────────────
echo "------------------------------------------------------------"
echo "PHASE 2 — CPU Work (parallel prime sieve, chunks of 2M)"
echo "------------------------------------------------------------"
srun bash -c '
    TASKID=$SLURM_PROCID
    OUTFILE="'"$OUTDIR"'/phase2_primes_task${TASKID}.txt"
    LIMIT=2000000

    python3 - <<PYEOF
import math, time
limit = $LIMIT
start = time.time()
sieve = bytearray([1]) * (limit + 1)
sieve[0] = sieve[1] = 0
for i in range(2, int(math.isqrt(limit)) + 1):
    if sieve[i]:
        sieve[i*i::i] = bytearray(len(sieve[i*i::i]))
count = sum(sieve)
elapsed = time.time() - start
print(f"task=$TASKID node=$(hostname) primes_in_2M={count} elapsed={elapsed:.3f}s")
with open("$OUTFILE", "w") as f:
    f.write(f"{count}\n")
PYEOF
'
echo ""
echo "Aggregating prime counts..."
TOTAL=0
for f in "$OUTDIR"/phase2_primes_task*.txt; do
    COUNT=$(cat "$f")
    TOTAL=$((TOTAL + COUNT))
done
echo "Total primes found across $NTASKS tasks: $TOTAL"
if [ "$TOTAL" -eq $((NTASKS * 148933)) ]; then
    echo "PASS — each task correctly found 148,933 primes in [2, 2,000,000]"
else
    echo "NOTE — expected $((NTASKS * 148933)) (${NTASKS} x 148,933); got $TOTAL"
fi
echo ""

# ── Phase 3: Barrier ─────────────────────────────────────────────────────────
echo "------------------------------------------------------------"
echo "PHASE 3 — Barrier (shared-volume token rendezvous)"
echo "------------------------------------------------------------"
BARRIER_DIR="$OUTDIR/barrier"
mkdir -p "$BARRIER_DIR"

srun bash -c '
    TOKEN="'"$BARRIER_DIR"'/ready_task${SLURM_PROCID}"
    echo "$(hostname):$$:$(date +%s)" > "$TOKEN"
    echo "task $SLURM_PROCID wrote barrier token"
'

echo "Waiting for all $NTASKS barrier tokens..."
DEADLINE=$(($(date +%s) + 30))
while true; do
    FOUND=$(ls "$BARRIER_DIR"/ready_task* 2>/dev/null | wc -l)
    if [ "$FOUND" -ge "$NTASKS" ]; then
        break
    fi
    if [ "$(date +%s)" -gt "$DEADLINE" ]; then
        echo "WARNING: barrier timed out ($FOUND / $NTASKS tokens)"
        break
    fi
    sleep 1
done
echo "Barrier cleared — all $NTASKS tasks checked in:"
ls "$BARRIER_DIR"/ | sort
echo ""

# ── Phase 4: Aggregation ─────────────────────────────────────────────────────
echo "------------------------------------------------------------"
echo "PHASE 4 — Aggregation (single-process result collection)"
echo "------------------------------------------------------------"
REPORT="$OUTDIR/phase4_report.txt"
{
    echo "Multi-Node Parallel Job Report"
    echo "Generated: $(date)"
    echo "Job ID:    $SLURM_JOB_ID"
    echo "Nodes:     $SLURM_JOB_NODELIST"
    echo ""
    echo "Per-task prime counts:"
    for f in $(ls "$OUTDIR"/phase2_primes_task*.txt | sort -V); do
        TASK=$(basename "$f" .txt | sed 's/phase2_primes_//')
        COUNT=$(cat "$f")
        printf "  %-25s  %d primes\n" "$TASK" "$COUNT"
    done
    echo ""
    echo "Barrier tokens:"
    for f in $(ls "$BARRIER_DIR"/ready_task* | sort -V); do
        printf "  %s  ->  %s\n" "$(basename "$f")" "$(cat "$f")"
    done
} | tee "$REPORT"
echo ""

# ── Phase 5: Parallel I/O ────────────────────────────────────────────────────
echo "------------------------------------------------------------"
echo "PHASE 5 — Parallel I/O (each task writes 8 MB to /shared)"
echo "------------------------------------------------------------"
srun bash -c '
    IOFILE="'"$OUTDIR"'/phase5_io_task${SLURM_PROCID}.bin"
    T0=$(date +%s%3N)
    dd if=/dev/urandom of="$IOFILE" bs=1M count=8 2>/dev/null
    T1=$(date +%s%3N)
    ELAPSED_MS=$(( T1 - T0 ))
    SIZE_MB=8
    if [ "$ELAPSED_MS" -gt 0 ]; then
        THROUGHPUT=$(( SIZE_MB * 1000 / ELAPSED_MS ))
    else
        THROUGHPUT=999
    fi
    echo "task=$SLURM_PROCID node=$(hostname) wrote=${SIZE_MB}MB time=${ELAPSED_MS}ms throughput~${THROUGHPUT}MB/s"
' | tee "$OUTDIR/phase5_io.txt"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "============================================================"
echo " All phases complete"
echo "============================================================"
echo "Output files in $OUTDIR:"
ls -lh "$OUTDIR"/ | awk '{print "  " $0}'
echo ""
echo "Finished: $(date)"
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
