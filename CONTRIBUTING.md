# Contributing

## Criteria

A resource belongs in this list if it:

1. **Addresses a specific harness problem** — context delivery, tool design, planning artifacts, permissions, memory, verification, sandboxing, or agent loop structure.
2. **Is worth someone's time** — not just "exists." Include a 1–2 sentence note explaining why.
3. **Is vendor-agnostic by principle** — resources tied to a specific model or platform are fine if the *pattern* generalizes.

## What doesn't belong

- General AI/ML papers not specific to agent harnesses
- Model capability benchmarks unrelated to harness design
- Product marketing or announcement posts without technical substance
- Tutorials on using a model (vs. building the scaffolding around it)

## How to contribute

1. Fork and create a branch.
2. Add your resource to the appropriate section in `README.md`.
3. Format: `- [Title](URL) — 1–2 sentence note explaining why it's worth including.`
4. Open a pull request with a brief description of what you're adding and why.

## Verify URLs

Install the verifier dependency and check the entire list before opening a pull request:

```bash
python -m pip install -r requirements.txt
python verify_urls.py --no-cache
```

Use `python verify_urls.py --limit 20 --no-cache` only as a quick local smoke test.
The limited command does not replace the required full pre-PR check.

## Updating existing entries

If a link is dead or a resource has a better successor, open an issue or PR with the replacement.

## Template contributions

If you have a harness artifact template (AGENTS.md, PLAN.md, etc.) that you've used in production and found valuable, add it to `templates/` with a brief header comment explaining the intended use.
