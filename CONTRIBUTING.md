# Contributing

## Development setup

```bash
python3 app.py --help
make ci
```

## Quality gates

- `make lint` must pass.
- `make test` must pass.
- PRs are validated by `.github/workflows/ci.yml`.

## Release and rollback

- Follow semantic versioning tags (`vMAJOR.MINOR.PATCH`).
- Create release notes including DB/script compatibility.
- If a release fails, rollback by redeploying the previous tag and re-running `make ci`.
