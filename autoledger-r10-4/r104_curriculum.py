from __future__ import annotations

R104_REVISION = "R10.4"

R104_UPDATE_FEATURES = (
    {
        "id": "update_r104_non_obscuring",
        "title": "Tutorial instructions no longer cover the control you need",
        "body": (
            "R10.4 continuously repositions the tutorial instruction bubble around the highlighted control. "
            "AUTOLEDGER checks the available space to the right, left, below and above the target and chooses a position that keeps the control clear for clicking or typing."
        ),
    },
    {
        "id": "update_r104_arrow",
        "title": "An animated arrow now points to the exact control",
        "body": (
            "R10.4 adds a gentle animated arrow beside the highlighted field, button, checkbox, dropdown or table. "
            "The arrow moves toward the target without sitting on top of the target, while the four-sided highlight remains visible."
        ),
    },
    {
        "id": "update_r104_targeting",
        "title": "Tutorial targeting now prefers the real interactive widget",
        "body": (
            "The walkthrough now ranks visible interactive controls before labels. Settings steps prefer the actual Entry, dropdown or checkbox; "
            "action steps prefer the exact button; transaction steps prefer the real transaction table; and Saved Rule steps follow the normal Saved Rule dialog field by field."
        ),
    },
    {
        "id": "update_r104_update_rule",
        "title": "R10.4 is available as both an update and a full installer",
        "body": (
            "If AUTOLEDGER is already installed, use the R10.4 Update installer so existing local data is preserved. "
            "The Full / Standalone installer remains available for a clean PC or a clean installation."
        ),
    },
)

R104_HELP_TOPICS = (
    {
        "id": "guided_walkthrough_r104_non_obscuring",
        "title": "R10.4 non-obscuring Guided Walkthrough",
        "page": "dashboard",
        "keywords": "tutorial bubble move non obscuring arrow highlight exact button field click type",
        "body": (
            "R10.4 keeps the Guided Walkthrough inside AUTOLEDGER but moves the instruction bubble away from the control you must use. "
            "A four-sided highlight surrounds the target and a gentle animated arrow points toward it without covering its click or edit area."
        ),
    },
    {
        "id": "guided_walkthrough_r104_targeting",
        "title": "How R10.4 chooses tutorial targets",
        "page": "settings",
        "keywords": "tutorial target exact field button entry dropdown checkbox table label",
        "body": (
            "When a tutorial step names a setting or action, AUTOLEDGER first looks for a visible interactive control that exactly matches the instruction. "
            "If the visible text is a field label, the walkthrough resolves that label to the input control on the same row or the nearest logical interactive control."
        ),
    },
)


def register_r104_curriculum(guided_tutorial_module, revision: str = R104_REVISION) -> None:
    guided_tutorial_module.UPDATE_FEATURES_BY_REVISION[revision] = R104_UPDATE_FEATURES
