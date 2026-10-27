# Intelligence Layer — Phase 1 (provider router)

This is an **optional, separate module** for the MoneyPrinterTurbo intelligence-layer prototype. It does not replace the existing video-generation LLM setting and is not yet called automatically by the WebUI, API, or CLI. Keeping it separate lets us test provider access and fallback behavior before connecting it to video production.

## Providers

The router uses the OpenAI-compatible chat-completions interface documented by each provider:

- CodeCraft API: `https://codecraftapi.com/v1`
- APInex: `https://api.apinex.bond/v1`
- OpenAI (optional fallback): `https://api.openai.com/v1`

Provider model IDs are **not guessed**. Copy the exact model ID from the relevant account dashboard.

## Configure privately

Set these environment variables in the runtime environment (or your hosting platform's secret manager). Never commit real keys to GitHub or paste them into chat.

| Variable | Purpose |
| --- | --- |
| `CODECRAFT_API_KEY` | CodeCraft API key |
| `CODECRAFT_MODEL` | Exact CodeCraft model ID |
| `APINEX_API_KEY` | APInex API key |
| `APINEX_MODEL` | Exact APInex model ID |
| `OPENAI_API_KEY` | Optional OpenAI key |
| `OPENAI_MODEL` | Exact OpenAI model ID |
| `MPT_INTELLIGENCE_PROVIDER_ORDER` | Optional comma-separated order, e.g. `codecraft,apinex` |

Default order is CodeCraft → APInex → OpenAI. Providers missing either a key or model ID are skipped. A provider error triggers fallback to the next configured provider. Requests time out after 45 seconds, SDK retries are disabled, and combined prompt text is limited to 30,000 characters.

### Output-token limits

The router accepts a requested `max_output_tokens` from 1 to 2,048. CodeCraft documents that its API raises any `max_tokens` value below 2,048 to 2,048, so this router sends 2,048 when using CodeCraft—even if the caller asks for less. APInex receives the requested value using `max_tokens`; OpenAI receives it using `max_completion_tokens`, which is the supported parameter for its reasoning models. The router omits `temperature` because model support differs between providers. The result reports the output-token-limit value sent, but provider behavior can differ; this setting is not a guarantee of actual charges. Review provider pricing and usage before production use.

## Supported task labels

- `research_plan`
- `topic_score`
- `script_draft`
- `script_review`
- `quality_check`

The caller supplies the actual instructions and source material. The router does not independently browse the web or verify facts; fact-checking needs a separate evidence-gathering stage.

## Intended workflow after integration

1. Research candidate topics and record evidence/URLs.
2. Score relevance, audience value, hook strength, evidence quality, and production cost.
3. Draft a script and production plan.
4. Review claims against the collected evidence.
5. Send the approved script to MoneyPrinterTurbo.
6. Run a human quality gate on the generated video.
7. Require human approval before publishing.
8. Record actual results before changing future scoring.

## Validation status

Mocked unit tests cover normal responses, fallback, provider-specific token limits, invalid inputs, and missing configuration. The tests have **not yet been executed in a real Python environment**, and no live API request or video generation has been run. The next phase is to run the test suite, configure keys only in a private runtime, make one low-cost test request per provider, then wire the router into the workflow after compatibility is confirmed.
