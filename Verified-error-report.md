# Packet error and exception report

This report separates a confirmed source omission from inconsistencies and open compliance or judgment items. A flagged difference is not automatically a tax error. Dollar effects below use the packet's v3 rate table only where the packet supplies a direct, small-change method; they are estimates, not an engine recomputation.

## Confirmed error

### Corrected Meridian 1099-B page 32 lot is absent from the computed return detail

- **Evidence:** D31 is marked corrected. Extracted field `ev-0703` (D31, page 1, `b_summary_proceeds`, “1099-B summary total proceeds”) is $71,965 at 99% confidence. D31 page 10 prints detail proceeds of $71,715. D31 page 32 prints M18: short-term noncovered, $250 proceeds and $310 basis. The packet extraction stops at 159 observations for D31 and says page 32 was not read. There is no M18 extracted-value record or M18 Form 8949 line in v3.
- **Check:** $71,715 extracted lot proceeds + $250 from the page 32 lot = $71,965, so the summary agrees when the omitted page is included. The confirmed defect is the missing extraction and return detail, not an erroneous statement total.
- **Affected lines:** Short-term gain/loss on Schedule D line 7; Schedule D line 16; Form 1040 line 7; and the California capital-gain allocation on Schedule CA 540NR lines 7.D and 7.E. The precise filed-line updates require the tax engine and a California sourcing review.
- **Supported impact:** M18 is a $60 short-term loss ($250 − $310). Applying v3's supplied STCG rates gives an estimated tax decrease of $20.88 federal and $2.04 California, about $22.92 combined. This is a rate-based estimate; the application does not recalculate the return.
- **Status / next action:** Open in the prototype. Add the lot to the brokerage detail, link D31 page 32, rerun the official calculation, then obtain review of the resulting version before any amendment decision.
- **How the design surfaced it:** The issue queue compares the printed corrected statement summary, extracted lots, and return lines. Selecting D31 page 32 opens its simulated printed content, and reverse tracing shows the extracted M1–M17 lines but no M18.

## Confirmed process event, corrected before acceptance

### Dependent name/TIN e-file rejection

- **Evidence:** Agency e-file record `agency:/efile` records federal rejection R0000-504-02 on July 13, 2026, for dependent 2. Timeline events `tl-21` through `tl-24` show D71 arriving after rejection and federal acceptance July 14, followed by California acceptance July 15. Client message `msg-10` says Theo's organizer number was mistyped.
- **Impact:** Filing transmission was delayed; the packet records later acceptance. No tax-line change is supported by these records.
- **Status / next action:** Resolved in the filing history. Preserve rejection, identity evidence, resubmission IDs, and acceptances together.
- **How the design surfaced it:** Filing history groups each jurisdiction's rejection, hold, and acceptance with the late identity document and timeline.

## Discrepancies and unresolved risks

| Finding | Evidence and check | Classification / impact | Status and next action |
|---|---|---|---|
| Organizer says no investments sold; records contain brokerage and crypto dispositions | `qa-14`; packet v3 diagnostic `QUESTIONNAIRE_SALES_CONFLICT`; D30/D31, D34/D35 | Confirmed answer-to-record conflict, not proof the answer or return is wrong. No separate tax impact established. | Open. Clarify what the client meant and reconcile completeness. |
| Coinhaven C6 basis is zero in the engine, but client reports a prior $3,050 purchase | `ev-0879`, `ev-0881`, `ev-0882`, `ev-0918`, `ev-0919`; `msg-07`; D35 | Potential basis error. The bank statement line is not complete purchase/lot proof; date and holding-period treatment also need support. Tax impact not quantified. | Open. Obtain available external-account evidence and trace transfer continuity before changing basis. |
| S corporation basis changed after late 2023 K-1 arrived | D40; v2/v3 changes to F7203.1 ($8,200 → $2,300) and excess distribution ($15,315 → $21,215); D39 | Late evidence changed the v3 computation; this is not evidence that v3 ignored D40. A historic basis gap remains. No new v3 tax delta is asserted. | Open historical judgment. Reconstruct basis and preserve D40's effect in the version history. |
| Two contractor payments trigger a 1099-NEC filing diagnostic | D27; `call-01`; v3 `FORM_1099_FILING` diagnostic | Compliance follow-up, not a supported adjustment to the 2025 return. | Open. Determine required correction and document client guidance/completion. |
| California AMT is not computed | D12; v3 `CA_AMT_NOT_COMPUTED` diagnostic | Explicit computation gap; tax effect unavailable from this packet. | Open. Obtain an appropriate California AMT calculation or record scope disposition. |
| Swedish account exceeds the FBAR maximum threshold in the engine diagnostic | D36; `F8938.1.max`; v3 `FBAR_OUTSIDE_RETURN` | Separate filing/completeness item outside this return engagement. | Open. Identify filing owner and retain separate filing confirmation. |
| St. Brigid handwritten amount had 0.41 extraction confidence | D64, `ev-1049`; later client `msg-08` | Initially weak evidence; client reports phone confirmation of $1,500 and check #2207. This later statement supports the amount but remains client confirmation. | Resolved in packet workflow. Keep the confirmation and bank support attached to the deduction decision. |
| Halvorsen W-2 appears as a PDF and phone photo | D09 and D10; v3 `F1040.1a` note says D10 is a second image and counted once | Duplicate upload, not a duplicate-income error in the supplied result. | Handled in v3. Keep D10 classified as duplicate evidence rather than deleting it. |
| IRS Letter 566 requests noncash gift support and Schedule C receipts reconciliation | D72 / `N-2025-L566`; response due 2028-02-19 | Post-filing examination task, not itself proof of an erroneous filed amount. | Open. Prepare a self-contained response using the frozen return, source support, and an independently reviewed gross-receipts tie-out. |

The source page view is synthetic because the packet contains records and printed-content text, not original document files. The app does not claim independent OCR, tax-law recomputation, e-file transmission, legal e-signature, or a completed IRS response.
