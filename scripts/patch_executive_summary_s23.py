#!/usr/bin/env python3
"""Re-apply the S23 fixes to docs/executive-summary.html (HEAD content + 3 broken-link fixes + review pointers).

The test suite re-renders that page from another renderer; run this after pytest to restore it.
Run from the repository root: python3 scripts/patch_executive_summary_s23.py
"""
from pathlib import Path
import subprocess
import os
os.chdir(Path(__file__).resolve().parents[1])
s=subprocess.run(['git','show','HEAD:docs/executive-summary.html'],capture_output=True,text=True,check=True).stdout
for name in ['run-card-S18-UNIQUE.json','HYPOTHESES_S18_UNIQUE.md','GEOTHERMAL_VENT_KNOWLEDGE_BASE.md']:
    s=s.replace(f'href="docs/{name}"', f'href="{name}"')
aside=('<aside style="background:#fff0e9;border-left:4px solid #9c3d25;padding:14px 18px;margin:14px 0">'
 '<strong>Do not upload the S22 file from this guide.</strong> Reading this guide is not an approval to upload that file. OK TO SUBMIT: NO for every file listed here. '
 'Historical review pointers: <a href="REVIEW-ACTIVE-E649E460-20261025.md">REVIEW-ACTIVE-E649E460-20261025.md</a> · '
 '<a href="run-card-E649E460-20261025.json">run-card-E649E460-20261025.json</a>. '
 'Current front door, dated 2026-10-27: <a href="../index.html">START HERE</a>.</aside>')
i=s.index('<main'); j=s.index('>',i)+1
Path('docs/executive-summary.html').write_text(s[:j]+aside+s[j:])
print('patched executive-summary')
