from __future__ import annotations

R103_REVISION = "R10.3"

R103_UPDATE_FEATURES = (
    {
        "id": "update_r103_inline_walkthrough",
        "title": "The tutorial now stays inside AUTOLEDGER",
        "body": (
            "R10.3 removes the separate tutorial window. The walkthrough now stays inside the normal AUTOLEDGER screen, "
            "highlights the exact control you need to use, and places a short instruction bubble beside that control."
        ),
    },
    {
        "id": "update_r103_exact_highlights",
        "title": "Exact fields and buttons are highlighted",
        "body": (
            "When a step asks you to enter or change a value, AUTOLEDGER highlights the actual input box, dropdown, button or table "
            "you must use rather than merely pointing at a label. There is no pulsing or bouncing tutorial animation."
        ),
    },
    {
        "id": "update_r103_priority_guidance",
        "title": "Saved Rule Priority is explained clearly",
        "body": (
            "The Saved Rule walkthrough now explains that Priority 100 is the normal default. Higher values such as 200 or 300 are "
            "used only when a more specific rule must take precedence over another rule that could also match the same transaction."
        ),
    },
)

R103_HELP_TOPICS = (
    {
        "id": "inline_guided_walkthrough_r103",
        "title": "R10.3 inline Guided Walkthrough",
        "page": "dashboard",
        "keywords": "inline guided walkthrough highlight field speech bubble hint no popup no animation",
        "body": (
            "The R10.3 Guided Walkthrough runs inside the normal AUTOLEDGER interface. It highlights the exact control to use and "
            "shows a nearby hint bubble. No separate tutorial window is opened. Required steps keep Next disabled until the real action is complete."
        ),
    },
    {
        "id": "saved_rule_priority_r103",
        "title": "Saved Rule Priority — when to change 100",
        "page": "payments",
        "keywords": "saved rule priority 100 200 300 higher wins overlap specific broad rule precedence",
        "body": (
            "Leave Priority at 100 for a normal Saved Rule. Change it only when two or more rules could match the same transaction and "
            "a more specific rule must win. Higher numbers are considered first: for example, a specific exception at 200 can take "
            "precedence over a broader rule at 100. Do not increase Priority simply because a rule is important."
        ),
    },
)


def register_r103_curriculum(guided_tutorial_module, revision: str = R103_REVISION) -> None:
    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R103_UPDATE_FEATURES
