#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import profile_media_facebook_auto_expand_comments_runner_r45d as r45d
import profile_media_facebook_modal_progress_hidden_comments_runner_r45f as r45f

MARKER = "YTCE_R45G_FACEBOOK_MODAL_HIDDEN_REPLIES_RUNNER"
STATUS_PASS = "PASS_R45G_FACEBOOK_MODAL_HIDDEN_REPLIES_RUNNER"
STATUS_NEEDS_MORE_EXPANSION = "NEEDS_MORE_EXPANSION_R45G_FACEBOOK_MODAL_HIDDEN_REPLIES_RUNNER"
STATUS_BLOCKED = "BLOCKED_R45G_FACEBOOK_MODAL_HIDDEN_REPLIES_RUNNER"
SCHEMA_VERSION = "facebook_modal_hidden_replies_runner.r45g.v1"

# R45G keeps the R45F modal/progress scroller but explicitly includes Facebook's
# "View hidden replies" controls. The previous R45F patterns covered hidden
# comments and visible reply expansions, but a live Facebook modal showed separate
# "View hidden replies" controls that could remain unclicked.
JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND = (
    r45f.JS_MODAL_PROGRESS_HIDDEN_COMMENTS_AUTO_EXPAND
    .replace('view hidden comments|\\d+\\s+of\\s+\\d+', 'view hidden comments|view hidden repl(?:y|ies)|hidden repl(?:y|ies)|\\d+\\s+of\\s+\\d+')
    .replace('view hidden comments|view all .* replies|view \\d+ repl|write a comment|\\d+\\s+of\\s+\\d+', 'view hidden comments|view hidden repl(?:y|ies)|hidden repl(?:y|ies)|view all .* replies|view \\d+ repl|write a comment|\\d+\\s+of\\s+\\d+')
    .replace('if (/hidden comments?/i.test(text)) priority += 10000;', 'if (/hidden (?:comments?|repl(?:y|ies))/i.test(text)) priority += 12000;')
)

EXPAND_PATTERNS_R45G = [
    r'view\s+hidden\s+comments?',
    r'view\s+\d+\s+hidden\s+comments?',
    r'hidden\s+comments?',
    r'view\s+hidden\s+repl(?:y|ies)',
    r'view\s+\d+\s+hidden\s+repl(?:y|ies)',
    r'hidden\s+repl(?:y|ies)',
    r'view\s+(?:more|previous)\s+comments?',
    r'view\s+\d+\s+more\s+comments?',
    r'view\s+(?:more|previous)\s+repl(?:y|ies)',
    r'view\s+\d+\s+more\s+repl(?:y|ies)',
    r'view\s+all\s+\d+\s+repl(?:y|ies)',
    r'view\s+\d+\s+repl(?:y|ies)',
    r'view\s+repl(?:y|ies)',
    r'see\s+more',
    r'show\s+more',
    r'more\s+comments?',
    r'more\s+repl(?:y|ies)',
]


def contract() -> Dict[str, Any]:
    base = r45f.contract()
    base.update({
        'marker': MARKER,
        'mode_id': 'facebook_modal_hidden_replies_runner',
        'schema_version': SCHEMA_VERSION,
        'primary_route': 'operator-controlled signed-in Facebook Chromium/WebView2 session; target the Facebook post modal/dialog; click hidden-comments, hidden-replies, reply, and see-more controls; scroll modal/comment containers until modal progress and coverage stop improving; then capture DOM/text/screenshots',
        'r45f_gap_fixed': 'R45F handled modal progress and hidden comments, but live testing showed separate Facebook controls labelled View hidden replies. R45G explicitly matches and prioritizes View hidden replies / hidden replies controls.',
        'hidden_replies_rule': 'click visible View hidden replies controls in addition to View hidden comments, View 1 reply, View all replies, View more replies, and See more.',
    })
    return base


def side_effect_flags(browser: bool, network: bool, auto_clicks: bool) -> Dict[str, Any]:
    flags = r45f.side_effect_flags(browser, network, auto_clicks)
    flags['visible_hidden_replies_clicks_supported'] = True
    flags['facebook_modal_hidden_replies_runner_invoked'] = True
    flags.pop('facebook_modal_progress_hidden_comments_runner_invoked', None)
    return flags


def patch_r45d_globals() -> None:
    r45f.patch_r45d_globals()
    r45d.MARKER = MARKER
    r45d.STATUS_PASS = STATUS_PASS
    r45d.STATUS_NEEDS_MORE_EXPANSION = STATUS_NEEDS_MORE_EXPANSION
    r45d.STATUS_BLOCKED = STATUS_BLOCKED
    r45d.SCHEMA_VERSION = SCHEMA_VERSION
    r45d.EXPAND_PATTERNS = list(EXPAND_PATTERNS_R45G)
    r45d.JS_AUTO_EXPAND = JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND
    r45d.sanitize_target_url = r45f.sanitize_target_url
    r45d.contract = contract
    r45d.side_effect_flags = side_effect_flags


def build_static_capture(candidate_text: str, output_root: Path, reference_text: Optional[str] = None, source_url: str = 'static_text', min_coverage: float = 0.25) -> Dict[str, Any]:
    patch_r45d_globals()
    return r45d.build_static_capture(candidate_text, output_root, reference_text=reference_text, source_url=source_url, min_coverage=min_coverage)


def run_self_test(args: argparse.Namespace) -> Dict[str, Any]:
    patch_r45d_globals()
    reference = '''Tony Bentley
Mohhamed etc is the first name of all muslim boys as it's the name of their prophet.
Dan Melin
Look I'm all for Restore, but this graph is so skewed.
Alex Barron
Context is everything
'''
    result = build_static_capture(reference, Path(args.output_root), reference_text=reference, source_url='self_test_fixture', min_coverage=0.99)
    joined_patterns = '\n'.join(r45d.EXPAND_PATTERNS).lower()
    checks = [
        {'name': 'modal_progress_parser_present', 'status': 'pass' if 'parseProgress' in JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND and 'of' in JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND and 'progress' in JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND.lower() else 'fail'},
        {'name': 'view_hidden_comments_pattern_supported', 'status': 'pass' if 'view\\s+hidden\\s+comments?' in joined_patterns else 'fail'},
        {'name': 'view_hidden_replies_pattern_supported', 'status': 'pass' if 'view\\s+hidden\\s+repl' in joined_patterns and 'hidden repl' in JS_MODAL_HIDDEN_REPLIES_AUTO_EXPAND.lower() else 'fail'},
        {'name': 'view_one_reply_pattern_supported', 'status': 'pass' if 'view\\s+\\d+\\s+repl' in joined_patterns else 'fail'},
        {'name': 'reference_comparison_matches_sentinels', 'status': 'pass' if result.get('comparison') and result['comparison']['coverage_ratio'] >= 0.99 and all(result['comparison']['sentinel_report'].values()) else 'fail'},
        {'name': 'side_effects_safe', 'status': 'pass' if not any(v for k, v in result['side_effect_flags'].items() if k not in {'facebook_modal_hidden_replies_runner_invoked','visible_hidden_comments_clicks_supported','visible_hidden_replies_clicks_supported'}) else 'fail'},
    ]
    status = STATUS_PASS if all(c['status'] == 'pass' for c in checks) else STATUS_BLOCKED
    report = {'marker': MARKER, 'status': status, 'schema_version': SCHEMA_VERSION, 'generated_at': _dt.datetime.now(_dt.timezone.utc).isoformat(), 'checks': checks, 'sample_result': result, 'contract': contract(), 'side_effect_flags': side_effect_flags(False, False, False)}
    r45d.write_json(Path(args.output_root) / 'r45g_self_test_report.json', report)
    print(MARKER)
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    patch_r45d_globals()
    ap = r45d.build_arg_parser()
    ap.description = 'R45G Facebook modal hidden-replies runner'
    ap.set_defaults(output_root='profile_media_live_captures/r45g_facebook_modal_hidden_replies_runner')
    ap.set_defaults(expand_rounds=480)
    ap.set_defaults(expand_max_clicks_per_round=36)
    ap.set_defaults(expand_scrolls_per_round=10)
    ap.set_defaults(expand_scroll_px=900)
    ap.set_defaults(expand_stop_after_stable_rounds=28)
    ap.set_defaults(tile_steps=300)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    patch_r45d_globals()
    ap = build_arg_parser()
    args = ap.parse_args(argv)
    if args.self_test:
        report = run_self_test(args)
        return 0 if report.get('status') == STATUS_PASS else 2
    if args.candidate_text:
        result = r45d.run_from_text_files(args)
        return 0 if result.get('status') == STATUS_PASS else 2
    if args.target_url or args.manual_current_page:
        result = r45d.run_live(args)
        if result.get('status') == STATUS_PASS:
            return 0
        if result.get('status') == STATUS_NEEDS_MORE_EXPANSION:
            return 3
        return 2
    ap.print_help()
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
