# Contributing to this repository is welcome and encouraged! If you have
suggestions for improvements or additional configurations, please follow the
guidelines below to submit your contributions.

## How to Contribute
1. Fork the repository to your GitHub account.
2. Clone the forked repository to your local machine.
3. Create a new branch for your contribution:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Commit Guidelines
When making commits, please follow these guidelines to ensure that your
contributions are clear and consistent:
- Use the present tense in commit messages (e.g., "Add new feature" instead of
  "Added new feature").
- Keep commit messages concise and descriptive.
- Use the following format for commit messages:
  ```<type>(<scope>): <subject> <body> <footer>```
  Where:
  - `<type>`: The type of change (e.g., feat, fix, docs, style, refactor, test,
    chore).
  - `<scope>`: The scope of the change (e.g., OKR, GitHub Actions, project
    board).
  - `<subject>`: A brief description of the change.
  - `<body>`: A more detailed description of the change (optional).
  - `<footer>`: Any relevant references or issues (optional).

Commits should be atomic, meaning that each commit should represent a single
logical change. This makes it easier to review and understand the history of
changes in the repository.

The linter will check for the presence of a valid commit message format and will
reject any commits that do not adhere to the specified guidelines. Please ensure
that your commit messages follow the format outlined above to avoid any issues
with your contributions.

All commits must be signed off with gpg to verify the authenticity of the
contributor. You can sign off your commits using the following command:
  ```bash
  git commit -s -m "Your commit message"
  ```

In tools that support it, you can also configure your Git client to
automatically sign off all commits. For example, you can add the following
configuration to your Git settings:
  ```bash
  git config --global commit.gpgSign true
  ```

One script is provided to help with gpg/ssh and git configuration:
  ```bash
  ./scripts/git-commit-signing-ssh.sh
  ```

## Pull Request Guidelines When submitting a pull request, please ensure that:
- Your branch is up to date with the main branch.
- Your pull request includes a clear description of the changes you have made.
- You have added tests for any new features or bug fixes.
- You have followed the commit guidelines outlined above.


