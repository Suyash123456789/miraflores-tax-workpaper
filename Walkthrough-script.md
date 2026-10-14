# Candidate walkthrough script (3:30)

## Before recording

Start the prototype with `python server.py` from the outputs folder and open `http://127.0.0.1:8765/workpaper.html`. Set the browser window to a readable desktop width, close personal tabs/notifications, and use the built-in role selector. Keep the app in its clean demo state. Do not submit real client data or use the demo role switcher to imply real identity controls.

## Spoken script and screen plan

### 0:00-0:25 | Opening - Overview

**Show:** Overview dashboard.

**Say:** “Hi, I’m Suyash. I built this prototype as an evidence-first tax workpaper for the supplied Okafor-Lindqvist packet. The central design choice is that a tax amount should be reviewable back to its source and calculation context. The app treats the supplied return versions as immutable baselines; it does not pretend to recalculate tax.”

### 0:25-0:55 | Product idea and data model

**Show:** Dashboard, then Return Lines and Evidence.

**Say:** “The core record is a graph: source document and page, extracted observation, calculation input, return line and version, issue or question, professional decision, and audit event. Stable source IDs connect those records. That lets a preparer start from a return line and trace backward, or start from a document and see its known downstream lines. Confidence is metadata for prioritizing review; it is not treated as proof.”

### 0:55-1:50 | Walk the confirmed omission

**Show:** Issues > inspect the Meridian corrected 1099-B > click D31 page 32 > show the printed-content text and any linked extracted values/return lines.

**Say:** “This is the clearest confirmed source omission. The corrected statement summary is $71,965. The extracted page 10 lot detail totals $71,715, and page 32 prints another short-term noncovered lot, M18, with $250 proceeds and $310 basis. The packet has no extraction record or Form 8949 line for M18. Adding its proceeds reconciles the statement total, so the statement summary is not the error; the missing extraction and return detail are. The lot is a $60 loss. A rate-based estimate from the packet is about $22.92 combined federal and California reduction, but that is not a tax-engine recomputation, and California sourcing needs review.”

### 1:50-2:20 | Evidence trace and draft control

**Show:** Open a return line, inspect source references, then Changes & Versions.

**Say:** “The same references work in reverse. Return-line source links lead to extracted observations and the source page. If a reviewer proposes a change, it is saved as a draft with a reason and references. The filed and computed versions remain unchanged. Reversal adds an audit event instead of deleting history.”

### 2:20-2:55 | Review and role boundaries

**Show:** Role selector > Reviewer; Review & Sign-off page; point out blocker and version-bound sign-off behavior. If demonstrating interaction, add a clearly labeled demo note and resolve it before ending.

**Say:** “The role selector previews different views, and the API checks which actions each demo role can perform. Reviewer notes can block sign-off, and sign-offs bind to a return version. This is only a demonstration boundary: the role comes from a request header, not real authentication, so it is not production security.”

### 2:55-3:20 | Other surfaced risks

**Show:** Issues list or Filing History / Notice.

**Say:** “The queue also separates unresolved questions from confirmed errors: the organizer answer conflicts with recorded sales; crypto basis lacks primary support; California AMT is not computed; and the late S-corporation K-1 changes historical basis. The e-file rejection is shown as a resolved process event, while the Letter 566 remains a post-filing response task.”

### 3:20-3:35 | Close and tradeoffs

**Show:** Product/data model document or dashboard.

**Say:** “I chose a small Python and SQLite stack to keep the prototype runnable and its state inspectable. The packet is loaded as supplied, while app-owned notes and audit history are stored separately. The tradeoff is that this is a local single-machine demo with synthetic source-page rendering, no tax engine, no real identity service, and no e-file integration. Those are clear next steps before production use.”

## Recording checklist

- Record the browser and your own narration with a screen recorder, then review audio and legibility once.
- Keep it around three to four minutes; prioritize the M18 source-to-return trace and the draft-versus-filed distinction.
- Upload the recording to a video host you control and set link access so the hiring team can view it.
- Paste the real video URL in the submission email. Do not use the local `127.0.0.1` app URL as the video link.

No recording or hosted video URL is included with the prototype; this script is ready for you to record.
