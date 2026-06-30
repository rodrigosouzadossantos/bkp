# Security Policy

## Reporting a Vulnerability
  If you discover a security vulnerability in this project (for example: leaking
secrets via workflow examples, unsafe GitHub Actions patterns, or configurations
that could enable privilege escalation), please report it to us immediately and
responsibly.

### How to report
  - **Preferred:** Open a **private security advisory** (GitHub: *Security* →
    *Advisories* → *New draft security advisory*), if enabled for this
    repository.
  - **Alternative:** If advisories are not available, contact the maintainers
    through an agreed internal channel (team email, ticketing system, or direct
    message).

### What to include
Please include:
  - A clear description of the issue and why it is a security risk
  - Affected file(s) and links/paths
  - Steps to reproduce (if applicable)
  - Suggested remediation, if you have one
  - Whether any secrets/tokens may have been exposed

### What to expect
  - **Acknowledgement:** within **5 business days**
  - **Triage & validation:** we will reproduce and assess impact
  - **Fix:** we will aim to patch promptly, depending on severity and complexity
  - **Disclosure:** we prefer coordinated disclosure after a fix is available


## Responsible Disclosure
  We take security vulnerabilities seriously and will work to address any issues
as quickly as possible. We ask that you do not disclose the vulnerability
publicly until we have had a chance to investigate and resolve the issue.


## Acknowledgments
  We appreciate the efforts of security researchers who help us identify and fix
vulnerabilities in our software. If you report a vulnerability to us, we will
acknowledge your contribution in our release notes and on our website, unless
you request otherwise.


## Security Updates
  We will release security updates as needed to address any vulnerabilities that
are discovered. We encourage users to keep their software up to date to ensure
that they have the latest security patches and fixes. We will also provide
information about any known vulnerabilities and how to mitigate them in our
documentation and release notes.


## Supported Versions
  This repository provides the ALM strategy for the Subsea AI area. Security
updates are provided on the default branch, which is currently `main`. We
recommend that users always use the latest version of the software to ensure
that they have the latest security patches and fixes.
  We do not provide security updates for older versions of the software, so it
is important to keep your software up to date. If you are using an older version
of the software and are concerned about security, we recommend that you upgrade
to the latest version as soon as possible.


## Security best practices for contributions
When contributing changes, please:
  - **Do not commit secrets** (tokens, passwords, private keys), even
    temporarily.
  - Avoid unsafe GitHub Actions patterns:
    - Don’t use unpinned third-party actions (pin to a full commit SHA when
      possible).
    - Minimize `GITHUB_TOKEN` permissions (use `permissions:` with least
      privilege).
    - Treat all PR content as untrusted—especially for workflows triggered by
      `pull_request_target`.
  - Prefer secure defaults in templates (least privilege, explicit permissions,
    protected environments).


## Scope

This policy applies to:
  - GitHub Actions workflow templates and recommended patterns
  - Issue/PR templates and any automation configuration
  - Documentation and scripts in this repository

  It does not cover security issues in downstream repositories that copy these
files, except where the issue originates from insecure guidance in this
repository.
