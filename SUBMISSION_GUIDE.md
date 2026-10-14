# Case-study submission guide

## Run the workpaper

1. Use Python 3.10 or later.
2. In this folder, run `python server.py`.
3. Open <http://127.0.0.1:8765/workpaper.html>.
4. Use the top-right role selector to preview Preparer, Reviewer, Partner, Client, Firm administrator, and Examiner.
5. Create a clearly labeled demo note or draft if you want to show persistence. Stop and restart the server; the note remains in `../work/workpaper-data.sqlite`.

The app binds to your computer only by default. The local link is not a public website. Demo roles are not authentication, and the app is not suitable for real taxpayer work.

## Packet and repository handling

Your local copy will load `okafor_lindqvist_2025_packet.json` as delivered. That file is excluded from Git because the case packet contains tax case data. A fresh repository clone uses the sanitized `.demo-data/packet.json` fallback so the prototype still opens and the walkthrough remains reproducible. The issue facts are retained in the redacted copy.

To publish from your GitHub account:

1. Create an empty repository named `miraflores-tax-workpaper` under `Suyash123456789`. Do not add a README, license, or `.gitignore` on GitHub because this folder already contains them.
2. In this folder, run:

   ```powershell
   git remote add origin https://github.com/Suyash123456789/miraflores-tax-workpaper.git
   git push -u origin main
   ```

3. Confirm the repository's packet file is the redacted `.demo-data/packet.json`; do not force-add the original `okafor_lindqvist_2025_packet.json`.

The repo is a source-code handoff, not a publicly hosted app. GitHub Pages cannot run the Python/SQLite API. For a reviewer to use the app, share a screen recording or run it locally with them; use a separate persistent hosting service for a publicly reachable app.

## Deliverables

- **Working workpaper:** `workpaper.html`, `app.js`, `style.css`, and `server.py`; local SQLite persistence and a demonstration role switcher.
- **Core idea and data model:** [Product-and-data-model.md](Product-and-data-model.md) (one-page summary and evidence graph).
- **Errors and how they surface:** [Verified-error-report.md](Verified-error-report.md), led by the confirmed missing Meridian M18 lot and separated from unresolved questions.
- **Video plan and script:** [Walkthrough-script.md](Walkthrough-script.md), with a timed route and narration. Record your own screen and voice; no video file or video URL has been fabricated.

## Video recording route (about 3½ minutes)

1. Start on Overview. Introduce the evidence-first idea and say the app does not recompute tax.
2. In Issues, open the corrected Meridian 1099-B. Trace to D31 page 32 and show M18's $250 proceeds and $310 basis, then compare the $71,715 detail subtotal to the $71,965 statement summary.
3. Show linked return lines and explain the supported $60 loss and the estimate's limitations.
4. Open Changes & Versions. Show a draft proposal and explain that the supplied return versions stay unchanged and reversals remain in the audit trail.
5. Switch to Reviewer. Show a review blocker or scoped sign-off, then explain that the role switcher is a demo boundary, not real login security.
6. Show one or two unresolved exceptions (such as crypto basis support or the CA AMT scope gap). Close with the Python/SQLite tradeoff, synthetic source rendering, and no tax engine or e-file integration.

Keep the browser at a readable desktop size, close personal tabs/notifications, and avoid entering real data. Record with a screen recorder, review the file, then upload to a video host you control with view-by-link access. Paste the actual video URL into the hiring submission; the script is not itself a video link.

## Suggested final submission note

> Attached is my MiraFlores AI tax workpaper prototype. The repository contains the local runnable app and a redacted packet fallback; my local app loads the case packet as delivered. The one-page design/data model and evidence-backed issue report are included. Walkthrough video: [paste your actual video URL].
