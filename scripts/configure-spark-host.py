"""Configure one dedicated Spark Ethernet profile and append one Docker group member.

Run locally on Spark with sudo after reviewing the exact interface and address.
Only this named profile may be activated; other profiles are never modified.
NetworkManager settings: https://www.networkmanager.dev/docs/api/1.46.2/nm-settings-nmcli.html
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

NMCLI = "/usr/bin/nmcli"
IP = "/usr/sbin/ip"
USERMOD = "/usr/sbin/usermod"
PROFILE = "voiceup-direct"
PRIVATE_NETWORKS = tuple(
    ipaddress.IPv4Network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


class ConfigurationError(Exception):
    """A fixed diagnostic that never contains subprocess output or secrets."""


def run_command(argv):
    try:
        result = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired:
        raise ConfigurationError("command_timeout") from None
    except OSError:
        raise ConfigurationError("command_unavailable") from None
    if result.returncode:
        raise ConfigurationError("command_failed")
    return result.stdout.strip()


def lookup_identity(user):
    # These modules exist on Linux; importing the CLI/help on Windows remains harmless.
    import grp
    import pwd

    try:
        account = pwd.getpwnam(user)
    except KeyError:
        raise ConfigurationError("missing_user") from None
    try:
        group = grp.getgrnam("docker")
    except KeyError:
        raise ConfigurationError("missing_docker_group") from None
    return account.pw_uid, account.pw_gid == group.gr_gid or user in group.gr_mem


def validate_address(value):
    try:
        if "/" not in value:
            raise ValueError
        address = ipaddress.IPv4Interface(value)
        if (
            address.network.prefixlen > 30
            or not any(address.network.subnet_of(network) for network in PRIVATE_NETWORKS)
            or address.ip in (address.network.network_address, address.network.broadcast_address)
        ):
            raise ValueError
    except (ValueError, TypeError):
        raise ConfigurationError("invalid_address: use a private IPv4 host with /prefix") from None
    return address


def connection_settings(address):
    return {
        "connection.autoconnect": "yes",
        "connection.master": "",
        "connection.secondaries": "",
        "ipv4.method": "manual",
        "ipv4.addresses": address,
        "ipv4.never-default": "yes",
        "ipv4.gateway": "",
        "ipv4.dns": "",
        "ipv4.dns-search": "",
        "ipv4.routes": "",
        "ipv4.routing-rules": "",
        "ipv4.ignore-auto-dns": "yes",
        "ipv4.ignore-auto-routes": "yes",
        "ipv4.may-fail": "no",
        "ipv4.dad-timeout": "1500",
        "ipv6.method": "link-local",
        "ipv6.never-default": "yes",
        "ipv6.gateway": "",
        "ipv6.dns": "",
        "ipv6.dns-search": "",
        "ipv6.addresses": "",
        "ipv6.routes": "",
        "ipv6.routing-rules": "",
    }


def nm_value(field, *target):
    value = run_command([NMCLI, "--escape", "no", "--get-values", field, *target])
    return "" if value == "--" else value


def validate_profile(profile_id, interface, address):
    expected = {
        "connection.id": PROFILE,
        "connection.type": "802-3-ethernet",
        "connection.interface-name": interface,
        **connection_settings(address),
    }
    for setting, value in expected.items():
        if nm_value(setting, "connection", "show", "uuid", profile_id) != value:
            raise ConfigurationError("profile_conflict: " + setting)


def validate_local_addresses(interface, address):
    try:
        rows = json.loads(run_command([IP, "-j", "-4", "address", "show"]))
        if not isinstance(rows, list):
            raise TypeError
        for row in rows:
            for entry in row.get("addr_info", []):
                if entry["family"] != "inet":
                    continue
                current = ipaddress.IPv4Interface(f"{entry['local']}/{entry['prefixlen']}")
                if row["ifname"] == interface:
                    conflict = current != address
                else:
                    conflict = current.network.overlaps(address.network)
                if conflict:
                    raise ConfigurationError(
                        "address_conflict: existing interface address or subnet"
                    )
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ConfigurationError("invalid_address_inventory") from None


def configure(user, interface, address, *, sysfs=Path("/sys/class/net")):
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        raise ConfigurationError("requires_linux_aarch64")
    if getattr(os, "geteuid", lambda: -1)() != 0:
        raise ConfigurationError("requires_root: run this reviewed helper locally with sudo")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
        raise ConfigurationError("invalid_user")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,14}", interface):
        raise ConfigurationError("invalid_interface")
    address = validate_address(address)
    uid, member = lookup_identity(user)
    if uid == 0:
        raise ConfigurationError("requires_nonroot_user")
    device = sysfs / interface
    try:
        if (
            not (device / "device").exists()
            or (device / "type").read_text().strip() != "1"
            or any((device / item).exists() for item in ("wireless", "phy80211", "master"))
            or (device / "carrier").read_text().strip() != "1"
        ):
            raise ConfigurationError("requires_connected_physical_ethernet")
    except OSError:
        raise ConfigurationError("invalid_interface_metadata") from None

    matches = []
    ids = nm_value("UUID", "connection", "show").splitlines()
    for profile_id in ids:
        try:
            UUID(profile_id)
        except ValueError:
            raise ConfigurationError("invalid_profile_inventory") from None
        if nm_value("connection.id", "connection", "show", "uuid", profile_id) == PROFILE:
            matches.append(profile_id)
    if len(matches) > 1:
        raise ConfigurationError("duplicate_profile: voiceup-direct")
    profile_id = matches[0] if matches else str(uuid4())
    if matches:
        validate_profile(profile_id, interface, str(address))
    active = nm_value("GENERAL.CON-UUID", "device", "show", interface)
    if active and active != profile_id:
        raise ConfigurationError("interface_in_use: another connection is active")
    validate_local_addresses(interface, address)

    # Every validation above finishes before the first network/group mutation.
    if not matches:
        options = {"connection.uuid": profile_id, **connection_settings(str(address))}
        run_command(
            [
                NMCLI,
                "connection",
                "add",
                "type",
                "ethernet",
                "con-name",
                PROFILE,
                "ifname",
                interface,
                *[word for pair in options.items() for word in pair],
            ]
        )
        validate_profile(profile_id, interface, str(address))
    if active != profile_id:
        run_command(
            [NMCLI, "--wait", "30", "connection", "up", "uuid", profile_id, "ifname", interface]
        )
        if nm_value("GENERAL.CON-UUID", "device", "show", interface) != profile_id:
            raise ConfigurationError("activation_not_confirmed")
    if not member:
        run_command([USERMOD, "-aG", "docker", user])
        if not lookup_identity(user)[1]:
            raise ConfigurationError("group_membership_not_confirmed")
    return {
        "profile": "existing" if matches else "created",
        "activation": "already_active" if active == profile_id else "activated",
        "docker_group": "already_member" if member else "added",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--address", required=True)
    args = parser.parse_args(argv)
    try:
        result = configure(args.user, args.interface, args.address)
    except ConfigurationError as exc:
        print(
            f"Configuration stopped: {exc}. Earlier successful steps may remain.", file=sys.stderr
        )
        return 1
    print(
        f"{PROFILE}: {args.interface} {args.address}; "
        + "; ".join(f"{key}={value}" for key, value in result.items())
    )
    print("Open a new login/SSH session to use Docker group membership.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
