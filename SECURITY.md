# Security Policy

## Supported Versions

AuraSaaS is currently an MVP demo. Security fixes target the latest `main` branch.

## Reporting a Vulnerability

Please do not open public issues for sensitive vulnerabilities. Send a private report to the project maintainer with:

- affected component and version/commit
- reproduction steps
- impact assessment
- suggested fix, if available

## Demo Safety Notes

- Do not commit real API keys. Use `.env` locally and `.env.example` for templates.
- The default JWT secret is for local demo only.
- Marketing execution tools are mock/simulated by default.
- Review all generated campaigns before connecting real outbound channels.
