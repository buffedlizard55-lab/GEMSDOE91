#!/usr/bin/env python3
"""QUARANTINED historical recovery entry point.

The inherited script wrote estimated/placeholder holdout, novelty and projected
score numbers into evidence as if measured. It also republished a parent-derived
submission. Those actions violate the standing no-fabrication protocol.

Historical evidence remains archived for traceability, not as validated results.
Use generate_submission.py / scripts/verify_s16.py for the real-data measured
pipeline. A recovery job must recompute measurements, never synthesize receipts.
"""


def main():
    raise SystemExit('BLOCKED: legacy GEOD recovery fabricated evidence. No files written. See docs/REVIEW-S16.md.')


if __name__ == '__main__':
    main()
