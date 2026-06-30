#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

REPO = 'rodrigo-santos35-prestserv_petro/subsea-alm-configurations'
DEFAULT_BASE_REF = 'origin/main'
COMMENT_MARKER_PREFIX = '<!-- commit-link:'
COMMENT_MARKER_SUFFIX = '-->'


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    body: str


def run(cmd: List[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        raise RuntimeError(
            f'Command failed ({p.returncode}): {" ".join(cmd)}\n'
            f'STDOUT:\n{p.stdout.decode()}\nSTDERR:\n{p.stderr.decode()}\n',
        )
    return p.stdout.decode().strip()


def iter_commits(rev_range: str) -> Iterable[Commit]:
    # Record separator + unit separator parsing
    fmt = '%H%x1f%s%x1f%b%x1e'
    out = run(['git', 'log', '--no-color', f'--pretty=format:{fmt}', rev_range])
    if not out:
        return []
    records = out.split('\x1e')
    commits: List[Commit] = []
    for rec in records:
        rec = rec.strip()
        if not rec:
            continue
        parts = rec.split('\x1f')
        sha, subject = parts[0], parts[1] if len(parts) > 1 else ''
        body = parts[2] if len(parts) > 2 else ''
        commits.append(Commit(sha=sha, subject=subject, body=body))
    return commits


def parse_issue_numbers(text: str) -> Set[int]:
    nums: Set[int] = set()

    # #123
    for m in re.finditer(r'(?<!\w)#(\d{1,6})\b', text):
        nums.add(int(m.group(1)))

    # Full URL .../issues/123
    for m in re.finditer(r'/issues/(\d{1,6})\b', text):
        nums.add(int(m.group(1)))

    return nums


def commit_permalink(sha: str) -> str:
    return f'https://github.com/{REPO}/commit/{sha}'


def comment_marker_for(sha: str) -> str:
    return f'{COMMENT_MARKER_PREFIX}{sha}{COMMENT_MARKER_SUFFIX}'


def issue_already_has_marker(issue_number: int, sha: str) -> bool:
    marker = comment_marker_for(sha)
    body = run(
        [
            'gh',
            'issue',
            'view',
            str(issue_number),
            '--repo',
            REPO,
            '--json',
            'comments',
            '--jq',
            '.comments[].body',
        ],
    )
    return marker in body


def post_issue_comment(issue_number: int, commit: Commit, dry_run: bool) -> None:
    url = commit_permalink(commit.sha)
    marker = comment_marker_for(commit.sha)

    comment = (
        'Related commit found in history:\n\n'
        f'- {url}\n'
        f'  - {commit.subject}\n\n'
        f'{marker}\n'
    )

    if dry_run:
        print(f'[dry-run] would comment on #{issue_number} with {commit.sha}')
        return

    run(
        [
            'gh',
            'issue',
            'comment',
            str(issue_number),
            '--repo',
            REPO,
            '--body',
            comment,
        ],
    )
    print(f'commented on #{issue_number}: {url}')


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Find commits mentioning issues and comment commit links on issues.',
    )
    ap.add_argument(
        '--range',
        default=f'{DEFAULT_BASE_REF}..HEAD',
        help='git revision range to scan (default: origin/main..HEAD)',
    )
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument(
        '--only',
        nargs='*',
        type=int,
        default=None,
        help='Only link commits for these issue numbers',
    )
    args = ap.parse_args()

    # Ensure we can talk to GitHub and the repo exists in this clone
    run(['gh', 'auth', 'status'])
    run(['git', 'rev-parse', '--is-inside-work-tree'])

    commits = list(iter_commits(args.range))
    if not commits:
        print(f'No commits found in range: {args.range}')
        return 0

    issue_to_commits: Dict[int, List[Commit]] = {}
    for c in commits:
        mentioned = parse_issue_numbers(c.subject + '\n' + c.body)
        for n in mentioned:
            if args.only is not None and n not in args.only:
                continue
            issue_to_commits.setdefault(n, []).append(c)

    if not issue_to_commits:
        print('No issue references found in commit messages.')
        print("Tip: include '#<issue>' or full issue URL in commit subjects/bodies.")
        return 0

    for issue_number, cs in sorted(issue_to_commits.items()):
        for c in cs:
            if issue_already_has_marker(issue_number, c.sha):
                print(f'skipping #{issue_number} {c.sha} (already linked)')
                continue
            post_issue_comment(issue_number, c, args.dry_run)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
