# Hancock in the CyberViser AI ecosystem

Hancock is the flagship cybersecurity agent inside the CyberViser / 0AI project family.

## Public links

| Resource | URL | Purpose |
|---|---|---|
| CyberViser AI hub | https://cyberviserai.com/ | Central public map for all CyberViser / 0AI projects |
| Hancock docs/demo | https://cyberviser.github.io/Hancock/ | Public Hancock project page |
| Hancock source | https://github.com/0ai-Cyberviser/Hancock | Agent source, API, collectors, docs, fuzz targets |
| 0AI project page | https://0ai-cyberviser.github.io/0ai/ | 0AI public project page |
| PeachFuzz | https://github.com/0ai-Cyberviser/peachfuzz | Fuzzing, crash minimization, regression reproducers |
| PeachTree | https://github.com/0ai-Cyberviser/PeachTree | Recursive dataset engine for safe JSONL datasets |
| MrClean | https://github.com/0ai-Cyberviser/mrclean | GitHub PR/repo maintenance automation agent |

## How the projects connect

```text
CyberViser AI hub
  ├── Hancock      → cybersecurity LLM agent and API
  ├── PeachFuzz    → fuzzing and regression reproducers
  ├── PeachTree    → dataset lineage, export, and training handoff
  ├── MrClean      → GitHub PR/repo maintenance and policy checks
  └── 0AI          → broader project coordination and public docs
```

## Free-first development path

The current public build strategy is GitHub-first:

1. Host public pages with GitHub Pages.
2. Use GitHub Actions for tests, linting, docs, and Pages deploys.
3. Use local machines and free CI before paid GPU/cloud work.
4. Keep all repos linked through `cyberviserai.com`.
5. Land improvements through reviewable PRs.

## Hancock role

Hancock should remain the main user-facing security agent. Other CyberViser projects support it:

- **PeachTree** builds traceable datasets from reviewed project artifacts.
- **PeachFuzz** turns fuzzing findings into safe regression and dataset material.
- **MrClean** keeps the GitHub estate clean, connected, and policy-compliant.
- **CyberViser-ViserHub** provides the public domain and repo atlas.
