#!/bin/bash
set -e

ROLE=${SLURM_ROLE:-worker}
NODE_NAME=${SLURM_NODE_NAME:-$(hostname)}

echo "[entrypoint] Starting node: $NODE_NAME, role: $ROLE"

# ── Munge ────────────────────────────────────────────────────────────────────
setup_munge() {
    echo "[entrypoint] Setting up munge..."
    mkdir -p /run/munge /etc/munge /var/log/munge /var/lib/munge
    chown -R munge:munge /run/munge /etc/munge /var/log/munge /var/lib/munge
    chmod 700 /etc/munge
    chmod 755 /run/munge

    # Wait for munge key to appear (shared via volume)
    for i in $(seq 1 30); do
        if [ -f /etc/munge/munge.key ]; then
            echo "[entrypoint] Munge key found."
            break
        fi
        echo "[entrypoint] Waiting for munge key... ($i/30)"
        sleep 2
    done

    if [ ! -f /etc/munge/munge.key ]; then
        echo "[entrypoint] ERROR: munge key not found after waiting."
        exit 1
    fi

    chmod 400 /etc/munge/munge.key
    chown munge:munge /etc/munge/munge.key

    # Start munge daemon
    sudo -u munge /usr/sbin/munged --force
    sleep 1
    echo "[entrypoint] Munge started."
}

# ── slurm.conf wait ───────────────────────────────────────────────────────────
wait_for_slurm_conf() {
    for i in $(seq 1 30); do
        if [ -f /etc/slurm/slurm.conf ]; then
            echo "[entrypoint] slurm.conf found."
            return 0
        fi
        echo "[entrypoint] Waiting for slurm.conf... ($i/30)"
        sleep 2
    done
    echo "[entrypoint] ERROR: slurm.conf not found."
    exit 1
}

# ── SSH ───────────────────────────────────────────────────────────────────────
start_ssh() {
    echo "[entrypoint] Starting SSH..."
    mkdir -p /run/sshd
    /usr/sbin/sshd
}

# ── Controller ────────────────────────────────────────────────────────────────
start_controller() {
    echo "[entrypoint] Starting slurmctld..."
    mkdir -p /var/spool/slurm /var/log/slurm /var/run/slurm
    chown -R slurm:slurm /var/spool/slurm /var/log/slurm /var/run/slurm

    # Start controller in foreground-friendly way
    /usr/sbin/slurmctld -D &
    CTLD_PID=$!
    echo "[entrypoint] slurmctld PID: $CTLD_PID"
    wait $CTLD_PID
}

# ── Worker ────────────────────────────────────────────────────────────────────
start_worker() {
    echo "[entrypoint] Starting slurmd on $NODE_NAME..."
    mkdir -p /var/spool/slurmd /var/log/slurm /var/run/slurm
    chown -R slurm:slurm /var/spool/slurmd /var/log/slurm /var/run/slurm

    # Wait a moment for controller to be ready
    sleep 5

    /usr/sbin/slurmd -D -N "$NODE_NAME" &
    SLURMD_PID=$!
    echo "[entrypoint] slurmd PID: $SLURMD_PID"
    wait $SLURMD_PID
}

# ── Main ──────────────────────────────────────────────────────────────────────
setup_munge
start_ssh
wait_for_slurm_conf

case "$ROLE" in
    controller)
        start_controller
        ;;
    worker)
        start_worker
        ;;
    *)
        echo "[entrypoint] Unknown role: $ROLE. Sleeping forever for debug."
        tail -f /dev/null
        ;;
esac
