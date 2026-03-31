"""Unit tests for slurm_cluster/cluster.py"""

import pytest
from unittest.mock import MagicMock, patch, call
from slurm_cluster.cluster import SlurmCluster, IMAGE_NAME


def make_cluster(name="testcluster", num_workers=2):
    """Create a SlurmCluster with a mocked Docker client."""
    mock_docker = MagicMock()
    mock_docker.ping.return_value = True
    with patch("slurm_cluster.cluster.SlurmCluster._get_docker_client", return_value=mock_docker):
        cluster = SlurmCluster(name=name, num_workers=num_workers)
    cluster._docker = mock_docker
    return cluster


# ── Initialization ────────────────────────────────────────────────────────────

class TestSlurmClusterInit:
    def test_name_stored(self):
        c = make_cluster(name="mycluster")
        assert c.name == "mycluster"

    def test_num_workers_stored(self):
        c = make_cluster(num_workers=4)
        assert c.num_workers == 4

    def test_network_name(self):
        c = make_cluster(name="foo")
        assert c.network_name == "foo_net"

    def test_controller_name(self):
        c = make_cluster(name="foo")
        assert c.controller_name == "foo_controller"

    def test_worker_names_count(self):
        c = make_cluster(name="foo", num_workers=3)
        assert len(c.worker_names) == 3

    def test_worker_names_format(self):
        c = make_cluster(name="foo", num_workers=2)
        assert c.worker_names == ["foo_worker1", "foo_worker2"]

    def test_munge_vol_name(self):
        c = make_cluster(name="bar")
        assert c.munge_vol == "bar_munge"

    def test_conf_vol_name(self):
        c = make_cluster(name="bar")
        assert c.conf_vol == "bar_conf"

    def test_shared_vol_name(self):
        c = make_cluster(name="bar")
        assert c.shared_vol == "bar_shared"

    def test_default_name(self):
        mock_docker = MagicMock()
        with patch("slurm_cluster.cluster.SlurmCluster._get_docker_client", return_value=mock_docker):
            c = SlurmCluster()
        assert c.name == "slurmlocal"

    def test_default_num_workers(self):
        mock_docker = MagicMock()
        with patch("slurm_cluster.cluster.SlurmCluster._get_docker_client", return_value=mock_docker):
            c = SlurmCluster()
        assert c.num_workers == 2

    def test_single_worker(self):
        c = make_cluster(name="solo", num_workers=1)
        assert c.worker_names == ["solo_worker1"]


# ── Docker client ─────────────────────────────────────────────────────────────

class TestGetDockerClient:
    def test_exits_if_docker_not_importable(self):
        with patch.dict("sys.modules", {"docker": None}):
            with pytest.raises(SystemExit):
                SlurmCluster._get_docker_client(MagicMock())

    def test_exits_if_docker_unreachable(self):
        mock_docker_module = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("connection refused")
        mock_docker_module.from_env.return_value = mock_client
        with patch.dict("sys.modules", {"docker": mock_docker_module}):
            with pytest.raises(SystemExit):
                SlurmCluster._get_docker_client(MagicMock())


# ── Volume mounts ─────────────────────────────────────────────────────────────

class TestCommonVolumes:
    def test_returns_dict(self):
        c = make_cluster(name="x")
        vols = c._common_volumes()
        assert isinstance(vols, dict)

    def test_munge_mount_path(self):
        c = make_cluster(name="x")
        vols = c._common_volumes()
        assert vols[c.munge_vol]["bind"] == "/etc/munge"

    def test_conf_mount_path(self):
        c = make_cluster(name="x")
        vols = c._common_volumes()
        assert vols[c.conf_vol]["bind"] == "/etc/slurm"

    def test_shared_mount_path(self):
        c = make_cluster(name="x")
        vols = c._common_volumes()
        assert vols[c.shared_vol]["bind"] == "/shared"

    def test_munge_mode_rw(self):
        c = make_cluster(name="x")
        assert c._common_volumes()[c.munge_vol]["mode"] == "rw"

    def test_conf_mode_ro(self):
        c = make_cluster(name="x")
        assert c._common_volumes()[c.conf_vol]["mode"] == "ro"

    def test_shared_mode_rw(self):
        c = make_cluster(name="x")
        assert c._common_volumes()[c.shared_vol]["mode"] == "rw"

    def test_three_volumes_returned(self):
        c = make_cluster(name="x")
        assert len(c._common_volumes()) == 3


# ── Container running check ───────────────────────────────────────────────────

class TestContainerRunning:
    def test_returns_true_when_running(self):
        c = make_cluster()
        mock_container = MagicMock()
        mock_container.status = "running"
        c._docker.containers.get.return_value = mock_container
        assert c._container_running("mycontainer") is True

    def test_returns_false_when_stopped(self):
        c = make_cluster()
        mock_container = MagicMock()
        mock_container.status = "exited"
        c._docker.containers.get.return_value = mock_container
        assert c._container_running("mycontainer") is False

    def test_returns_false_when_not_found(self):
        c = make_cluster()
        c._docker.containers.get.side_effect = Exception("not found")
        assert c._container_running("nocontainer") is False


# ── Assert cluster running ─────────────────────────────────────────────────────

class TestAssertClusterRunning:
    def test_does_not_raise_when_running(self):
        c = make_cluster()
        with patch.object(c, "_container_running", return_value=True):
            c._assert_cluster_running()  # should not raise

    def test_raises_system_exit_when_not_running(self):
        c = make_cluster()
        with patch.object(c, "_container_running", return_value=False):
            with pytest.raises(SystemExit):
                c._assert_cluster_running()


# ── Exec on controller ────────────────────────────────────────────────────────

class TestExecOnController:
    def test_returns_stdout(self):
        c = make_cluster(name="ctrl")
        with patch("slurm_cluster.cluster.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello\n", stderr="")
            result = c._exec_on_controller("echo hello")
        assert result == "hello"

    def test_strips_whitespace(self):
        c = make_cluster(name="ctrl")
        with patch("slurm_cluster.cluster.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="  output  \n", stderr="")
            result = c._exec_on_controller("cmd")
        assert result == "output"

    def test_raises_on_nonzero_exit_by_default(self):
        c = make_cluster(name="ctrl")
        with patch("slurm_cluster.cluster.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
            with pytest.raises(RuntimeError):
                c._exec_on_controller("failing-cmd")

    def test_no_raise_when_raise_on_error_false(self):
        c = make_cluster(name="ctrl")
        with patch("slurm_cluster.cluster.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="partial", stderr="")
            result = c._exec_on_controller("cmd", raise_on_error=False)
        assert result == "partial"

    def test_uses_controller_name_in_command(self):
        c = make_cluster(name="mytest")
        with patch("slurm_cluster.cluster.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            c._exec_on_controller("sinfo")
        args = mock_run.call_args[0][0]
        assert c.controller_name in args


# ── Network management ────────────────────────────────────────────────────────

class TestCreateNetwork:
    def test_creates_network_if_not_exists(self):
        c = make_cluster()
        c._docker.networks.get.side_effect = Exception("not found")
        c._create_network()
        c._docker.networks.create.assert_called_once_with(c.network_name, driver="bridge")

    def test_does_not_create_if_already_exists(self):
        c = make_cluster()
        c._docker.networks.get.return_value = MagicMock()
        c._create_network()
        c._docker.networks.create.assert_not_called()


class TestRemoveNetwork:
    def test_removes_existing_network(self):
        c = make_cluster()
        mock_net = MagicMock()
        c._docker.networks.get.return_value = mock_net
        c._remove_network()
        mock_net.remove.assert_called_once()

    def test_silently_ignores_missing_network(self):
        c = make_cluster()
        c._docker.networks.get.side_effect = Exception("not found")
        c._remove_network()  # should not raise


# ── Volume management ─────────────────────────────────────────────────────────

class TestCreateVolumes:
    def test_creates_missing_volumes(self):
        c = make_cluster()
        c._docker.volumes.get.side_effect = Exception("not found")
        c._create_volumes()
        assert c._docker.volumes.create.call_count == 3

    def test_skips_existing_volumes(self):
        c = make_cluster()
        c._docker.volumes.get.return_value = MagicMock()
        c._create_volumes()
        c._docker.volumes.create.assert_not_called()

    def test_creates_three_specific_volumes(self):
        c = make_cluster(name="abc")
        c._docker.volumes.get.side_effect = Exception("not found")
        c._create_volumes()
        created_names = [call[0][0] for call in c._docker.volumes.create.call_args_list]
        assert "abc_munge" in created_names
        assert "abc_conf" in created_names
        assert "abc_shared" in created_names


class TestRemoveVolumes:
    def test_removes_all_volumes(self):
        c = make_cluster()
        mock_vol = MagicMock()
        c._docker.volumes.get.return_value = mock_vol
        c._remove_volumes()
        assert mock_vol.remove.call_count == 3

    def test_silently_ignores_missing_volumes(self):
        c = make_cluster()
        c._docker.volumes.get.side_effect = Exception("not found")
        c._remove_volumes()  # should not raise


# ── Ensure image ─────────────────────────────────────────────────────────────

class TestEnsureImage:
    def test_does_not_build_if_image_exists(self):
        c = make_cluster()
        c._docker.images.get.return_value = MagicMock()
        with patch.object(c, "build_image") as mock_build:
            c._ensure_image()
        mock_build.assert_not_called()

    def test_builds_if_image_missing(self):
        c = make_cluster()
        c._docker.images.get.side_effect = Exception("not found")
        with patch.object(c, "build_image") as mock_build:
            c._ensure_image()
        mock_build.assert_called_once()


# ── Wait for cluster ──────────────────────────────────────────────────────────

class TestWaitForCluster:
    def test_returns_true_when_nodes_idle(self):
        c = make_cluster()
        with patch.object(c, "_container_running", return_value=True):
            with patch.object(c, "_exec_on_controller", return_value="worker1 idle"):
                result = c._wait_for_cluster(timeout=10)
        assert result is True

    def test_returns_false_when_controller_stops(self):
        c = make_cluster()
        with patch.object(c, "_container_running", return_value=False):
            with patch.object(c, "_print_container_logs"):
                result = c._wait_for_cluster(timeout=10)
        assert result is False

    def test_returns_false_on_timeout(self):
        c = make_cluster()
        with patch.object(c, "_container_running", return_value=True):
            with patch.object(c, "_exec_on_controller", return_value=""):
                result = c._wait_for_cluster(timeout=1)
        assert result is False

    def test_attempts_resume_when_nodes_registered_but_not_idle(self):
        c = make_cluster()
        exec_calls = []

        def fake_exec(cmd, raise_on_error=True):
            exec_calls.append(cmd)
            if "sinfo" in cmd:
                return "worker1 down*"
            return ""

        with patch.object(c, "_container_running", return_value=True):
            with patch.object(c, "_exec_on_controller", side_effect=fake_exec):
                c._wait_for_cluster(timeout=1)

        resume_calls = [cmd for cmd in exec_calls if "State=RESUME" in cmd]
        assert len(resume_calls) == 1

    def test_resume_attempted_only_once(self):
        c = make_cluster()
        resume_count = [0]

        def fake_exec(cmd, raise_on_error=True):
            if "State=RESUME" in cmd:
                resume_count[0] += 1
            if "sinfo" in cmd:
                return "worker1 down*"
            return ""

        with patch.object(c, "_container_running", return_value=True):
            with patch.object(c, "_exec_on_controller", side_effect=fake_exec):
                c._wait_for_cluster(timeout=1)

        assert resume_count[0] == 1

    def test_shows_logs_when_controller_stops(self):
        c = make_cluster()
        with patch.object(c, "_container_running", return_value=False):
            with patch.object(c, "_print_container_logs") as mock_logs:
                c._wait_for_cluster(timeout=10)
        mock_logs.assert_called_once_with(c.controller_name)


class TestUp:
    def _patch_up(self, cluster, ready):
        cluster._ensure_image = MagicMock()
        cluster._create_network = MagicMock()
        cluster._create_volumes = MagicMock()
        cluster._inject_munge_key = MagicMock()
        cluster._inject_slurm_conf = MagicMock()
        cluster._start_controller = MagicMock()
        cluster._start_worker = MagicMock()
        cluster._wait_for_cluster = MagicMock(return_value=ready)

    def test_success_message_printed_when_ready(self, capsys):
        c = make_cluster()
        self._patch_up(c, ready=True)
        import slurm_cluster.ui as ui_mod
        with patch.object(ui_mod, "USE_COLOR", False):
            c.up()
        out = capsys.readouterr().out
        assert "up" in out.lower() or "🎉" in out

    def test_exits_with_error_when_not_ready(self):
        c = make_cluster()
        self._patch_up(c, ready=False)
        with pytest.raises(SystemExit) as exc_info:
            c.up()
        assert exc_info.value.code == 1

    def test_all_startup_steps_called(self):
        c = make_cluster()
        self._patch_up(c, ready=True)
        c.up()
        c._ensure_image.assert_called_once()
        c._create_network.assert_called_once()
        c._create_volumes.assert_called_once()
        c._inject_munge_key.assert_called_once()
        c._inject_slurm_conf.assert_called_once()
        c._start_controller.assert_called_once()

    def test_workers_started_for_each_worker(self):
        c = make_cluster(num_workers=3)
        self._patch_up(c, ready=True)
        c.up()
        assert c._start_worker.call_count == 3


# ── Submit sample job ─────────────────────────────────────────────────────────

class TestSubmitSampleJob:
    def test_unknown_job_prints_error(self, capsys):
        c = make_cluster()
        with patch.object(c, "_assert_cluster_running"):
            import slurm_cluster.ui as ui_mod
            with patch.object(ui_mod, "USE_COLOR", False):
                c.submit_sample_job(job_name="nonexistent")
        err = capsys.readouterr().err
        assert "nonexistent" in err or "Unknown" in err

    def test_submit_all_submits_all_jobs(self):
        c = make_cluster()
        mock_exec = MagicMock(return_value="Submitted batch job 1")
        with patch.object(c, "_assert_cluster_running"):
            with patch.object(c, "_exec_on_controller", mock_exec):
                c.submit_sample_job(job_name="all")
        from slurm_cluster.jobs import SAMPLE_JOBS
        # _exec_on_controller should be called twice per job (write + sbatch)
        assert mock_exec.call_count >= len(SAMPLE_JOBS)

    def test_submit_specific_job(self):
        c = make_cluster()
        mock_exec = MagicMock(return_value="Submitted batch job 42")
        with patch.object(c, "_assert_cluster_running"):
            with patch.object(c, "_exec_on_controller", mock_exec):
                c.submit_sample_job(job_name="hello")
        # Only "hello" job processed: write + sbatch = 2 calls
        assert mock_exec.call_count == 2


# ── Logs ──────────────────────────────────────────────────────────────────────

class TestLogs:
    def test_defaults_to_controller(self):
        c = make_cluster(name="mytest")
        with patch.object(c, "_assert_cluster_running"):
            with patch("slurm_cluster.cluster.os.execvp") as mock_exec:
                c.logs(node=None)
        args = mock_exec.call_args[0]
        assert c.controller_name in args[1]

    def test_selects_matching_worker(self):
        c = make_cluster(name="mytest", num_workers=2)
        with patch.object(c, "_assert_cluster_running"):
            with patch("slurm_cluster.cluster.os.execvp") as mock_exec:
                c.logs(node="worker1")
        args = mock_exec.call_args[0]
        assert "mytest_worker1" in args[1]

    def test_prints_error_for_unknown_node(self, capsys):
        c = make_cluster(name="mytest")
        with patch.object(c, "_assert_cluster_running"):
            with patch("slurm_cluster.cluster.os.execvp"):
                import slurm_cluster.ui as ui_mod
                with patch.object(ui_mod, "USE_COLOR", False):
                    c.logs(node="nonexistent_xyz")
        err = capsys.readouterr().err
        assert "nonexistent_xyz" in err


# ── Down ──────────────────────────────────────────────────────────────────────

class TestDown:
    def test_removes_all_containers(self):
        c = make_cluster(name="test", num_workers=2)
        mock_container = MagicMock()
        c._docker.containers.get.return_value = mock_container
        with patch.object(c, "_remove_network"):
            with patch.object(c, "_remove_volumes"):
                c.down()
        # controller + 2 workers = 3 containers
        assert mock_container.remove.call_count == 3

    def test_calls_remove_network(self):
        c = make_cluster()
        c._docker.containers.get.side_effect = Exception("not found")
        with patch.object(c, "_remove_network") as mock_net:
            with patch.object(c, "_remove_volumes"):
                c.down()
        mock_net.assert_called_once()

    def test_calls_remove_volumes(self):
        c = make_cluster()
        c._docker.containers.get.side_effect = Exception("not found")
        with patch.object(c, "_remove_network"):
            with patch.object(c, "_remove_volumes") as mock_vols:
                c.down()
        mock_vols.assert_called_once()

    def test_tolerates_missing_containers(self):
        c = make_cluster()
        c._docker.containers.get.side_effect = Exception("not found")
        with patch.object(c, "_remove_network"):
            with patch.object(c, "_remove_volumes"):
                c.down()  # should not raise
