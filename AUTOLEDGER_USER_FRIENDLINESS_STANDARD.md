# AUTOLEDGER — Permanent User-Friendliness Standard

This is a standing release requirement.

1. Treat every user as a first-time learner. Never assume knowledge of accounting software, bank CSV files, GL accounts, VAT, tax types, Pastel imports, matching rules, filters, recurring transactions, licensing, backups or installation terminology.
2. The Tutorial must cover every user-facing feature, field, button, option, workflow, warning and setting. It may be long; completeness is more important than assuming something is obvious.
3. Searchable Help must use the same complete knowledge source and allow ordinary-language searches.
4. Each explanation should state: what the feature is, when to use it, what happens when it is used, important consequences/cautions, and an example where useful.
5. Labels such as Priority, Matching method, Contra Account, Tax type and similar technical terms must be defined plainly before relying on the term.
6. New software features are not release-complete until Tutorial and searchable Help are updated.
7. CI should inventory actionable user-interface controls and fail the build when a new actionable control is not mapped to Help.
8. Pro software updates must continue accepting existing valid permanent Pro entitlements unless explicitly authorised otherwise.
9. Full / Stand-alone installers and in-place Update installers must both remain available for Free and Pro when a release is distributed.
