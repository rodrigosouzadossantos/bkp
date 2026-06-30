#!/bin/bash

PROJECT_NAME="NOAA"
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

mkdir -p 01-initiation 02-planning 03-execution 04-monitoring 05-closing

# 1. Configuration File
cat <<EOF > _quarto.yml
project:
  type: book

book:
  title: "Núcleo Operacional de Análise Ambiental de Imagens Marinhas"
  author: "Rodrigo Souza dos Santos"
  date: "`date +%Y-%m-%d`"
  chapters:
    - index.qmd
    - part: "Initiation"
      chapters:
        - 01-initiation/charter.qmd
        - 01-initiation/stakeholder-register.qmd
    - part: "Planning"
      chapters:
        - 02-planning/scope-mgmt.qmd
        - 02-planning/wbs.qmd
        - 02-planning/schedule.qmd
        - 02-planning/comm-plan.qmd
    - part: "Execution"
      chapters:
        - 03-execution/status-report.qmd
    - part: "Monitoring & Control"
      chapters:
        - 04-monitoring/risk-register.qmd
        - 04-monitoring/change-log.qmd
    - part: "Closing"
      chapters:
        - 05-closing/lessons-learned.qmd

format:
  html:
    theme: cosmo
  pdf:
    documentclass: report
    toc: true
EOF

# 2. Executive Summary
cat <<EOF > index.qmd
# Executive Summary {.unnumbered}

This document contains the complete management lifecycle for **$PROJECT_NAME**.

## Project Metadata

| Item | Description |
|------|-------------|
| **Sponsor** | [Name] |
| **PM** | [Name] |
| **Status** | In Planning |

## Quick Navigation
Use the sidebar to navigate between Initiation, Planning, and Monitoring artifacts.
EOF

# 3. Initiation Artifacts
cat <<EOF > 01-initiation/charter.qmd
# Project Charter

## Project Purpose
Describe the business need and justification for this project.

## High-Level Objectives
- [ ] Objective 1 (SMART)
- [ ] Objective 2 (SMART)

## High-Level Risks
1. Budget constraints.
2. Resource availability.

## Approval
**Sponsor Signature:** ____________________
EOF

cat <<EOF > 01-initiation/stakeholder-register.qmd
# Stakeholder Register


| Name | Role | Influence | Interest | Strategy |
|------|------|-----------|----------|----------|
| John Doe | Sponsor | High | High | Manage Closely |
| Jane Smith | User | Low | High | Keep Informed |
EOF

# 4. Planning Artifacts
cat <<EOF > 02-planning/scope-mgmt.qmd
# Scope Management Plan

## Project Scope Statement
Define what is **In Scope** and **Out of Scope**.

### In Scope
- Deliverable A
- Deliverable B

### Out of Scope
- Maintenance after handover.
- Third-party licensing.
EOF

cat <<EOF > 02-planning/wbs.qmd
# Work Breakdown Structure (WBS)

The WBS decomposes the project into manageable work packages.

\`\`\`{mermaid}
graph TD
    P[Project] --> I[Initiation]
    P --> PL[Planning]
    P --> E[Execution]
    
    I --> I1[Charter]
    I --> I2[Stakeholders]
    
    PL --> PL1[Scope]
    PL --> PL2[Schedule]
    
    E --> E1[Development]
    E --> E2[Testing]
\`\`\`
EOF

cat <<EOF > 02-planning/schedule.qmd
# Project Schedule

## Milestones

| Milestone | Target Date |
|-----------|-------------|
| Planning Approval | 2024-05-01 |
| Beta Release | 2024-08-15 |
| Final Handover | 2024-12-01 |
EOF

cat <<EOF > 02-planning/comm-plan.qmd
# Communication Management Plan


| Stakeholder | Method | Frequency | Owner |
|-------------|--------|-----------|-------|
| Team | Slack/Daily Standup | Daily | PM |
| Sponsor | Email/Meeting | Bi-weekly | PM |
| Users | Newsletter | Monthly | Marketing |
EOF

# 5. Execution & Monitoring Artifacts
cat <<EOF > 03-execution/status-report.qmd
# Status Report

**Reporting Period:** [Date Range]

## Summary
- **Schedule:** On Track
- **Budget:** Under Budget
- **Resources:** Sufficient

## Accomplishments this Period
- Completed WBS.
- Finalized Stakeholder list.
EOF

cat <<EOF > 04-monitoring/risk-register.qmd
# Risk Register


| ID | Risk Description | Probability | Impact | Mitigation Strategy |
|----|------------------|-------------|--------|----------------------|
| R1 | Resource turnover | Medium | High | Cross-train team members |
| R2 | Scope creep | High | Medium | Strict change control |
EOF

cat <<EOF > 04-monitoring/change-log.qmd
# Change Log


| ID | Date | Description | Status | Impact |
|----|------|-------------|--------|--------|
| C1 | 2024-04-10 | Add new feature | Pending | +2 weeks |
EOF

# 6. Closing Artifacts
cat <<EOF > 05-closing/lessons-learned.qmd
# Lessons Learned

## What Went Well
- Use of Quarto for documentation.
- Early stakeholder engagement.

## Areas for Improvement
- Initial budget estimation was too optimistic.
EOF

echo "Done! Full PMBOK Quarto project created in '$PROJECT_NAME'."

