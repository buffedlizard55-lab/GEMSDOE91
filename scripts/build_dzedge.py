#!/usr/bin/env python3
"""Retired DZ-EDGE builder: fail closed instead of generating a noncompliant raster.

The historical artifact and its audit remain under docs/downloads/ and in the
run card. This script is intentionally not a private rebuild of the template:
its former implementation only compared final dots with parent R0, lacked a
pre-placement surface scan and complete-registry scan, and its hide-and-recover
score did not validate the off-catalogue hypothesis. Those checks are necessary
under the current parallel-run protocol. Use the shared evaluator/writer only
after an exact lane is assigned and the common complete-scope registry gate is
available.
"""
from __future__ import annotations


def main() -> int:
    print(
        "BUILD BLOCKED: retired DZ-EDGE runner lacks an assigned lane and "
        "complete two-phase registry gates; no artifact written."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
