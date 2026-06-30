#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

REPO = 'rodrigo-santos35-prestserv_petro/subsea-alm-configurations'
DEFAULT_RECENT = 'HEAD~50..HEAD'
DEFAULT_PROJECT_URL = 'https://github.com/users/rodrigo-santos35-prestserv_petro/projects/6'

COMMENT_MARKER_PREFIX = 'commit-link:'
COMMENT_MARKER_SUFFIX = ''


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str


def run(cmd: List[str]) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        raise RuntimeError(
            f'Command failed ({p.returncode}): {" ".join(cmd)}\n'
            f'STDOUT:\n{p.stdout.decode()}\nSTDERR:\n{p.stderr.decode()}\n',
        )
    return p.stdout.decode().strip()


def gh_api_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    cmd = ['gh', 'api', 'graphql', '-f', f'query={query}']
    for key, value in variables.items():
        cmd += ['-F', f'{key}={value}']
    out = run(cmd)
    return json.loads(out)


def commit_permalink(sha: str) -> str:
    return f'https://github.com/{REPO}/commit/{sha}'


def comment_marker_for(issue_number: int, sha: str) -> str:
    # Include issue_number to allow the same commit to be linked to multiple issues.
    raw = f'{REPO}#{issue_number}@{sha}'
    digest = hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]
    return f'{COMMENT_MARKER_PREFIX}{digest}{COMMENT_MARKER_SUFFIX}'''


def iter_commits(rev_range: str) -> Iterable[Commit]:
    fmt = '%H%x1f%s%x1e'
    out = run(['git', 'log', '--no-color', f'--pretty=format:{fmt}', rev_range])
    if not out:
        return []
    records = out.split('\x1e')
    commits: List[Commit] = []
    for rec in records:
        rec = rec.strip()
        if not rec:
            continue
        sha, subject = rec.split('\x1f', 1)
        commits.append(Commit(sha=sha, subject=subject))
    return commits


def changed_files_for_commit(sha: str) -> Set[str]:
    out = run(['git', 'show', '--name-only', '--pretty=format:', sha])
    return {line.strip() for line in out.splitlines() if line.strip()}


def any_match(path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def issue_has_marker(issue_number: int, sha: str) -> bool:
    marker = comment_marker_for(issue_number, sha)
    bodies = run(
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
    return marker in bodies


def comment_issue(
    issue_number: int,
    sha: str,
    subject: str,
    files: Set[str],
    dry_run: bool,
) -> None:
    url = commit_permalink(sha)
    marker = comment_marker_for(issue_number, sha)

    files_list = '\n'.join(f'- `{f}`' for f in sorted(files))
    body = (
        'Auto-linked commit based on changed files:\n\n'
        f'- {url}\n'
        f'  - {subject}\n\n'
        'Files changed:\n'
        f'{files_list}\n\n'
        f'Marker: {marker}\n'
    )

    if dry_run:
        print(f'[dry-run] would comment on #{issue_number} with {sha}')
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
            body,
        ],
    )
    print(f'commented on #{issue_number}: {url}')


def issue_state(issue_number: int) -> str:
    out = run(
        [
            'gh',
            'issue',
            'view',
            str(issue_number),
            '--repo',
            REPO,
            '--json',
            'state',
            '--jq',
            '.state',
        ],
    )
    return out.strip().upper()


def close_issue(issue_number: int, reason: str, dry_run: bool) -> None:
    if issue_state(issue_number) == 'CLOSED':
        print(f'skipping close #{issue_number} (already closed)')
        return

    if dry_run:
        print(f'[dry-run] would close issue #{issue_number}')
        return

    run(
        [
            'gh',
            'issue',
            'close',
            str(issue_number),
            '--repo',
            REPO,
            '--comment',
            reason,
        ],
    )
    print(f'closed issue #{issue_number}')


def parse_project_number_from_url(url: str) -> int:
    return int(url.rstrip('/').split('/')[-1])


def parse_user_login_from_project_url(url: str) -> str:
    # https://github.com/users/<login>/projects/<n>
    return url.split('/users/')[1].split('/projects/')[0]


def get_project_id_and_status_field(project_url: str) -> Tuple[str, str, Dict[str, str]]:
    login = parse_user_login_from_project_url(project_url)
    number = parse_project_number_from_url(project_url)

    q = '''
    query($login:String!, $number:Int!){
      user(login:$login){
        projectV2(number:$number){
          id
          fields(first:50){
            nodes{
              ... on ProjectV2SingleSelectField {
                id
                name
                options { id name }
              }
            }
          }
        }
      }
    }
    '''
    data = gh_api_graphql(q, {'login': login, 'number': number})
    proj = data['data']['user']['projectV2']
    project_id = proj['id']

    status_field_id = ''
    options: Dict[str, str] = {}
    for field in proj['fields']['nodes']:
        if field and field.get('name') == 'Status':
            status_field_id = field['id']
            for opt in field.get('options', []) or []:
                options[opt['name']] = opt['id']
            break

    return project_id, status_field_id, options


def get_issue_node_id(issue_number: int) -> str:
    owner, name = REPO.split('/', 1)
    q = '''
    query($owner:String!, $name:String!, $number:Int!){
      repository(owner:$owner, name:$name){
        issue(number:$number){ id }
      }
    }
    '''
    data = gh_api_graphql(q, {'owner': owner, 'name': name, 'number': issue_number})
    return data['data']['repository']['issue']['id']


def find_project_item_id(project_id: str, issue_node_id: str) -> Optional[str]:
    q = '''
    query($projectId:ID!, $contentId:ID!){
      node(id:$projectId){
        ... on ProjectV2 {
          items(first:100){
            nodes{
              id
              content { ... on Issue { id } }
            }
          }
        }
      }
    }
    '''
    data = gh_api_graphql(q, {'projectId': project_id, 'contentId': issue_node_id})

    # We queried items, but GraphQL doesn't filter by contentId here.
    # So we scan the returned items to find matching issue content id.
    nodes = data['data']['node']['items']['nodes']
    for n in nodes:
        content = n.get('content')
        if content and content.get('id') == issue_node_id:
            return n.get('id')
    return None


def add_issue_to_project(project_id: str, issue_node_id: str, dry_run: bool) -> str:
    if dry_run:
        print('[dry-run] would add issue to project')
        return '(dry-run-item-id)'

    m = '''
    mutation($projectId:ID!, $contentId:ID!){
      addProjectV2ItemById(input:{projectId:$projectId, contentId:$contentId}) {
        item { id }
      }
    }
    '''
    data = gh_api_graphql(m, {'projectId': project_id, 'contentId': issue_node_id})
    return data['data']['addProjectV2ItemById']['item']['id']


def set_project_item_status(
    project_id: str,
    item_id: str,
    status_field_id: str,
    status_option_id: str,
    dry_run: bool,
) -> None:
    if dry_run:
        print('[dry-run] would set project item Status=Done')
        return

    m = '''
    mutation($projectId:ID!, $itemId:ID!, $fieldId:ID!, $optionId:String!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$projectId,
        itemId:$itemId,
        fieldId:$fieldId,
        value:{ singleSelectOptionId:$optionId }
      }) { projectV2Item { id } }
    }
    '''
    gh_api_graphql(
        m,
        {
            'projectId': project_id,
            'itemId': item_id,
            'fieldId': status_field_id,
            'optionId': status_option_id,
        },
    )


def default_issue_file_map() -> Dict[str, List[str]]:
    return {
        'readme': ['README.md'],
        'license': ['LICENSE', 'LICENSE.*', 'LICENSE.md'],
        'contributing': ['CONTRIBUTING.md', '.github/CONTRIBUTING.md'],
        'security': ['SECURITY.md', '.github/SECURITY.md'],
        'architecture': [
            'ARCHICTERURE.md',
            'ARCHITECTURE.md',
            'docs/architecture*',
            'docs/**/architecture*',
        ],
        'roles': ['ROLES.md', 'docs/roles*', 'docs/**/roles*'],
        'python_version': ['.python-version'],
        'pyproject': ['pyproject.toml'],
        'subsea': ['SUBSEA.md', 'docs/subsea*', 'docs/**/subsea*'],
        'docs_dir': ['docs/**'],
    }


# Fill these with your real issue numbers once.
ISSUE_NUMBERS: Dict[str, int] = {
    # 'readme': 2,
    # 'license': 3,
    # 'contributing': 4,
    # 'security': 5,
    # 'architecture': 6,
    # 'roles': 7,
    # 'python_version': 8,
    # 'pyproject': 9,
    # 'subsea': 10,
    # 'docs_dir': 11,
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description='Auto-link commits to issues based on changed files.',
    )
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument(
        '--range',
        dest='rev_range',
        default=None,
        help=f'Git revision range to scan (default: {DEFAULT_RECENT})',
    )
    ap.add_argument('--all', action='store_true', help='Scan all commits (HEAD)')
    ap.add_argument('--close', action='store_true', help='Close matched issues')
    ap.add_argument(
        '--move-done',
        action='store_true',
        help='Move matched issues in Project v2 to Status=Done',
    )
    ap.add_argument(
        '--project-url',
        default=DEFAULT_PROJECT_URL,
        help='Project v2 URL (user project)',
    )
    args = ap.parse_args()

    run(['gh', 'auth', 'status'])
    run(['git', 'rev-parse', '--is-inside-work-tree'])

    if not ISSUE_NUMBERS:
        print('ISSUE_NUMBERS is empty. Fill it with your issue numbers and re-run.')
        return 2

    rev_range = 'HEAD' if args.all else (args.rev_range or DEFAULT_RECENT)
    commits = list(iter_commits(rev_range))
    if not commits:
        print(f'No commits found in range: {rev_range}')
        return 0

    file_map = default_issue_file_map()
    unknown = sorted(set(ISSUE_NUMBERS.keys()) - set(file_map.keys()))
    if unknown:
        raise RuntimeError(f'ISSUE_NUMBERS has unknown keys: {unknown}')

    project_id = ''
    status_field_id = ''
    status_done_option_id = ''
    if args.move_done:
        project_id, status_field_id, options = get_project_id_and_status_field(
            args.project_url,
        )
        status_done_option_id = options.get('Done', '')
        if not status_field_id or not status_done_option_id:
            raise RuntimeError(
                "Project Status field or 'Done' option not found. "
                "Check your project setup.",
            )

    # Track which issues we touched in this run (so we close/move once per issue).
    touched_issues: Set[int] = set()

    for c in commits:
        files = changed_files_for_commit(c.sha)
        if not files:
            continue

        for key, issue_number in ISSUE_NUMBERS.items():
            patterns = file_map[key]
            matched = {f for f in files if any_match(f, patterns)}
            if not matched:
                continue

            if not issue_has_marker(issue_number, c.sha):
                comment_issue(issue_number, c.sha, c.subject, matched, args.dry_run)

            touched_issues.add(issue_number)

    # Close and/or move-to-done once per touched issue.
    for issue_number in sorted(touched_issues):
        if args.move_done:
            issue_node_id = get_issue_node_id(issue_number)
            item_id = find_project_item_id(project_id, issue_node_id)
            if not item_id:
                item_id = add_issue_to_project(project_id, issue_node_id, args.dry_run)
            set_project_item_status(
                project_id,
                item_id,
                status_field_id,
                status_done_option_id,
                args.dry_run,
            )
            print(f'moved issue #{issue_number} to Done in project')

        if args.close:
            close_issue(
                issue_number,
                reason='Auto-closed after detecting commit(s) touching related files.',
                dry_run=args.dry_run,
            )

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
