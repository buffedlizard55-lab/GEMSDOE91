# Submission guide — current automated decision

**OK to download the new research TIFF. NOT OK TO SUBMIT it.**

Use the [executive summary](executive-summary.html) for the exact process, short
name/note, range-error explanation and links to the real file. The [run card](run-card.json)
is authoritative evidence; `src/gems91/readiness.py` is the shared fail-closed policy.

```bash
python scripts/restore_data.py --only sample_submission,existing_faults
python scripts/verify_current_artifact.py --with-data
```

A format PASS is not a novelty/science/selector PASS. No human inspector is needed
to reach the current negative verdict, and no automatic competition upload exists.
Only a future candidate clearing every automated gate plus the separate selector
may use a weekly slot. Record actual organizer-page receipts as ORGANIZER-CONFIRMED;
never infer scores from projections, a filename or a third-party page.

Previous upload queues and model forecasts are archived, not active advice:
[historical instructions](archive/SUBMIT-before-CED91.md).
