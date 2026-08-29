# AUTOLEDGER permanent guided-tutorial update policy

This is a release-blocking rule for every future AUTOLEDGER Free and Pro revision.

1. A clean installation automatically starts the complete beginner Guided Tutorial.
2. A clean installation MUST NOT show `NEW IN THIS UPDATE`.
3. An update over any supported older AUTOLEDGER installation automatically starts with `NEW IN THIS UPDATE` as the first guided screen.
4. Every new/changed feature in that software revision must be included in the update-feature curriculum before release.
5. After the update-feature section, the normal guided workflow/refresher remains available.
6. Required-action tutorial steps keep `Next` disabled until the application can verify the action/result has been completed.
7. The tutorial must use plain language suitable for a first-time learner and may provide clearly labelled example/test values. Examples are never represented as universal Pastel codes.
8. `Skip tutorial` must always be available.
9. The complete Guided Tutorial must be runnable again from Tutorial & Help.
10. Searchable Help remains the complete reference for every user-facing feature and must be updated together with the tutorial.
11. Tutorial completion/update state is version-aware. A previous completion must not suppress the tutorial for a newer software update.
12. Free and Pro use the same tutorial behaviour.
13. Every future Pro revision remains an UPDATE to the same product and must preserve existing valid `ALP225R6` permanent entitlements, profiles, settings and customer data.
14. Full / Stand-alone and Update installers must both write an install-context marker so the application can distinguish a clean installation from an update reliably.
15. CI must block a release if the new revision has no `NEW IN THIS UPDATE` curriculum, if clean/update ordering is wrong, or if update compatibility checks fail.
