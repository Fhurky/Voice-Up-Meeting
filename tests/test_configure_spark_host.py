"""The privileged helper is tested with real sysfs fixtures and bounded command mocks."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest

PROFILE_UUID = "b7e1fe46-3710-45a5-a210-895b00a56784"
WIFI_UUID = "89e3faf0-6663-4d41-bbb9-f8da64193a09"


@pytest.fixture
def helper():
    source = Path(__file__).resolve().parents[1] / "scripts" / "configure-spark-host.py"
    spec = importlib.util.spec_from_file_location("configure_spark_host", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def host(helper, monkeypatch, tmp_path):
    interface = tmp_path / "enP7s7"
    (interface / "device").mkdir(parents=True)
    (interface / "type").write_text("1\n")
    (interface / "carrier").write_text("1\n")
    monkeypatch.setattr(helper.platform, "system", lambda: "Linux")
    monkeypatch.setattr(helper.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(helper.os, "geteuid", lambda: 0, raising=False)
    state = {"profiles": {}, "active": "", "member": False, "mutations": [], "addresses": []}
    monkeypatch.setattr(helper, "lookup_identity", lambda user: (1000, state["member"]))

    def run(argv, *, stdin, capture_output, text, check, timeout, env):
        assert stdin == subprocess.DEVNULL and capture_output and text and not check
        assert timeout <= 45 and env["LC_ALL"] == "C"
        assert argv[0] in {"/usr/bin/nmcli", "/usr/sbin/usermod", "/usr/sbin/ip"}
        output = ""
        if argv[0].endswith("/ip"):
            assert argv == ["/usr/sbin/ip", "-j", "-4", "address", "show"]
            output = json.dumps(state["addresses"])
        elif argv[0].endswith("/usermod"):
            assert argv == ["/usr/sbin/usermod", "-aG", "docker", "lab_nvidia1"]
            state["mutations"].append(argv)
            state["member"] = True
        elif "--get-values" in argv:
            field = argv[argv.index("--get-values") + 1]
            if field == "UUID":
                output = "\n".join([WIFI_UUID, *state["profiles"]])
            elif field == "GENERAL.CON-UUID":
                assert argv[-3:] == ["device", "show", "enP7s7"]
                output = state["active"] or "--"
            elif argv[-1] == WIFI_UUID:
                assert field == "connection.id", "Other profile settings must not be read"
                output = "Existing Wi-Fi"
            else:
                output = state["profiles"][argv[-1]][field]
        elif "add" in argv:
            state["mutations"].append(argv)
            assert argv[1:4] == ["connection", "add", "type"]
            assert argv[4:9] == ["ethernet", "con-name", "voiceup-direct", "ifname", "enP7s7"]
            options = dict(zip(argv[9::2], argv[10::2]))
            profile_id = options.pop("connection.uuid")
            state["profiles"][profile_id] = {
                "connection.id": "voiceup-direct",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "enP7s7",
                **options,
            }
        else:
            assert argv[:5] == ["/usr/bin/nmcli", "--wait", "30", "connection", "up"]
            assert argv[5] == "uuid" and argv[-2:] == ["ifname", "enP7s7"]
            state["mutations"].append(argv)
            state["active"] = argv[6]
        return subprocess.CompletedProcess(argv, 0, output + "\n", "")

    mock = create_autospec(subprocess.run, side_effect=run)
    monkeypatch.setattr(helper.subprocess, "run", mock)
    state.update(sysfs=tmp_path, mock=mock)
    return state


def invoke(helper, host):
    return helper.configure("lab_nvidia1", "enP7s7", "192.168.137.2/24", sysfs=host["sysfs"])


def existing(helper, host, **overrides):
    host["profiles"][PROFILE_UUID] = {
        "connection.id": "voiceup-direct",
        "connection.type": "802-3-ethernet",
        "connection.interface-name": "enP7s7",
        **helper.connection_settings("192.168.137.2/24"),
        **overrides,
    }


def test_create_activate_then_add_group_preserves_other_profiles(helper, host):
    result = invoke(helper, host)
    assert result == {"profile": "created", "activation": "activated", "docker_group": "added"}
    commands = host["mutations"]
    assert len(commands) == 3 and "add" in commands[0] and "up" in commands[1]
    assert commands[2][0].endswith("/usermod")
    assert not any(
        word in command
        for command in commands
        for word in ("delete", "modify", "down", "wifi", "sudo", "docker", "install", "pull")
        if command[0].endswith("/nmcli")
    )
    profile = next(iter(host["profiles"].values()))
    assert profile["ipv4.never-default"] == "yes"
    assert profile["ipv4.gateway"] == profile["ipv4.dns"] == ""
    assert profile["ipv6.method"] == "link-local"
    assert profile["connection.autoconnect"] == "yes"
    assert invoke(helper, host) == {
        "profile": "existing",
        "activation": "already_active",
        "docker_group": "already_member",
    }
    assert len(host["mutations"]) == 3


@pytest.mark.parametrize(
    "setting,value",
    [
        ("connection.interface-name", "wlan0"),
        ("ipv4.addresses", "192.168.137.3/24"),
        ("ipv4.never-default", "no"),
        ("ipv4.gateway", "192.168.137.1"),
        ("ipv4.dns", "192.168.137.1"),
        ("ipv4.routes", "0.0.0.0/0 192.168.137.1"),
        ("ipv6.method", "auto"),
        ("connection.autoconnect", "no"),
    ],
)
def test_existing_profile_conflict_fails_before_mutation(helper, host, setting, value):
    existing(helper, host, **{setting: value})
    with pytest.raises(helper.ConfigurationError, match="profile_conflict"):
        invoke(helper, host)
    assert host["mutations"] == []


def test_duplicate_name_fails_before_mutation(helper, host):
    existing(helper, host)
    host["profiles"]["11111111-2222-3333-4444-555555555555"] = dict(host["profiles"][PROFILE_UUID])
    with pytest.raises(helper.ConfigurationError, match="duplicate_profile"):
        invoke(helper, host)
    assert host["mutations"] == []


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.2/24",
        "8.8.8.8/24",
        "::1/64",
        "192.168.137.0/24",
        "192.168.137.255/24",
        "192.168.137.2",
        "192.168.137.2/32",
        "169.254.1.2/16",
        "192.0.2.2/24",
        "192.168.137.2/0",
    ],
)
def test_invalid_address_rejected_before_commands(helper, host, address):
    with pytest.raises(helper.ConfigurationError, match="invalid_address"):
        helper.configure("lab_nvidia1", "enP7s7", address, sysfs=host["sysfs"])
    host["mock"].assert_not_called()


@pytest.mark.parametrize(
    "problem",
    [
        "nonroot",
        "architecture",
        "os",
        "root_user",
        "missing_group",
        "wifi",
        "virtual",
        "carrier",
        "invalid_user",
        "invalid_interface",
    ],
)
def test_host_validation_fails_before_commands(helper, host, monkeypatch, problem):
    user, interface = "lab_nvidia1", "enP7s7"
    if problem == "nonroot":
        monkeypatch.setattr(helper.os, "geteuid", lambda: 1000)
    if problem == "architecture":
        monkeypatch.setattr(helper.platform, "machine", lambda: "x86_64")
    if problem == "os":
        monkeypatch.setattr(helper.platform, "system", lambda: "Windows")
    if problem == "root_user":
        monkeypatch.setattr(helper, "lookup_identity", lambda user: (0, False))
    if problem == "missing_group":

        def missing(user):
            raise helper.ConfigurationError("missing_docker_group")

        monkeypatch.setattr(helper, "lookup_identity", missing)
    if problem == "wifi":
        (host["sysfs"] / interface / "wireless").mkdir()
    if problem == "virtual":
        (host["sysfs"] / interface / "device").rmdir()
    if problem == "carrier":
        (host["sysfs"] / interface / "carrier").write_text("0")
    if problem == "invalid_user":
        user = "--root"
    if problem == "invalid_interface":
        interface = "../enP7s7"
    with pytest.raises(helper.ConfigurationError):
        helper.configure(user, interface, "192.168.137.2/24", sysfs=host["sysfs"])
    host["mock"].assert_not_called()


def test_other_active_connection_is_not_disconnected(helper, host):
    host["active"] = WIFI_UUID
    with pytest.raises(helper.ConfigurationError, match="interface_in_use"):
        invoke(helper, host)
    assert host["mutations"] == []


def test_other_interface_subnet_is_not_overridden(helper, host):
    host["addresses"] = [
        {
            "ifname": "wlan0",
            "addr_info": [{"family": "inet", "local": "192.168.137.8", "prefixlen": 24}],
        }
    ]
    with pytest.raises(helper.ConfigurationError, match="address_conflict"):
        invoke(helper, host)
    assert host["mutations"] == []


def test_failed_activation_does_not_grant_docker_group(helper, host, monkeypatch):
    original = helper.run_command

    def fail_activation(argv):
        if "up" in argv:
            raise helper.ConfigurationError("command_failed")
        return original(argv)

    monkeypatch.setattr(helper, "run_command", fail_activation)
    with pytest.raises(helper.ConfigurationError):
        invoke(helper, host)
    assert not host["member"]


def test_command_failure_does_not_expose_stderr(helper, monkeypatch):
    monkeypatch.setattr(
        helper.subprocess,
        "run",
        create_autospec(
            subprocess.run,
            return_value=subprocess.CompletedProcess([], 1, "private stdout", "private stderr"),
        ),
    )
    with pytest.raises(helper.ConfigurationError, match="command_failed") as error:
        helper.run_command(["/usr/bin/nmcli", "connection", "show"])
    assert "private" not in str(error.value)


@pytest.mark.parametrize("missing", ["user", "group"])
def test_missing_real_identity_lookup_is_explicit(helper, monkeypatch, missing):
    def getpwnam(name):
        assert name == "lab_nvidia1"
        if missing == "user":
            raise KeyError(name)
        return SimpleNamespace(pw_uid=1000, pw_gid=1000)

    def getgrnam(name):
        assert name == "docker"
        raise KeyError(name)

    monkeypatch.setitem(sys.modules, "pwd", SimpleNamespace(getpwnam=getpwnam))
    monkeypatch.setitem(sys.modules, "grp", SimpleNamespace(getgrnam=getgrnam))
    with pytest.raises(
        helper.ConfigurationError,
        match="missing_user" if missing == "user" else "missing_docker_group",
    ):
        helper.lookup_identity("lab_nvidia1")


def test_command_timeout_is_bounded_and_sanitized(helper, monkeypatch):
    monkeypatch.setattr(
        helper.subprocess,
        "run",
        create_autospec(
            subprocess.run, side_effect=subprocess.TimeoutExpired(["private"], 45, output="private")
        ),
    )
    with pytest.raises(helper.ConfigurationError, match="command_timeout") as error:
        helper.run_command(["/usr/bin/nmcli", "connection", "show"])
    assert "private" not in str(error.value)


def test_cli_root_rejection_is_read_only(helper, host, monkeypatch, capsys):
    monkeypatch.setattr(helper.os, "geteuid", lambda: 1000)
    assert (
        helper.main(
            ["--user", "lab_nvidia1", "--interface", "enP7s7", "--address", "192.168.137.2/24"]
        )
        == 1
    )
    assert "requires_root" in capsys.readouterr().err
    host["mock"].assert_not_called()
