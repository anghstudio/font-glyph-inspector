# Contributing

Thanks for your interest in improving Font Glyph Inspector!

## Before you start

- Open an issue for substantial changes so the approach can be discussed first.
- Keep pull requests focused and explain the user-facing impact.
- Do not commit commercial fonts, customer fonts, or font files unless you have permission to redistribute them.
- Include tests or clear reproduction steps for bug fixes.

## Development setup

Follow the local setup instructions in [README.md](README.md). Run the API and frontend in separate terminals.

## Pull request checklist

- [ ] The change has a clear description and rationale.
- [ ] Existing behavior has been preserved where practical.
- [ ] New behavior has tests or reproducible manual test steps.
- [ ] Documentation has been updated where needed.
- [ ] No private fonts, secrets, API keys, or generated build folders are included.

## Code style

Prefer small, readable functions. Keep font parsing and validation in the Python backend; keep presentation and interaction in the React frontend. Be explicit when a font table or lookup type is only partially decoded.
