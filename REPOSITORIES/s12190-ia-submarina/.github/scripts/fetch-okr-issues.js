const { request, gql } = require('graphql-request');
const fs = require('fs');

const token = process.env.GITHUB_TOKEN;
const endpoint = 'https://api.github.com/graphql';

// Lista de repositórios no formato { owner, name }
const repos = [
  { owner: "petrobrasbr", name: "s12190-ambiental" },
  { owner: "petrobrasbr", name: "s12190-descomissionamento" },
  { owner: "petrobrasbr", name: "s12190-integridade" },
  { owner: "petrobrasbr", name: "s12190-limpeza-hub" }
];

const query = gql`
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    issues(first: 100, labels: ["okr"]) {
      nodes {
        number
        title
        body
        state
        labels(first:10){nodes{name}}
        assignees(first:5){nodes{login}}
      }
    }
  }
}`;

const headers = {
  Authorization: `Bearer ${token}`
};

async function fetchAll() {
  const allData = [];

  for (const repo of repos) {
    const variables = { owner: repo.owner, name: repo.name };
    try {
      const data = await request(endpoint, query, variables, headers);
      const issues = data.repository.issues.nodes.map(issue => ({
        repo: data.repository.name,
        number: issue.number,
        title: issue.title,
        state: issue.state,
        labels: issue.labels.nodes.map(l => l.name),
        assignees: issue.assignees.nodes.map(a => a.login),
        body: issue.body
      }));
      allData.push(...issues);
    } catch (error) {
      console.error(`Erro no repo ${repo.owner}/${repo.name}:`, error);
    }
  }

  fs.writeFileSync(
    'dashboard/data/okr-issues-dashboard.json',
    JSON.stringify(allData, null, 2)
  );
  console.log("Dashboard JSON consolidado criado: okr-issues-dashboard.json");
}

fetchAll();
