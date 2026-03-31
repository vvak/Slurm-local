"""Unit tests for slurm_cluster/config.py"""

import pytest
from slurm_cluster.config import generate_slurm_conf, generate_cgroup_conf


class TestGenerateSlurmConf:
    def test_cluster_name_in_output(self):
        conf = generate_slurm_conf("ctrl", ["n1"], cluster_name="mycluster")
        assert "ClusterName=mycluster" in conf

    def test_default_cluster_name(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "ClusterName=localcluster" in conf

    def test_controller_host_in_output(self):
        conf = generate_slurm_conf("mycontroller", ["n1"])
        assert "SlurmctldHost=mycontroller" in conf

    def test_single_node_definition(self):
        conf = generate_slurm_conf("ctrl", ["worker1"])
        assert "NodeName=worker1" in conf
        assert "CPUs=2" in conf
        assert "RealMemory=512" in conf

    def test_multiple_node_definitions(self):
        conf = generate_slurm_conf("ctrl", ["worker1", "worker2", "worker3"])
        assert "NodeName=worker1" in conf
        assert "NodeName=worker2" in conf
        assert "NodeName=worker3" in conf

    def test_node_list_in_partitions(self):
        conf = generate_slurm_conf("ctrl", ["n1", "n2"])
        assert "Nodes=n1,n2" in conf

    def test_debug_partition_is_default(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "PartitionName=debug" in conf
        assert "Default=YES" in conf
        assert "MaxTime=INFINITE" in conf

    def test_batch_partition_exists(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "PartitionName=batch" in conf
        assert "MaxTime=01:00:00" in conf

    def test_auth_type_is_munge(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "AuthType=auth/munge" in conf
        assert "CryptoType=crypto/munge" in conf

    def test_scheduler_type(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "SchedulerType=sched/backfill" in conf

    def test_select_type_cons_tres(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "SelectType=select/cons_tres" in conf
        assert "SelectTypeParameters=CR_Core_Memory" in conf

    def test_proctrack_type(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "ProctrackType=proctrack/pgid" in conf

    def test_ports_present(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "SlurmctldPort=6817" in conf
        assert "SlurmdPort=6818" in conf

    def test_log_paths(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "SlurmctldLogFile=/var/log/slurm/slurmctld.log" in conf
        assert "SlurmdLogFile=/var/log/slurm/slurmd.log" in conf

    def test_state_save_location(self):
        conf = generate_slurm_conf("ctrl", ["n1"])
        assert "StateSaveLocation=/var/spool/slurm" in conf

    def test_node_spec_details(self):
        conf = generate_slurm_conf("ctrl", ["worker1"])
        assert "Sockets=1" in conf
        assert "CoresPerSocket=2" in conf
        assert "ThreadsPerCore=1" in conf
        assert "State=UNKNOWN" in conf

    def test_returns_string(self):
        result = generate_slurm_conf("ctrl", ["n1"])
        assert isinstance(result, str)

    def test_empty_node_list_still_returns_string(self):
        result = generate_slurm_conf("ctrl", [])
        assert isinstance(result, str)
        # Partitions will have empty Nodes=
        assert "PartitionName=debug" in result

    def test_special_chars_in_cluster_name(self):
        conf = generate_slurm_conf("ctrl", ["n1"], cluster_name="test-cluster-1")
        assert "ClusterName=test-cluster-1" in conf


class TestGenerateCgroupConf:
    def test_returns_string(self):
        result = generate_cgroup_conf()
        assert isinstance(result, str)

    def test_cgroup_automount(self):
        conf = generate_cgroup_conf()
        assert "CgroupAutomount=yes" in conf

    def test_no_constrain_cores(self):
        conf = generate_cgroup_conf()
        assert "ConstrainCores=no" in conf

    def test_no_constrain_ram(self):
        conf = generate_cgroup_conf()
        assert "ConstrainRAMSpace=no" in conf

    def test_is_deterministic(self):
        assert generate_cgroup_conf() == generate_cgroup_conf()
