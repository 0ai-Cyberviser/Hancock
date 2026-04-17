# Contributing to Hancock

Thank you for your interest in contributing to **Hancock** by Johnny Watters
(`0ai-Cyberviser`)! 🛡️

## Code of Conduct

Be respectful. All contributions must be ethical and legal. Hancock is built for **authorized security work only**.

## How to Contribute

### Reporting Bugs
Open an issue using the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md).

### Suggesting Features
Open an issue using the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md).

### Pull Requests

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/Hancock.git`
3. **Create a branch**: `git checkout -b feat/your-feature-name`
4. **Set up dev environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env  # add your NVIDIA API key
   ```
5. **Make your changes**
6. **Test** your changes manually
7. **Commit** using conventional commits:
   ```
   feat: add new SOC triage endpoint
   fix: handle empty alert in /v1/triage
   docs: update API reference
   refactor: clean up collector logic
   ```
8. **Push** and open a Pull Request

## Ownership and Contribution Terms

This repository is maintained by Johnny Watters (`0ai-Cyberviser`) under the
project license in [LICENSE](LICENSE). Repository administration, release
decisions, and branding control remain with the maintainer.

By submitting a pull request, patch, dataset, prompt, documentation update, or
other contribution for review, you confirm that:

1. you have the legal right to submit the contribution;
2. the contribution does not knowingly infringe third-party rights; and
3. if the maintainer requests a separate written assignment, trademark
   acknowledgment, or relicensing confirmation before merge, you will either
   provide it or withdraw the contribution.

Maintainers may decline or close contributions that do not come with whatever
rights confirmation is needed for the project.

## Areas Where Help is Needed

| Area | Description |
|------|-------------|
| 🤖 **Fine-tuning data** | More pentest/SOC Q&A pairs for training datasets |
| 🔌 **Integrations** | Burp Suite extension, Splunk app, VS Code plugin |
| 📝 **Documentation** | Usage guides, tutorial blog posts |
| 🧪 **Tests** | Unit tests for collectors, formatter, API endpoints |
| 🌐 **Website** | Improvements to `docs/index.html` |

## Development Guidelines

- Python 3.10+
- Follow existing code style (no linter enforced yet, use common sense)
- Keep the agent's ethical guardrails intact — never remove authorization checks
- All training data must come from **public, legally sourced** cybersecurity knowledge bases

## Questions?

Open an issue or reach out at
[github.com/0ai-Cyberviser](https://github.com/0ai-Cyberviser).
