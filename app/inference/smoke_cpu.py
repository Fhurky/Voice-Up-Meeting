#!/usr/bin/env python3
"""Exercise real CPU VAD/ECAPA and private HTTP inside a network-none container.

Supply a previously prepared clean speech fixture with at least ten usable seconds.
This checks software wiring, not held-out speaker recognition accuracy.
"""

import argparse
import json
from pathlib import Path

from smoke_cuda import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-profile", choices=["x86_64-cpu", "aarch64-cpu"], required=True)
    parser.add_argument("fixtures", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.fixtures, cpu_profile=args.runtime_profile), indent=2))
