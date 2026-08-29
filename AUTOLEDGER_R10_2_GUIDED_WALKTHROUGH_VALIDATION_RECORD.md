# AUTOLEDGER v2.2.5 R10.2 — True Guided Walkthrough validation record

R10.2 corrects the R10/R10.1 tutorial design so the tutorial behaves as a real action-gated walkthrough rather than a slide-like information window.

## Permanent tutorial requirements

- Clean installation starts with the beginner Welcome workflow and never shows `NEW IN THIS UPDATE`.
- An update from an older supported installation starts with `NEW IN THIS UPDATE`, then covers the new/changed features before the workflow/refresher.
- Back, Next and Skip Tutorial must remain physically visible and usable throughout the walkthrough.
- Long instructions scroll inside the walkthrough; navigation controls must not be pushed off-screen.
- Required steps keep Next disabled until AUTOLEDGER detects that the real action has actually been completed.
- AUTOLEDGER points at the real application control with an animated `DO THIS NOW` pointer.
- Saved Rule creation is taught field by field, including Rule name, matching text, matching method, transaction GL, VAT/tax type, Priority, optional amount allocation, and Save Rule.
- Priority: normal/default 100; higher values such as 200/300 only when a more specific rule must take precedence over a broader rule.
- Searchable Help remains the complete reference for all user-facing features.
- Every future software revision must register its own update curriculum and preserve this walkthrough policy.

## Windows validation

Branch: `autoledger-r10-2-guided-walkthrough`

Validated source/build commit: `092cd88b11320e087ef8ae31db437b02a533ef69`

GitHub Actions run: `33278758193`

Artifact ID: `9722343205`

Artifact digest: `sha256:fe08000e55edf2d83529410d2e989e45a361e51208b17386d5d420c336526ad8`

The Windows acceptance gate proved, among other things:

- update walkthrough begins with `NEW IN THIS UPDATE`;
- clean walkthrough begins with `Welcome` and contains no fake update introduction;
- Back, Next and Skip Tutorial are mapped and physically inside the visible walkthrough window;
- Next actually advances and Back actually returns;
- Skip Tutorial actually closes the walkthrough;
- the Profile step disables Next until the profile is actually renamed;
- after the real profile rename the gate unlocks Next;
- the animated pointer can find the real Profile control;
- the Saved Rule curriculum contains separate steps for rule open/name/match/method/GL/VAT/Priority/optional amount/save;
- complete beginner Help coverage passed;
- self-contained Free and Pro Windows applications built and smoke-tested;
- all four installers built;
- UPDATE recognises R6, R8, R9, R10 and R10.1 and refuses a clean PC;
- R10.1 -> R10.2 update preserved Free usage state, tutorial history and the permanent R6-compatible Pro entitlement;
- clean Full installations wrote clean tutorial context;
- complete Free and Pro source packages were generated from the exact effective validated source.

## Permanent licence compatibility

R10.2 retains the existing `ALP225R6` permanent Pro entitlement lineage, R6 AppIds, AppData namespaces and `pro_licence_r6.json` storage. A customer does not require a new permanent licence because AUTOLEDGER is updated.

## Signing status

These R10.2 packages remain unsigned TEST builds until the AUTOLEDGER SYSTEMS PTY LTD Windows code-signing certificate is available.
