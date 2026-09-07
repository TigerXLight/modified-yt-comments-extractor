from __future__ import annotations
import datetime
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from profile_media_archive_source_role_surface_r42ds import build_archive_source_role_surface_from_result


def main() -> int:
    root = Path.cwd()
    out = root / 'profile_media_live_captures' / 'r42ds_archive_source_roles_webview2' / ('probe_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True, exist_ok=True)
    article = out / 'article_text.txt'
    article.write_text(
        "People shout seagull eater in the street because of far right lies.\n\n"
        "Published by Metro News. Nora Mubarak told Metro the abuse followed propagated claims online.\n\n"
        "She described what happened and the report preserves her account for review.",
        encoding='utf-8',
    )

    class Artifact:
        artifact_kind = 'article_text'
        local_path = article
        media_type = 'text/plain'
        def to_dict(self):
            return {'artifact_kind': 'article_text', 'local_path': str(article), 'media_type': 'text/plain'}

    class Result:
        status = 'success'
        article_status = 'material_from_native_webview2_live_document'
        browser_status = 'NATIVE_WEBVIEW2_LIVE_MATERIAL_OK'
        output_dir = str(out)
        artifacts = (Artifact(),)

    class Row:
        row_id = 'archive-row-03'
        title = 'People shout seagull eater'

    surface = build_archive_source_role_surface_from_result(
        row=Row(),
        result=Result(),
        source_url='[https://archive.ph/6mr3C](https://archive.ph/6mr3C)',
        source_title='People shout seagull eater',
        output_root=out,
    )
    summary = surface.to_dict()
    (out / 'r42ds_probe_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'mode': 'probe',
        'schema': 'ytce.r42ds.archive_source_role_surface_probe.v1',
        'outdir': str(out),
        'canonical_source': summary['canonical_source'],
        'span_count': summary['span_count'],
        'role_counts': summary['role_counts'],
        'first_span_source_url': summary['claim_role_spans'][0]['source_url'] if summary['claim_role_spans'] else '',
        'side_effects': summary['side_effects'],
    }, ensure_ascii=False, indent=2))
    print('[DONE] Probe output:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
