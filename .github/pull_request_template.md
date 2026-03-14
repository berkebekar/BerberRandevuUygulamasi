## Summary
- What changed?
- Why was it needed?

## Behavior Safety
- [ ] No breaking API change
- [ ] Existing behavior preserved
- [ ] Backward compatibility checked

## Quality Gates
- [ ] `backend`: `ruff check app tests`
- [ ] `backend`: `black --check app tests`
- [ ] `backend`: `mypy app`
- [ ] `backend`: `pytest`
- [ ] `frontend`: `npm run lint`
- [ ] `frontend`: `npm run typecheck`
- [ ] `frontend`: `npm run build`

## Docs
- [ ] `.private-docs/CLAUDE.md` updated (if affected)
- [ ] README updated (if setup/run behavior changed)

## Risks
- Main risk:
- Mitigation:
