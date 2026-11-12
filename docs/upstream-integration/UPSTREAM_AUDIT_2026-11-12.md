# MoneyPrinterTurbo upstream reverse-engineering audit

Audit date: 2026-11-12

## Executive finding

The fork's original `main` branch is based on an older upstream snapshot. At audit time:

- Original upstream repository: `harry0703/MoneyPrinterTurbo`
- User fork: `williamsjam2x-ctrl/MoneyPrinterTurbo`
- Current upstream `main`: `82216ccbad2ff20d9c51a0cd8472e6ee6cda3f45`
- Released tag `v1.3.10`: `8b0206be2c7977e3bc3cf25ff99a2adc3c9c65f9`
- Fork's original `main`: `40d7f3de9d8e14056c72f523ecbb6700cff50372`
- The fork's original `main` is 66 commits behind current upstream `main`, with no fork-only commits on that branch.
- Upstream `main` contains 14 commits after the v1.3.10 release tag.
- The fork's `feature/upstream-sync` branch is based on upstream commit `950ba89899d3b6ef080c18ad5791e7c9ead0ac66`; it carries upstream changes and fork-specific intelligence/security work. Compared with the current integration branch it diverges, so a blind fast-forward or force-push is not appropriate.

## What MoneyPrinterTurbo does

MoneyPrinterTurbo is a Python-based short-video production system. It accepts a subject, script, or prepared materials and orchestrates an end-to-end video job.

High-level pipeline:

1. WebUI, CLI, or FastAPI receives the user's request.
2. Pydantic schemas validate video parameters and bound API input.
3. The LLM service generates narration, stock-footage search terms, and social metadata.
4. The material service searches, caches, downloads, and allocates footage or images.
5. The task service orchestrates material, voice, subtitle, and rendering stages.
6. Voice services generate narration; subtitle services align and shape captions.
7. The video service composes footage, motion, transitions, subtitles, audio, and final MP4 output with MoviePy/FFmpeg.
8. Task state, progress, files, and optional cross-posting status are tracked. Redis is available for queued and multi-worker task management.

This separation matters: the LLM is one part of the system, not the whole application. A better brain improves planning and instructions; it does not replace the renderer, media providers, task queue, voice stack, or quality controls.

## Valuable upstream work through v1.3.10

### Provider and account access

- OpenAI Codex device-code subscription access with dynamic model discovery.
- Separate ChatGPT Native OAuth integration. This is eligibility-dependent and independent of Codex device sign-in.
- Codex image generation as a material source, reusing the Codex login while keeping its image model separate from the text model.
- Infistar and Jalapeno Cloud LLM/video support.
- Runcrate, CloudGPU, and cheapaimodel LLM gateways.

Value: more choice of model and media providers; reduced dependence on one API vendor; subscription-based access where the account and model are eligible. This does not mean all inference or image/video generation is free. Each service retains its own allowance, eligibility, and billing rules.

### Production reliability and workflow

- Long-running video jobs expose stages, elapsed time, and polling status.
- Task tracking survives page refreshes and temporary query failures.
- Duplicate submissions are guarded against.
- Redis concurrency limits are shared across workers using atomic slot reservation, lease renewal, and queued-task recovery.
- Provider settings and selection are easier to navigate.
- Script/keyword errors preserve existing content and avoid continuing into dependent generation steps after script failure.

Value: fewer lost jobs, less accidental repeated paid work, clearer diagnostics, and more reliable operation for longer videos or multiple workers.

### Media quality and multilingual support

- Arabic subtitle shaping, connected glyphs, right-to-left layout, mixed-script font fallback, and glyph-aware wrapping.
- Smoother slow image zoom.
- Indonesian script-language and interface support.
- Better subtitle segmentation for dates, clock times, abbreviations, punctuation, names, Thai, and Lao.
- Better preservation of transcription timing when script alignment fails.
- Multilingual hashtag normalization preserving combining marks while removing emoji marks.
- More reliable repeated-topic matching and Pexels/Coverr search diagnostics.
- Windows path/render synchronization fixes and safer download filenames.

Value: improved readability and fidelity for more languages, fewer narration/subtitle mismatches, and fewer platform-specific rendering failures.

### Security and operations

- Remote Jalapeno video endpoints must use HTTPS; HTTP is restricted to loopback development hosts.
- Credential-bearing Jalapeno requests force TLS verification even when the global TLS setting is disabled.
- Container dependency hardening and vulnerability scanning.
- Improved Docker configuration guidance and recovery diagnostics.
- Expanded automated regression coverage.

Value: less risk of exposing bearer credentials, fewer broken deployments, and more repeatable releases.

## Additional upstream commits after v1.3.10

The current upstream `main` is 14 commits ahead of the release tag. Notable additions include:

- APIXO AI provider using the OpenAI Responses API, default model `gpt-5.4-mini`. The implementation checks that the response status is `completed` before accepting text. This is a different protocol from ordinary Chat Completions and must not be treated as a generic OpenAI-compatible chat endpoint.
- APINEBULA LLM provider.
- UberLLM OpenAI-compatible pay-as-you-go gateway. Its documentation says it is prepaid and has no free tier.
- Better sequential footage allocation so the renderer uses later portions of each clip before repeating earlier footage.
- Correct stock-video download coverage when playback speed is above 1x.
- Opaque-canvas compositing optimizations that avoid generating unnecessary full-frame transparency masks.
- More reliable subtitle cue alignment, script code-fence cleanup, full-width pause-tag handling, fallback social-title punctuation, and file-size display boundaries.
- Refreshed provider lists and resource documentation.

Value: broader provider choice, better video coverage, fewer repeated shots, smoother rendering, and fewer text/audio edge cases.

## Existing fork-specific work preserved

The integration work retains these fork additions:

1. `app/services/intelligence_router.py`: optional CodeCraft -> APINEX -> OpenAI-compatible text router. It has explicit task labels, prompt/token bounds, provider-aware output-token parameters, timeouts, and fallback after a real provider failure. It is intentionally separate from normal video generation.
2. `app/services/exa_research.py`: bounded Exa search adapter. It reads `EXA_API_KEY` from the runtime environment, enables moderation, limits result count, rejects non-HTTPS sources, and captures returned cost telemetry. It only retrieves evidence; it does not score claims or start production.
3. Jalapeno endpoint hardening: remote HTTP URLs are rejected, local loopback HTTP remains available for development, and bearer-token requests force TLS verification.
4. Fork regression tests and intelligence-layer documentation.
5. Puter.js architecture proposal: browser-side user-pays AI planning component. It is documentation only; the SDK has not yet been wired into the WebUI.

## Diagnostic assessment

### Strong points

- Good separation between provider adapters, production stages, task state, and media composition.
- Extensive test coverage in upstream, including mocked provider calls and platform-specific regression tests.
- Multiple options for text, image, voice, stock footage, and AI-video providers.
- Existing API, CLI, and WebUI entrypoints provide integration points for a planning layer.
- The user's separate intelligence router and Exa adapter can extend the system without replacing the production path.

### Risks and limitations

- Provider availability does not imply the user's account has an entitlement, free allowance, or usable payment method.
- OpenAI Responses, Chat Completions, OAuth, and Codex flows have different request/authentication contracts. A single generic provider fallback must not silently mix them.
- Puter.js user-pays only works as intended when AI requests execute in the signed-in user's browser context. A Python server request using the owner's Puter credentials would change who pays.
- Exa search is source retrieval, not factual verification. Search results and page content are untrusted input.
- Media generation, TTS, stock-media, storage, hosting, and Exa calls can still incur costs even when text planning uses an account-based allowance.
- Current upstream's full test suite is large. A clean merge is not sufficient evidence; CI and a real end-to-end render remain required.

## Integration performed

A clean branch was created on the user's fork directly from the audited current upstream HEAD:

`integration/upstream-2026-11-12` -> `82216ccbad2ff20d9c51a0cd8472e6ee6cda3f45`

A draft integration PR was opened:

- PR #4: https://github.com/williamsjam2x-ctrl/MoneyPrinterTurbo/pull/4
- Base: `integration/upstream-2026-11-12`
- Head: `feature/puter-browser-brain`
- At initial review, GitHub reported the PR mergeable after its mergeability refresh.
- The PR diff was 12 files, 1,161 additions, and 6 deletions.
- The diff preserves the intelligence router, Exa adapter, their tests/docs, Jalapeno security hardening, CI branch workflow change, and Puter architecture note.
- The PR remains draft. CI is running on Python 3.11, Python 3.13, and Windows. No merge has been performed.

## Required acceptance gates before main is updated

1. PR #4 must pass Python 3.11, Python 3.13, and Windows smoke tests.
2. Resolve any CI failures rather than bypassing checks.
3. Review the merged tree against upstream HEAD and verify the provider registry, OAuth modules, Codex image flow, subtitle shaping, Redis task manager, and updated dependency lock remain present.
4. Merge PR #4 into the integration branch only after all checks pass.
5. Create a separate PR from the integration branch to `main`.
6. Run the same CI matrix on that PR.
7. Only then merge into `main`.
8. After installation on a real machine, perform a controlled script-to-MP4 smoke render. Do not assume GitHub CI proves live provider access or end-to-end rendering with paid services.

## Current status

- Upstream investigation and code-path mapping: completed.
- Current upstream snapshot imported as a clean fork branch: completed.
- Fork-specific additions preserved in draft integration PR: completed.
- GitHub CI: in progress at audit time.
- PR #4 merge: pending CI.
- Fork `main` update: pending PR #4 validation and the separate main integration PR.
- Puter SDK implementation: not started.
- Live Exa request: not run.
- Live CodeCraft/APINEX requests: not run.
- End-to-end video render: not run.

## Primary references

- Upstream repository: https://github.com/harry0703/MoneyPrinterTurbo
- Upstream v1.3.10: https://github.com/harry0703/MoneyPrinterTurbo/releases/tag/v1.3.10
- Upstream changes since v1.3.10: https://github.com/harry0703/MoneyPrinterTurbo/compare/v1.3.10...main
- User fork: https://github.com/williamsjam2x-ctrl/MoneyPrinterTurbo
- Integration branch: https://github.com/williamsjam2x-ctrl/MoneyPrinterTurbo/tree/integration/upstream-2026-11-12
- Integration PR: https://github.com/williamsjam2x-ctrl/MoneyPrinterTurbo/pull/4
