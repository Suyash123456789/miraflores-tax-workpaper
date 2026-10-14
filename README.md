# MiraFlores Tax Workpaper prototype

An evidence-first local workpaper for the supplied Okafor–Lindqvist 2025 case packet. The app traces return lines to source documents, extracted observations, calculations, issues, review decisions, and audit history.

## Run locally

Requires Python 3.10+ and a modern browser. In PowerShell, from this folder:

```powershell
python server.py
```

Open <http://127.0.0.1:8765/workpaper.html>. The server binds to loopback by default. Stop it with Ctrl+C. Interactive state is saved in SQLite at `../work/workpaper-data.sqlite`; it persists across app restarts on this machine.

The role selector previews Preparer, Reviewer, Partner, Client, Firm administrator, and Examiner views. Roles are simulated with a request header and are **not authenticated identities or production access controls**. Keep this demo on your machine; do not expose it to the public internet with real taxpayer data.

## Packet behavior and GitHub safety

- If `okafor_lindqvist_2025_packet.json` is present beside `server.py`, the app loads that delivered packet unchanged. It is intentionally excluded from Git by `.gitignore` because it contains sensitive tax case data.
- A fresh Git checkout falls back to `.demo-data/packet.json`, a redacted copy that preserves the walkthrough findings. The fallback file is served to the app API but blocked as a static file.
- The packet itself is read-only. App-owned notes, decisions, draft workpaper values, sign-offs, and audit events are stored separately in SQLite.
- Source pages are simulated from packet `printed_content`; original document files were not supplied.

## Prototype limits

The app does not calculate or recompute tax, determine tax law, transmit an e-file, send client communications, or provide real authentication. Return versions supplied in the packet remain immutable baselines; proposals are drafts and do not change an official return amount.

## Case-study handoff

See [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md) for GitHub publishing steps, deliverable map, findings, and the video recording plan. The one-page idea/data model is [Product-and-data-model.md](Product-and-data-model.md); verified findings are in [Verified-error-report.md](Verified-error-report.md); the spoken walkthrough is in [Walkthrough-script.md](Walkthrough-script.md).
