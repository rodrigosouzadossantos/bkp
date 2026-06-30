/**
 * fetch-okr.js
 * Extrai Issues e PRs de múltiplos repositórios e gera okr-dashboard.json
 */

import fetch from "node-fetch";
import fs from "fs";

// Configuração dos repositórios a serem monitorados
const repos = [
  { owner: "minha-org", repo: "subsea-ia" },
  { owner: "minha-org", repo: "subsea-utils" }
];

const token = process.env.GH_TOKEN;
const headers = {
  "Authorization": `Bearer ${token}`,
  "Accept": "application/vnd.github+json"
};

async function fetchIssues(repo) {
  const url = `https://api.github.com/repos/${repo.owner}/${repo.repo}/issues?state=all&per_page=100`;
  const response = await fetch(url, { headers });
  const data = await response.json();
  return data.map(issue => ({
    repo: repo.repo,
    number: issue.number,
    title: issue.title,
    labels: issue.labels.map(l => l.name),
    state: issue.state,
    assignees: issue.assignees.map(a => a.login),
    body: issue.body,
    url: issue.html_url
  }));
}

async function main() {
  let allIssues = [];
  for (const repo of repos) {
    const issues = await fetchIssues(repo);
    allIssues = allIssues.concat(issues);
  }

  // Gera JSON final
  fs.writeFileSync(
    "dashboard/data/okr-dashboard.json",
    JSON.stringify(allIssues, null, 2)
  );
  console.log(`Dashboard atualizado: ${allIssues.length} issues processadas.`);
}

main().catch(console.error);
