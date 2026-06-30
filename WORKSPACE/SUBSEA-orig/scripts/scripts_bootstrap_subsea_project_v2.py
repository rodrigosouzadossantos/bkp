#!/usr/bin/env python3
"""
Bootstrap Subsea GitHub Project v2 and initial atomic issues.

What it does
- Creates 10 atomic issues in the repo (idempotent via a marker in the body)
- Links them as sub-issues of parent issue #1
- Adds them to GitHub Project v2 (user project #6)
- Attempts to set Status to "Backlog" (if Status field exists and has that
  option)

Requirements
- Python 3.10+
- GitHub CLI installed and authenticated: `gh auth status`
- Token scopes: `repo`, `project` (and for some org settings: `read:project` /
  `write:project`)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

REPO = "rodrigo-santos35-prestserv_petro/subsea-alm-configurations"
PARENT_ISSUE_NUMBER = 1
PROJECT_URL = "https://github.com/users/rodrigo-santos35-prestserv_petro/projects/6"
MARKER_PREFIX = 'subsea-bootstrap:'
MARKER_SUFFIX = ''

ISSUES = [
    ("README file presence and content",
     "Ensure there is a README.md file explaining the purpose, overview, and setup of the subsea-alm-configurations repository."),
    ("LICENSE file verification",
     "Ensure there is a LICENSE.md file that defines the repository's license."),
    ("CONTRIBUTING guidelines presence",
     "Validate CONTRIBUTING.md exists to detail how contributors can participate, submit PRs, and issue reporting."),
    ("SECURITY document presence",
     "Ensure SECURITY.md exists to document security policies, reporting vulnerabilities, and contact info."),
    ("Architecture documentation file",
     "Check ARCHICTERURE.md for presence and completeness in describing repository architecture, components, and structure."),
    ("Roles documentation verification",
     "Confirm ROLES.md exists and describes the roles and responsibilities within the subsea-alm-configurations project."),
    ("Python version file check",
     "Ensure .python-version exists and specifies correct Python version for repo setup."),
    ("Project meta/config file check (pyproject.toml)",
     "Verify pyproject.toml configuration exists and is properly setup for tooling and dependencies."),
    ("Subsea domain file verification",
     "Check SUBSEA.md exists and provides domain summary, technical aims, or specification for subsea configuration context."),
    ("Documentation directory existence",
     "Verify docs/ directory is present and contains initial documentation."),
]


@dataclass(frozen=True)
class CreatedIssue:
    number: int
    url: str
    node_id: str


def run(cmd: List[str], *, input_text: Optional[str] = None) -> str:
    p = subprocess.run(
        cmd,
        input=input_text.encode("utf-8") if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed ({p.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{p.stdout.decode()}\nSTDERR:\n{p.stderr.decode()}\n"
        )
    return p.stdout.decode("utf-8").strip()


def gh_api_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    # Use -F to ensure gh passes variables correctly (avoids "invalid value null" errors)
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        cmd += ["-F", f"{k}={v}"]
    out = run(cmd)
    return json.loads(out)


def gh_api_rest(endpoint: str) -> Any:
    out = run(["gh", "api", endpoint])
    return json.loads(out) if out else None


def repo_info() -> Tuple[str, str]:
    owner, name = REPO.split("/", 1)
    return owner, name


def get_repo_node_id() -> str:
    owner, name = repo_info()
    q = """
    query($owner:String!, $name:String!){
      repository(owner:$owner, name:$name){ id }
    }
    """
    data = gh_api_graphql(q, {"owner": owner, "name": name})
    return data["data"]["repository"]["id"]


def get_parent_issue_node_id() -> str:
    owner, name = repo_info()
    q = """
    query($owner:String!, $name:String!, $number:Int!){
      repository(owner:$owner, name:$name){
        issue(number:$number){ id }
      }
    }
    """
    data = gh_api_graphql(q, {"owner": owner, "name": name, "number": PARENT_ISSUE_NUMBER})
    return data["data"]["repository"]["issue"]["id"]


def marker_for(title: str) -> str:
    digest = hashlib.sha1(title.encode('utf-8')).hexdigest()[:12]
    return f'{MARKER_PREFIX}{digest}{MARKER_SUFFIX}'


def find_existing_issue_by_marker(marker: str) -> Optional[CreatedIssue]:
    out = run(
        [
            'gh',
            'search',
            'issues',
            marker,
            '--repo',
            REPO,
            '--json',
            'number,url,id',
            '--limit',
            '1',
        ],
    )
    items = json.loads(out)
    if not items:
        return None
    item = items[0]
    return CreatedIssue(number=item['number'], url=item['url'], node_id=item['id'])


def create_issue(title: str, body: str, dry_run: bool) -> CreatedIssue:
  if dry_run:
      print(f'[dry-run] would create issue: {title}')
      return CreatedIssue(number=-1, url='(dry-run)', node_id='(dry-run)')

  # `gh issue create` does not support --json in your gh build.
  # It prints the created issue URL on stdout.
  issue_url = run(
    [
      'gh',
      'issue',
      'create',
      '--repo',
      REPO,
      '--title',
      title,
      '--body',
      body,
    ],
  ).strip()

  # Now fetch number/url/id from the created issue using `gh issue view --json`.
  issue_json = run(
    [
      'gh',
      'issue',
      'view',
      issue_url,
      '--repo',
      REPO,
      '--json',
      'number,url,id',
    ],
  )
  data = json.loads(issue_json)
  return CreatedIssue(
    number=data['number'],
    url=data['url'],
    node_id=data['id'],
  )


def ensure_issue(title: str, sentence: str, dry_run: bool) -> CreatedIssue:
    marker = marker_for(title)
    existing = find_existing_issue_by_marker(marker)
    if existing:
        print(f"exists: #{existing.number} {existing.url}")
        return existing
    body = f"{sentence}\n\n{marker}\n"
    created = create_issue(title, body, dry_run)
    print(f"created: #{created.number} {created.url}")
    return created


def add_sub_issue(parent_issue_id: str, child_issue_id: str, dry_run: bool) -> None:
    # GraphQL AddSubIssue mutation (requires sub-issues to be enabled)
    if dry_run:
        print(f"[dry-run] would link child issue to parent")
        return
    m = """
    mutation($parentId:ID!, $childId:ID!){
      addSubIssue(input:{issueId:$parentId, subIssueId:$childId}) {
        issue { id }
      }
    }
    """
    gh_api_graphql(m, {"parentId": parent_issue_id, "childId": child_issue_id})


def parse_project_number_from_url(url: str) -> int:
    # .../projects/6
    return int(url.rstrip("/").split("/")[-1])


def get_user_project_node_id_and_fields() -> Tuple[str, str, str, Dict[str, str]]:
    """
    Returns: (user_login, project_id, status_field_id, status_option_name_to_id)
    """
    project_number = parse_project_number_from_url(PROJECT_URL)
    user_login = PROJECT_URL.split("/users/")[1].split("/projects/")[0]

    q = """
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
    """
    data = gh_api_graphql(q, {"login": user_login, "number": project_number})
    proj = data["data"]["user"]["projectV2"]
    project_id = proj["id"]

    status_field_id = ""
    options_map: Dict[str, str] = {}

    for f in proj["fields"]["nodes"]:
        if f and f.get("name") == "Status":
            status_field_id = f["id"]
            for opt in f.get("options", []) or []:
                options_map[opt["name"]] = opt["id"]
            break

    return user_login, project_id, status_field_id, options_map


def add_issue_to_project(project_id: str, content_id: str, dry_run: bool) -> Optional[str]:
    if dry_run:
        print("[dry-run] would add issue to project")
        return "(dry-run-item-id)"
    m = """
    mutation($projectId:ID!, $contentId:ID!){
      addProjectV2ItemById(input:{projectId:$projectId, contentId:$contentId}) {
        item { id }
      }
    }
    """
    data = gh_api_graphql(m, {"projectId": project_id, "contentId": content_id})
    return data["data"]["addProjectV2ItemById"]["item"]["id"]


def set_project_item_status(project_id: str, item_id: str, field_id: str, option_id: str, dry_run: bool) -> None:
    if not field_id or not option_id:
        return
    if dry_run:
        print("[dry-run] would set Status=Backlog")
        return
    m = """
    mutation($projectId:ID!, $itemId:ID!, $fieldId:ID!, $optionId:String!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$projectId,
        itemId:$itemId,
        fieldId:$fieldId,
        value:{ singleSelectOptionId:$optionId }
      }) { projectV2Item { id } }
    }
    """
    gh_api_graphql(m, {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "optionId": option_id})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Do not create or mutate anything")
    args = ap.parse_args()

    # Basic checks
    run(["gh", "auth", "status"])

    parent_id = get_parent_issue_node_id()
    _, project_id, status_field_id, status_options = get_user_project_node_id_and_fields()
    backlog_option_id = status_options.get("Backlog") or status_options.get("Backlog ")

    created: List[CreatedIssue] = []
    for title, sentence in ISSUES:
        created.append(ensure_issue(title, sentence, args.dry_run))

    # Link sub-issues + add to project
    for iss in created:
        if iss.node_id.startswith("(dry-run)") or iss.number == -1:
            continue
        add_sub_issue(parent_id, iss.node_id, args.dry_run)
        item_id = add_issue_to_project(project_id, iss.node_id, args.dry_run)
        if item_id and backlog_option_id:
            set_project_item_status(project_id, item_id, status_field_id, backlog_option_id, args.dry_run)

    print("\nDone. Issues:")
    for iss in created:
        print(f"- {iss.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
