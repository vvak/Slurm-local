FROM ubuntu:22.04

LABEL maintainer="slurm-local"
LABEL description="SLURM node for local testing"

ENV DEBIAN_FRONTEND=noninteractive

# Install SLURM and dependencies
# slurm-wlm provides slurmctld, slurmd, srun, sbatch, squeue, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        munge \
        libmunge-dev \
        slurm-wlm \
        openssh-server \
        openssh-client \
        python3 \
        python3-pip \
        wget \
        curl \
        vim \
        procps \
        iputils-ping \
        net-tools \
        sudo \
        && rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN ssh-keygen -A && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
    echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config

# Create slurm user/group if not already created by the package
RUN getent group slurm || groupadd -r slurm && \
    getent passwd slurm || useradd -r -g slurm -d /var/lib/slurm -s /sbin/nologin slurm

# Create required directories
RUN mkdir -p \
        /var/spool/slurm \
        /var/spool/slurmd \
        /var/log/slurm \
        /var/run/slurm \
        /etc/slurm \
        /shared && \
    chown -R slurm:slurm \
        /var/spool/slurm \
        /var/spool/slurmd \
        /var/log/slurm \
        /var/run/slurm && \
    chmod 755 /shared

# Munge setup
RUN mkdir -p /etc/munge /var/log/munge /var/lib/munge /run/munge && \
    chown -R munge:munge /etc/munge /var/log/munge /var/lib/munge /run/munge && \
    chmod 700 /etc/munge

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create a test user for job submission
RUN useradd -m -s /bin/bash testuser && \
    echo "testuser:testpass" | chpasswd && \
    usermod -aG sudo testuser

EXPOSE 22 6817 6818 6819

ENTRYPOINT ["/entrypoint.sh"]
