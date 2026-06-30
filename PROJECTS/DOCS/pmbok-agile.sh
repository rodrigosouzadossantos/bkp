#!/bin/bash

# Project Name
PROJECT_NAME="NOAA"
PROJECT_DIR="NOAA"

# Create main project directory
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Create subdirectory structure
mkdir -p 01_strategy_okrs
mkdir -p 02_initiating_pmbok
mkdir -p 03_planning_scope
mkdir -p 04_agile_execution/sprint_reports
mkdir -p 05_monitoring_control
mkdir -p assets/images
mkdir -p {location,scripts,templates}

# _i18n.yml
cat <<EOF > location/en.yml
# General Headers
#
nav_dashboard: "Dashboard"

section_strategy: "Strategy & Governance"
section_initiating: "Initiating (PMBOK)"
section_planning: "Planning & Scope"
section_execution: "Execution"
section_control: "Control"

i18n:

  dashboard_title: "Project Master Dashboard"
  charter_title: "Project Charter"
  wbs_title: "Work Breakdown Structure (WBS)"
  risk_label: "Risk Level"
  author_label: "Lead Specialist"

  # Strategy & Governance
  okr_label: "OKR"
  vsm_label: "Value Stream Mapping"

  # Initiating
  business_case: "Business Case"
  project_charter: "Project Charter"
  stakeholder_register: "Stakeholder Register"

  # Planning & Scope
  requirements_doc: "Requirements Documentation"
  wbs_label: "Work Breakdown Structure (WBS)"
  wbs_dictionary: "WBS Dictionary"

  # Execution
  product_backlog: "Product Backlog"
  product_roadmap: "Product Roadmap"

  # Control
  risk_register: "Risk Register"
  change_log: "Change Log"

EOF


cat <<EOF > location/pt.yml
# General Headers
nav_dashboard: "Painel"

dashboard_title: "Painel Mestre do Projeto"
section_strategy: "Estratégia & Governança"
section_initiating: "Iniciação (PMBOK)"
section_planning: "Planejamento & Escopo"
section_execution: "Execução"
section_control: "Controle"

i18n:

  charter_title: "Termo de Abertura (TAP)"
  wbs_title: "Estrutura Analítica do Projeto (EAP)"
  risk_label: "Nível de Risco"
  author_label: "Especialista Responsável"

  # Strategy & Governance
  okr_label: "OKR"
  vsm_label: "Mapeamento do Fluxo de Valor"

  # Initiating
  business_case: "Caso de Negócio"
  project_charter: "Termo de Abertura do Projeto (TAP)"
  stakeholder_register: "Registro de Partes Interessadas"

  # Planning & Scope
  requirements_doc: "Documentação de Requisitos"
  wbs_label: "Estrutura Analítica do Projeto (EAP)"
  wbs_dictionary: "Dicionário da EAP"

  # Execution
  product_backlog: "Backlog do Produto"
  product_roadmap: "Roadmap do Produto"

  # Control
  risk_register: "Registro de Riscos"
  change_log: "Registro de Mudanças"

EOF

# --- 1. GLOBAL CONFIGURATION ---
cat <<EOF > _quarto.yml
project:
  title: "${PROJECT_NAME}"

metadata:
  project-name: "${PROJECT_NAME}"
  author-name: "Rodrigo Souza dos Santos"

format:
  html:
    theme: cosmo
    toc: true
    code-fold: true
    css: styles.css
    html-math-method: mathjax
    bread-crumbs: false
  pdf:
    documentclass: report
    #keep-tex: true
    include-in-header:
      - templates/header.tex
    template-partials:
      - templates/before-body.tex
EOF

cat <<EOF > _quarto-en.yml
lang: en

metadata-files:
  - location/en.yml
EOF

cat <<EOF > _quarto-pt.yml
lang: pt

metadata-files:
  - location/pt.yml
EOF

cat <<EOF > _quarto-book.yml
project:
  type: book

book:
  title: "${PROJECT_NAME}"
  author: "Rodrigo Souza dos Santos"
  date: "$(date +%Y-%m-%d)"
  chapters:
    - index.qmd
    - part: "{{< meta section_strategy >}}"
      chapters:
        - 01_strategy_okrs/okr_dashboard.qmd
        - 01_strategy_okrs/value_stream.qmd
    - part: "{{< meta section_initiating >}}"
      chapters:
        - 02_initiating_pmbok/business_case.qmd
        - 02_initiating_pmbok/project_charter.qmd
        - 02_initiating_pmbok/stakeholder_reg.qmd
    - part: "{{< meta section_planning >}}"
      chapters:
        - 03_planning_scope/requirements.qmd
        - 03_planning_scope/wbs.qmd
        - 03_planning_scope/wbs_dictionary.qmd
    - part: "{{< meta section_execution >}}"
      chapters:
        - 04_agile_execution/product_backlog.qmd
        - 04_agile_execution/roadmap.qmd
    - part: "{{< meta section_control >}}"
      chapters:
        - 05_monitoring_control/risk_register.qmd
        - 05_monitoring_control/change_log.qmd

EOF

cat <<EOF > _quarto-web.yml
project:
  type: website

website:
  page-footer:
    left: "Copyright 2026, Petrobras - Submarina".
    right:.
      - icon: github
        href: https://github.com/orgs/petrobrasbr/projects/293
  sidebar:
    style: "floating"
    contents:
      - href: index.qmd
        text: "{{< meta nav_dashboard >}}"
      - section: "{{< meta section_strategy >}}"
        contents:
          - 01_strategy_okrs/okr_dashboard.qmd
          - 01_strategy_okrs/value_stream.qmd
      - section: "{{< meta section_initiating >}}"
        contents:
          - 02_initiating_pmbok/business_case.qmd
          - 02_initiating_pmbok/project_charter.qmd
          - 02_initiating_pmbok/stakeholder_reg.qmd
      - section: "{{< meta section_planning >}}"
        contents:
          - 03_planning_scope/requirements.qmd
          - 03_planning_scope/wbs.qmd
          - 03_planning_scope/wbs_dictionary.qmd
      - section: "{{< meta section_execution >}}"
        contents:
          - 04_agile_execution/product_backlog.qmd
          - 04_agile_execution/roadmap.qmd
      - section: "{{< meta section_control >}}"
        contents:
          - 05_monitoring_control/risk_register.qmd
          - 05_monitoring_control/change_log.qmd

EOF

# --- 2. INDEX / DASHBOARD ---
cat <<EOF > index.qmd
# Project Master Dashboard

Welcome to the governance portal for **{{< meta project-name >}}**. This site
serves as the "Single Source of Truth" for PMBOK artifacts and Agile execution.

### Project Identity
| Attribute | Value |
| :--- | :--- |
| **Project Name** | {{< meta project-name >}} |
| **Lead Specialist** | {{< meta author-name >}} |
| **Current Phase** | [Planning]{.status-badge} |
| **Last Audit** | `$(date +%Y-%m-%d)` |

---

### Artifact Status
Navigate through the sidebar to access the required PMBOK and Agile documents.

::: {.ProjectBox title="Latest Milestone"}
The **Project Charter** has been formally authorized. We are currently
decomposing the **WBS** into the **Product Backlog** for Sprint 01.
:::


EOF

# Create CSS for HTML branding
cat <<EOF > styles.css
/* Custom Header for the Web Dashboard */
body::before {
    content: "Rodrigo Souza dos Santos | AI Project Governance";
    display: block;
    text-align: right;
    padding: 10px 20px;
    background: #f8f9fa;
    font-size: 0.8em;
    color: #666;
    border-bottom: 1px solid #dee2e6;
}

/* Style for the "Status Badges" so they look like the LaTeX version */
.status-badge {
    display: inline-block;
    padding: 5px 12px;
    background-color: #0066cc;
    color: white;
    border-radius: 4px;
    font-weight: bold;
    font-size: 0.8em;
}

/* Match the LaTeX ProjectBox in HTML */
.ProjectBox {
    border: 1px solid #003366;
    background-color: #f8f9fa;
    border-radius: 4px;
    margin: 1em 0;
}

.ProjectBox .code-copy-button {
    display: none; /* Hide code copy on these boxes if used as containers */
}

.ProjectBox::before {
    content: attr(title); /* If you use a title attribute */
    display: block;
    background: #003366;
    color: white;
    padding: 5px 10px;
    font-weight: bold;
}
EOF

# --- 3. STRATEGY & OKRs ---
cat <<EOF > 01_strategy_okrs/okr_dashboard.qmd
# OKR {{< meta nav_dashboard >}} {}

**Objective:** Establish the industry-leading CV engine for industrial safety.

| Key Result | Target | Current | Status |
| :--- | :--- | :--- | :--- |
| KR1: Latency per frame | < 30ms | 45ms | 🟡 |
| KR2: Test Coverage | > 90% | 82% | 🟢 |
| KR3: Model Accuracy (mAP) | > 0.95 | 0.89 | 🟡 |

Last updated: \$(date +%Y-%m-%d)
EOF

cat <<EOF > 01_strategy_okrs/value_stream.qmd
# {{< i18n vsm_label >}} {}

This document maps our technical tasks to business value.

1. **Ingestion (Kafka/Redis):** Enables real-time responsiveness.
2. **Preprocessing:** Reduces noise, increasing safety accuracy.
3. **Inference (PyTorch/TF):** The core value-add.
EOF

# --- 4. INITIATING (PMBOK) ---
cat <<EOF > 02_initiating_pmbok/business_case.qmd
# {{< i18n business_case >}} {}

### Strategic Alignment
Current systems suffer from data leakage and high latency. This package utilizes
**Natural Language Processing** for data validation and optimized **Computer
Vision** pipelines to mitigate these risks.

### ROI Estimate
Expected 25% reduction in compute costs through optimized ETL pipelines using
Redis Streams.
EOF

cat <<EOF > 02_initiating_pmbok/project_charter.qmd
# {{< i18n project_charter >}} {}

**Project Name:** CV-Engine-Alpha  
**Project Manager:** Rodrigo Souza dos Santos  
**Sponsor:** Tech Operations Dept.

### High-Level Requirements
- Real-time processing via Kafka.
- Support for Grad-CAM visualizations.
- Modular architecture (PyTorch and TensorFlow).

### Authority
The PM is authorized to allocate resources from the AI Research squad.
EOF

cat <<EOF > 02_initiating_pmbok/stakeholder_reg.qmd
# {{< i18n stakeholder_register >}} {}

| Name | Role | Influence | Interest |
| :--- | :--- | :--- | :--- |
| Tech Lead | Consultant | High | High |
| DevOps Team | Supporting | Med | High |
| End Client | Beneficiary | High | High |
EOF

# --- 5. PLANNING & SCOPE ---
cat <<EOF > 03_planning_scope/requirements.qmd
# {{< i18n requirements_doc >}} {}

### Functional Requirements
1. The system shall support asynchronous inference.
2. The system shall integrate with Redis Streams for real-time ETL.

### Non-Functional Requirements
1. Latency must be deterministic.
2. Model weight loading must happen in < 5 seconds.
EOF

cat <<EOF > 03_planning_scope/wbs.qmd
# {{< i18n wbs_label >}} {}



\`\`\`{mermaid}
graph TD
    Root[CV Engine] --> Ingest[Data Ingestion]
    Root --> Core[Model Core]
    Root --> Ops[Deployment/Mlopps]
    
    Ingest --> Kafka[Kafka Connect]
    Ingest --> Redis[Redis Streams]
    
    Core --> Optim[Quantization]
    Core --> Viz[Grad-CAM Module]
\`\`\`
EOF

cat <<EOF > 03_planning_scope/wbs_dictionary.qmd
# {{< i18n wbs_dictionary >}} {}

### WP 1.1: Kafka Connect
- **Owner:** Data Engineer
- **Description:** Implement the consumer group logic for raw image ingestion.
- **Acceptance Criteria:** Successfully consume 500 images/sec.
EOF

# --- 6. AGILE EXECUTION ---
cat <<EOF > 04_agile_execution/product_backlog.qmd
# {{< i18n product_backlog >}} {}

- [ ] **Epic:** Real-time Pipeline Stabilization
    - [ ] Story: As a dev, I need a Redis sink for processed metadata.
- [ ] **Epic:** Explainability Features
    - [ ] Story: As a user, I want heatmaps on detection failures.
EOF

cat <<EOF > 04_agile_execution/roadmap.qmd
# {{< i18n product_roadmap >}} {}

- **Q1:** Core Engine & Kafka Integration.
- **Q2:** Optimization for Edge Devices (Quantization).
- **Q3:** Advanced Visualization and NLP-based filtering.
EOF

# --- 7. MONITORING & CONTROL ---
cat <<EOF > 05_monitoring_control/risk_register.qmd
# {{< i18n risk_register >}} {}

| Risk ID | Description | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| R-001 | Data Leakage | Low | Critical | NLP-based PII filtering |
| R-002 | Inference Lag | Med | High | TensorRT optimization |
EOF

cat <<EOF > 05_monitoring_control/change_log.qmd
# {{< i18n change_log >}} {}

| Date | Change | Approved By | Status |
| :--- | :--- | :--- | :--- |
| 2026-03-23 | Initial Baseline | Rodrigo | Approved |
EOF

cat <<EOF > templates/header.tex
\usepackage{fancyhdr}
\usepackage{titlesec}

\usepackage{amsmath}
\usepackage{bm} % For bold math symbols in CV formulas
\usepackage{xcolor} % For "Risk" or "Warning" boxes in PMBOK
\usepackage{tcolorbox} % For styled boxes around requirements or risks

\pagestyle{fancy}
\fancyhf{}

% This removes the "Chapter #" prefix and just leaves the title, similar to the web version
\titleformat{\chapter}[hang]{\huge\bfseries}{}{0pt}{}

% Define a custom color for "AI Specialist" brand
\definecolor{aibrow}{RGB}{0, 102, 204}

% Custom command for a "Project Status" badge
\newcommand{\statusbadge}[1]{%
    % \begin{tcolorbox}[colback=aibrow!20,colframe=aibrow!80!black,title=Status]
    \begin{tcolorbox}[colback=aibrow!5,colframe=aibrow,width=3cm,arc=1mm, auto outer arc]
      \centering \small \textbf{#1}
    \end{tcolorbox}
}

\newenvironment{ProjectBox}[1]
{\begin{tcolorbox}[colback=gray!5,colframe=blue!50!black,title=#1]}
{\end{tcolorbox}}

\rhead{\theAuthor}
\lhead{\theProjectName}
\chead{\textbf{\thePageTitle}}
%\chead{\leftmark}
\cfoot{\thepage}

% Custom styling for requirements
\newenvironment{requirement}
{\begin{tcolorbox}[colback=gray!10,colframe=black,title=Requirement]}
{\end{tcolorbox}}
EOF

cat <<EOF > templates/before-body.tex
\newcommand{\theProjectName}{\$project-name\$}
\newcommand{\theAuthor}{\$author-name\$}
\newcommand{\thePageTitle}{\$title\$}
EOF

cat <<'EOF' > Makefile
# vim: ft=makefile noet ts=4 sw=4 :
# Makefile for building the Project

.DEFAULT_GOAL := help
.PHONY: help all en-web pt-web en-book pt-book clean build

help:
	@echo "AI Project Governance - Build System"
	@echo "------------------------------------"
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  en-web    : Build English Website"
	@echo "  pt-web    : Build Portuguese Website"
	@echo "  en-book   : Build English Book (PDF/HTML)"
	@echo "  pt-book   : Build Portuguese Book (PDF/HTML)"
	@echo "  all       : Build all 4 versions"
	@echo "  clean     : Remove build artifacts"

all: en-web pt-web en-book pt-book

en-web:
	quarto render --profile en,web --output-dir _site/en/web

pt-web:
	quarto render --profile pt,web --output-dir _site/pt/web

en-book:
	quarto render --profile en,book --output-dir _site/en/book

pt-book:
	quarto render --profile pt,book --output-dir _site/pt/book

clean:
	quarto clean

EOF
#vim -c "set noet" -c "%retab!" -c "wq" Makefile

echo "Done! Structure for '${PROJECT_NAME}' created with templates."
echo "To view: cd $PROJECT_DIR && quarto preview"
