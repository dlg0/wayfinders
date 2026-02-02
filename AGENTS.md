# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## What We're Building

**Wayfinders** is a production tool for creating a stylized, low-frame kids adventure series using rigged cutouts (Option B).

See `README.md` for "Definition of Done" and `docs/ARCHITECTURE.md` for system design.

## Quick Start (New Contributors)

```bash
# Set up environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,placeholders]"

# Run the example episode through the pipeline
uv run wf validate episodes/s01e01_map_forgot_roads/episode.yaml --allow-missing-assets
uv run wf placeholders episodes/s01e01_map_forgot_roads/episode.yaml
uv run wf plan episodes/s01e01_map_forgot_roads/episode.yaml
uv run wf build-timeline episodes/s01e01_map_forgot_roads/episode.yaml
uv run wf build-animatic episodes/s01e01_map_forgot_roads/episode.yaml
```

Outputs go to `episodes/s01e01_map_forgot_roads/logs/`.

## Key Concepts

- **Canon YAML** (`show/canon/*.yaml`) – Master reference data: characters, environments, reusable assets
- **Episode YAML** – Declarative episode script + metadata
- **Shotlist YAML** – Shot-by-shot rendering instructions
- **Timeline IR** – Intermediate representation (JSON) used by renderers
- **Provenance** – Metadata sidecars tracking asset generation (sources, cache keys, provider calls)

See `docs/CLI_SPEC.md` for command contracts and `docs/ARCHITECTURE.md` for build system design.

## Development Workflow

### Before Starting Work

1. Run `bd ready` to see available issues
2. Run `bd show <id>` to understand the issue scope
3. Check `docs/ROADMAP.md` for M0–M5 phases and dependencies
   - Example: M2 (Generation infrastructure) depends on M0 (validation/planning) being solid

### During Development

1. **Validate schemas locally**
   ```bash
   uv run pytest tests/
   ```

2. **Test with the example episode**
   ```bash
   uv run wf validate episodes/s01e01_map_forgot_roads/episode.yaml --allow-missing-assets
   ```

3. **Check code quality**
   ```bash
   uv run ruff check src/ tests/
   ```

### Quality Gates (MANDATORY before push)

- [ ] Tests pass: `uv run pytest tests/`
- [ ] Linter passes: `uv run ruff check src/ tests/`
- [ ] Example episode still validates/plans/builds
- [ ] New tests added for new functionality
- [ ] Code follows style guide (see `docs/style_guide.md` for visual rules, apply PEP 8 elsewhere)

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **Verify quality gates pass** (if code changed):
   ```bash
   uv run pytest tests/
   uv run ruff check src/ tests/
   uv run wf validate episodes/s01e01_map_forgot_roads/episode.yaml --allow-missing-assets
   ```

2. **File issues for remaining work** - Create issues for anything that needs follow-up

3. **Update issue status**:
   ```bash
   bd update <id> --status in_progress  # If pausing mid-work
   bd close <id>                        # If work is done
   ```

4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

## Key Docs (Read These)

- `docs/ARCHITECTURE.md` – Build system design + constraints
- `docs/ROADMAP.md` – Phases M0–M5 with dependencies
- `docs/CLI_SPEC.md` – Command contracts (what each CLI command does)
- `docs/TIMELINE_IR.md` – Timeline IR schema
- `docs/PROVENANCE.md` – Asset generation metadata
- `docs/RENDER_SPEC.md` – Rendering engine spec (M3+)
