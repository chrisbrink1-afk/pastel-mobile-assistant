from __future__ import annotations
import json, re, sys
from pathlib import Path
from help_topics import COMPLETE_HELP_TOPICS

# Every actionable control currently present in the reconstructed R8 core must map
# to a help topic. If a future build adds an actionable control and does not add it
# here with documentation, CI fails.
CONTROL_TOPIC_MAP = {
    'No VAT':'vat', 'VAT':'vat', 'Use amount-based allocation rule':'amount_rule',
    'Assign selected…':'amount_review', 'Select all shown':'amount_review', 'Clear selection':'amount_review',
    'Cancel':'rule_save_cancel', 'Save rule':'rule_save_cancel', 'Apply':'manual_fields',
    'Assign selected':'amount_review', 'Apply correction':'correct_auto', 'Clear search':'help_search',
    'Re-scan my progress':'tutorial_controls', 'Skip tutorial':'tutorial_controls', 'Close':'tutorial_controls',
    'Next':'tutorial_controls', 'Back':'tutorial_controls', 'New':'profile_buttons', 'Rename':'profile_buttons',
    'Delete':'profile_buttons', 'Load bank CSV...':'load_csv', 'Review Payments':'payments_receipts',
    'Review Receipts':'payments_receipts', 'Check selected for errors':'validation',
    'Export selected to Pastel...':'export', 'Tutorial & searchable help':'help_search',
    'Apply saved rules':'apply_saved_rules', 'Modern UI':'ui_modes', 'Tutorial & Help':'help_search',
    'Classic UI':'ui_modes', 'Export to Pastel':'export', 'Validate':'validation', 'Load statement':'load_csv',
    'Clear':'repeat_description', 'New payment rule':'new_rules', 'New receipt rule':'new_rules',
    'Edit':'rules_overview', 'Export rules backup…':'rules_backup', 'Import rules backup…':'rules_backup',
    'Save settings':'save_settings', 'Export settings backup…':'settings_backup',
    'Import settings backup / v1.10 database…':'import_settings',
}

# Controls/fields whose labels are generated dynamically or are not all discovered
# as action widgets by the AST inventory still receive an explicit coverage gate.
REQUIRED_FIELD_TERMS = {
    'Rule name':'rule_name', 'Name / number to match':'match_text',
    'General ledger account':'gl_account', 'GL account':'gl_account',
    'Pastel description':'pastel_description', 'Pastel reference':'pastel_reference',
    'Priority':'priority', 'Matching method':'matching_methods', 'Pastel tax type':'tax_type',
    'If amount':'amount_condition', 'Alternative GL':'alternative_allocation',
    'Alternative description':'alternative_allocation', 'Find':'find_search', 'Show':'show_filter',
    'Repeat description':'repeat_description', 'Sort date':'sort_date', 'Export selection':'export_tick',
    'Recurring allocation tools':'recurring_allocation', 'Quick select for export':'quick_select',
    'Cash Book bank GL':'contra_account', 'VAT tax type number':'vat_setting', 'VAT rate':'vat_rate',
    'Fiscal year start month':'fiscal_month', 'Project code':'project_code',
}

REQUIRED_TOPIC_IDS = {
    'welcome','workflow','company_profiles','profile_buttons','dashboard','ui_modes','load_csv',
    'payments_receipts','transaction_table','export_tick','status_colors','find_search','show_filter',
    'repeat_description','sort_date','allocation_tools','assign_once','manual_fields','save_rule_vs_once',
    'correct_auto','apply_saved_rules','rules_overview','new_rules','rule_name','match_text','matching_methods',
    'priority','gl_account','pastel_description','pastel_reference','vat','tax_type','amount_rule',
    'amount_condition','amount_actions','alternative_allocation','amount_review','rule_save_cancel','recurring',
    'recurring_tree','recurring_allocation','quick_select','validation','validation_errors','export',
    'receipt_sign','references','settings_overview','contra_account','vat_setting','vat_rate','fiscal_month',
    'project_code','save_settings','rules_backup','settings_backup','import_settings','autosave','help_search',
    'tutorial_controls','free_edition','pro_edition','pro_transfer','privacy','install_update','uninstall'
}


def _words(value: str):
    return re.findall(r'[a-z0-9]+', value.lower())


def _term_is_explained(term: str, text: str) -> bool:
    """Accept natural grammatical forms such as selection/selected without weakening feature coverage."""
    term_words = _words(term)
    text_words = _words(text)
    for wanted in term_words:
        stem = wanted[:6] if len(wanted) >= 7 else wanted
        if not any(word == wanted or word.startswith(stem) or wanted.startswith(word[:6]) for word in text_words):
            return False
    return True


def main(inventory_path: str) -> None:
    topics = {t['id']: t for t in COMPLETE_HELP_TOPICS}
    missing_ids = sorted(REQUIRED_TOPIC_IDS - set(topics))
    if missing_ids:
        raise SystemExit(f'Missing required help topics: {missing_ids}')
    if len(topics) != len(COMPLETE_HELP_TOPICS):
        raise SystemExit('Duplicate help topic IDs detected')
    if len(topics) < 60:
        raise SystemExit(f'Help curriculum unexpectedly small: {len(topics)} topics')

    for topic_id, topic in topics.items():
        if len(topic.get('body','').strip()) < 80:
            raise SystemExit(f'Help topic is too brief for a beginner: {topic_id}')
        if not topic.get('keywords','').strip():
            raise SystemExit(f'Help topic has no search keywords: {topic_id}')

    inv = json.loads(Path(inventory_path).read_text(encoding='utf-8'))
    actionable = sorted({r['text'] for r in inv.get('controls',[]) if r.get('type') in {'Button','Checkbutton','Radiobutton'}})
    undocumented = [label for label in actionable if label not in CONTROL_TOPIC_MAP]
    if undocumented:
        raise SystemExit('Actionable UI controls without an explicit help mapping: ' + repr(undocumented))
    bad_targets = sorted({topic for topic in CONTROL_TOPIC_MAP.values() if topic not in topics})
    if bad_targets:
        raise SystemExit(f'Control mappings point at missing topics: {bad_targets}')

    missing_terms=[]
    for term, topic_id in REQUIRED_FIELD_TERMS.items():
        if topic_id not in topics:
            missing_terms.append((term, topic_id))
            continue
        topic = topics[topic_id]
        text = topic['title']+' '+topic['keywords']+' '+topic['body']
        if not _term_is_explained(term, text):
            missing_terms.append((term, topic_id))
    if missing_terms:
        raise SystemExit(f'Fields/features lacking explicit beginner help: {missing_terms}')

    # High-risk explanations that previously caused confusion must always remain explicit.
    priority = topics['priority']['body'].lower()
    for phrase in ['higher numbers have higher priority','leave normal rules at 100','200 or 300']:
        if phrase not in priority:
            raise SystemExit(f'Priority help lost required explanation: {phrase}')
    methods = topics['matching_methods']['body'].lower()
    for phrase in ['smart name + number','contains','starts with','exact']:
        if phrase not in methods:
            raise SystemExit(f'Matching-method help incomplete: {phrase}')

    print(f'PASS: {len(topics)} complete help topics cover {len(actionable)} actionable controls plus required fields/features.')


if __name__ == '__main__':
    main(sys.argv[1])
