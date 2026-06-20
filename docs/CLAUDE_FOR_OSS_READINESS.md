# Claude for Open Source readiness tracker

This tracker separates official program requirements from internal adoption goals.

Last verified: **2026-06-19**.

Official sources:

- [Claude for Open Source application](https://claude.com/contact-sales/claude-for-oss)
- [Claude for Open Source terms](https://www.anthropic.com/claude-for-oss-terms)

## Current decision

Current readiness: **not eligible for the Maintainer Track; ecosystem-impact evidence is not yet sufficient**.

The repository is public, actively maintained, licensed under Apache-2.0, tested in CI, and published to PyPI. It does not currently meet the Maintainer Track scale threshold, and there is no verified downstream-dependency or external-adoption evidence strong enough to support an Ecosystem Impact Track claim.

## Official program gate

Applications are reviewed on a rolling basis. The current terms state that the application period expires on **2026-06-30**, unless Anthropic extends it, and that the program is capped at up to 10,000 approved recipients.

### Maintainer Track

All of the following are required:

- primary maintainer or core team member of a public GitHub repository;
- repository has at least 5,000 GitHub stars **or** at least 1 million monthly NPM downloads;
- write or admin access to the repository; and
- commits, issue triage, PR reviews, or releases within the previous three months.

This Python package cannot substitute PyPI downloads for the official NPM threshold.

### Ecosystem Impact Track

Applicants below the Maintainer Track thresholds may apply at Anthropic's discretion when a project is meaningfully depended on by the open-source ecosystem. The official factors include:

- downstream dependents;
- breadth of usage;
- criticality of the project's function; and
- the applicant's maintenance role.

Claims for this track must be backed by public, verifiable evidence. Stars, downloads, issues, testimonials, or dependents must not be purchased, exchanged, automated, or otherwise inflated.

## Verified repository evidence

Snapshot captured on 2026-06-19:

| Evidence | Current value | Interpretation |
|---|---:|---|
| Public GitHub repository | Yes | Required base condition met |
| License | Apache-2.0 | Open-source license present |
| GitHub stars | 0 | Maintainer Track threshold not met |
| Forks | 0 | No external fork evidence yet |
| External issues | 0 | Existing issues were opened by the repository owner |
| External PRs | 0 | No external contribution evidence yet |
| GitHub releases | 9 | Latest release is `v0.6.0` |
| PyPI version | `0.6.0` | Aligned with the latest GitHub release |
| PyPI recent downloads | 333 | Raw download count; not proof of unique users or downstream dependence |
| Latest CI on `main` | Passing | Python 3.11-3.13 tests and package build passed |
| Recent maintainer activity | Yes | Commits and releases occurred within three months |

## Application evidence still required

- [ ] Verifiable downstream projects or dependents.
- [ ] External user reports that identify a real workflow and outcome.
- [ ] External issues or pull requests.
- [x] Repository-hosted reproducible consumer tutorial.
- [ ] Independent technical posts, tutorials, or mentions outside this repository.
- [ ] A concise explanation of ecosystem significance supported by links.
- [ ] Confirmation that the individual applicant meets the general eligibility requirements in the official terms.

## Repository work that supports the goal

- [x] Public GitHub repository.
- [x] Apache-2.0 license.
- [x] CI workflow for Python 3.11-3.13.
- [x] PyPI production publishing.
- [x] GitHub release aligned with the latest PyPI version.
- [x] At least five GitHub releases.
- [x] Multi-symbol universe mode.
- [x] Artifact validation and quality scoring.
- [x] Read-only local artifact API, static dashboard frontend, and static report.
- [x] Issue forms and pull request template.
- [x] Windows quickstart and artifact-contract documentation.
- [x] Offline downstream consumer example with a CI-tested synthetic fixture.
- [x] Repository-hosted dashboard screenshot rendered from the synthetic fixture.
- [x] Repository-hosted technical guide for coverage, dispersion, and public book concentration.
- [x] Structured GitHub Issue Form for downstream-use evidence intake.
- [x] Manual GitHub Pages workflow for a reproducible synthetic artifact report.
- [ ] First verified external user or downstream project.
- [ ] First external issue.
- [ ] First external pull request.
- [ ] Independent public technical post or tutorial outside this repository.

## Evidence collection rules

For each external use case, record:

1. a public URL or an explicit permission-to-quote statement;
2. the user or project and the concrete workflow;
3. the package version used;
4. the artifact or feature used; and
5. the observed limitation or value without trading-performance claims.

Do not describe raw package downloads as users, organizations, dependents, or production deployments.

## Project position

`crypto-composite-market-data` provides reproducible public crypto market-data artifacts across Binance, OKX, and Bybit. It helps developers and researchers inspect venue coverage, price dispersion, orderbook quality, and multi-symbol data health before consuming public market data downstream.

The project explicitly avoids trading signals, order execution, financial advice, private orderflow claims, market-maker intent claims, and profitability or statistical-edge claims.
