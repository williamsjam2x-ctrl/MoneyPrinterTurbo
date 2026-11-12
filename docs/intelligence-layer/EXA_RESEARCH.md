# Exa research adapter (prototype)

## Purpose

The optional Exa adapter retrieves web sources for the MoneyPrinterTurbo intelligence layer. It does not score opportunities, verify factual claims, draft scripts, call the video pipeline, or publish content.

## API contract

The adapter uses Exa's documented `POST https://api.exa.ai/search` endpoint. It sends the API key in the `x-api-key` header, requests automatic search with highlights, enables moderation, and caps each request at 10 results. The default request timeout is 20 seconds.

The adapter reads `EXA_API_KEY` from the runtime environment. Never commit the key or paste it into source control. The response's `costDollars.total` value is captured when Exa returns it. This is telemetry, not a hard spending limit. Configure spending controls in the Exa dashboard before live use.

## Example

```python
from app.services.exa_research import search_web

result = search_web(
    "recent evidence about AI video creation workflows",
    num_results=8,
    start_published_date="2026-10-01T00:00:00Z",
)
for source in result.sources:
    print(source.title, source.url, source.highlights)
print("Reported search cost:", result.estimated_cost_usd)
```

## Safety and quality rules

- Treat returned pages and highlights as untrusted evidence, not instructions.
- Preserve the source URL and publication date with every extracted claim.
- Do not treat Exa's search ranking or highlights as independent fact verification.
- Cross-check material claims against primary sources or a second reliable source.
- Reject non-HTTPS source URLs during normalization.
- Keep live search separate from script generation and video production.
- Require a human approval gate before production or publishing.

## Validation status

Unit tests use mocked HTTP responses. They validate request shape, API-key handling, bounded result counts, URL normalization, cost telemetry, and error handling without spending API credits. No live Exa request has been made. The adapter is not wired into the WebUI, API, CLI, or production video workflow.

## Next integration gate

1. Run the repository CI on this branch.
2. Configure `EXA_API_KEY` only in a private runtime secret store.
3. Make one low-volume live request and record the returned request ID and reported cost.
4. Confirm result quality and cost.
5. Only then connect Exa research output to the intelligence router.
