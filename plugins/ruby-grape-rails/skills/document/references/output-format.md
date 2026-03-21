# Documentation Output Format

Write documentation report to `.claude/plans/{slug}/reviews/{feature}-docs.md`:

```markdown
# Documentation: {Feature}

## Generated Documentation

### Module Documentation Added

| Module | Description |
|--------|-------------|
| `MyApp::Auth` | Authentication context |
| `MyApp::MagicToken` | Magic token model |

### Method Documentation Added

| Method | Module |
|--------|--------|
| `create_magic_token` | MyApp::Auth |
| `verify_magic_token` | MyApp::Auth |

### README Updated

- Added "Magic Link Authentication" section

### ADR Created

- `docs/adr/003-magic-link-auth.md`

## Documentation Checklist

- [x] All new modules have YARD/RDoc documentation
- [x] All public methods have documentation with @param and @return
- [x] Complex logic has inline comments explaining why
- [x] README updated for user-facing features
- [x] ADR created for architectural decisions
```
