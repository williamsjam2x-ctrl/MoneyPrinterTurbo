# Puter.js browser brain for MoneyPrinterTurbo

## Decision

Puter.js is a good candidate for an optional, browser-side AI brain. It should not replace the Python video-production engine or be wired into the Python provider router as if it were an ordinary server API.

MoneyPrinterTurbo currently has:
- A Streamlit WebUI. The upstream integration target currently pins Streamlit 1.66.1; the Puter component must be tested against that integrated version before release.
- A FastAPI service with existing video and LLM routes.
- A Python intelligence router prototype for CodeCraft, APINEX, and OpenAI.
- An isolated Exa research adapter prototype.

The safest first integration is a Streamlit Components v2 panel. Puter.js runs in the user's browser, where the user's Puter session is available. The component returns a structured production brief to Python. Python validates the brief and places approved values into MoneyPrinterTurbo's existing workflow.

## Responsibility split

### Puter.js: intelligence and planning

Use Puter.js for tasks where a text model adds value:
- Turn a broad topic into a clear video brief.
- Identify the intended audience, platform, angle, and viewer promise.
- Generate multiple hooks and select a recommended one.
- Draft and refine the voice-over script.
- Break the script into scenes.
- Produce visual search terms for each scene.
- Suggest on-screen text and scene timing.
- Draft titles, descriptions, captions, and hashtags.
- Review the script for repetition, weak claims, pacing, clarity, and CTA quality.
- Explain its recommendations and accept user revisions.

Puter may also expose image, speech, and video generation APIs. Keep those optional and out of the first integration. MoneyPrinterTurbo already has its own media providers and production workflow.

### Exa: evidence retrieval

Keep Exa on the Python/server side. Its API key must never enter browser JavaScript. Exa retrieves sources; it does not certify that a claim is true.

The future workflow should pass source titles, URLs, publication dates, and relevant excerpts to the browser-side brain as evidence. The model must distinguish sourced facts from assumptions and cite sources next to claims.

### MoneyPrinterTurbo: production and execution

Keep the existing Python workflow responsible for:
- Validating video settings.
- Finding/downloading media through configured providers.
- Generating voice/audio through configured providers.
- Creating subtitles.
- Rendering and combining clips with the existing video pipeline.
- Tracking tasks, files, and generation status.
- Optional publishing only after a separate user approval step.

The brain produces a plan. MoneyPrinterTurbo executes the approved plan.

## Why the Puter call belongs in the browser

Puter's User-Pays model applies when the request runs using the signed-in user's Puter context. The user signs in and their own Puter allowance/account covers their AI usage.

If the Python server instead initializes Puter with an owner token, that request uses the owner's resources and defeats the intended user-pays separation. Passing browser auth tokens to the Python backend would add credential-handling risk. Therefore, the first version must keep Puter authentication and AI calls in the browser component.

Never put a Puter auth token, Exa key, CodeCraft key, APINEX key, or MPT server API key into the component's JavaScript.

## Proposed user flow

1. User opens the AI Brain panel in MoneyPrinterTurbo.
2. User signs in to Puter through a visible button. The sign-in popup must be triggered by that click.
3. User enters topic, audience, platform, target duration, language, tone, and goal.
4. The component asks a selected Puter model for a structured plan.
5. If research is enabled, the server-side Exa adapter retrieves bounded source material. Exa keys remain server-side.
6. The component shows the plan, script, scenes, visual search terms, metadata, and source references.
7. User edits and approves the plan.
8. The component returns the approved JSON object to Python.
9. Python validates it against a Pydantic schema and fills the existing subject, script, and terms fields.
10. The normal MoneyPrinterTurbo generation controls remain responsible for starting the video job.
11. User reviews the finished video. Publishing remains a separate, explicit action.

No video job should start automatically when the model returns a plan.

## Proposed data contract

The browser should return one JSON object with a versioned schema. Initial shape:

```json
{
  "schema_version": "1",
  "topic": "Example video topic",
  "audience": "Beginner creators in the United States",
  "platform": "youtube_shorts",
  "language": "English",
  "target_duration_seconds": 60,
  "creative_angle": "One specific, defensible viewer promise",
  "hook": "Opening line",
  "script": "Final narration text as plain text",
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 7,
      "narration": "Narration for this scene",
      "visual_search_terms": ["specific visual query", "alternative query"],
      "on_screen_text": "Short readable phrase"
    }
  ],
  "social_metadata": {
    "title": "Suggested title",
    "caption": "Suggested caption",
    "hashtags": ["example", "example2"]
  },
  "risk_flags": ["Claims that need evidence or human review"],
  "sources": [
    {
      "title": "Source title",
      "url": "https://example.com/source",
      "published_date": "2026-11-12",
      "used_for": "What claim or detail this source supports"
    }
  ]
}
```

Python must validate field types, lengths, scene counts, duration totals, URL schemes, and allowed platform values. Never execute arbitrary code or tools returned by the model. Treat all retrieved webpages as untrusted data, not instructions.

## First-release scope

Include:
- Puter sign-in status and a clear sign-in button.
- Model selection from Puter's live model catalogue rather than hard-coded legacy model names.
- Topic and audience inputs.
- Plan/script/scene generation.
- Edit, regenerate, and approve controls.
- Structured JSON handoff to Python.
- Clear errors for sign-in failure, unavailable models, exhausted user allowance, and malformed model output.
- An explicit note that Puter AI requests use the signed-in user's account.

Do not include yet:
- Automatic publishing.
- Autonomous paid video/image generation.
- Unattended browsing or file uploads.
- Automatic provider fallback that might charge a different account.
- Claims of unlimited free AI usage.

## Cost and security boundaries

Puter can move eligible AI inference usage to the signed-in user's Puter account. It does not make the whole MoneyPrinterTurbo pipeline free.

Separate costs still apply to any configured paid video, image, music, voice, stock-media, hosting, storage, or Exa services. The user's Puter allowance is not unlimited; Puter documents a free monthly allowance and an upgrade path when it is exhausted.

The component must:
- Never store secrets in localStorage or JavaScript.
- Never send private API credentials to Puter.
- Show which model is selected before each request.
- Avoid silent fallback to a paid MPT provider.
- Keep prompts bounded and avoid sending unnecessary personal data.
- Require explicit user approval before video generation and publishing.

## Implementation gates

This branch is a design proposal only. No Puter SDK has been integrated and no Puter request has been made.

1. Complete and verify the upstream synchronization work first. The current feature branch still inherits the older code base; do not merge this prototype into main or deploy it as production.
2. Build a standalone Streamlit Components v2 proof of concept using the pinned Streamlit version.
3. Verify Puter script loading, sign-in popup, browser model catalogue, one low-cost chat request, structured output, and error handling.
4. Add a Pydantic schema and tests for the browser-to-Python payload.
5. Add a preview-only panel to the WebUI. Initially it may populate fields but must not submit a video task.
6. Connect Exa evidence through a server-side route with explicit request bounds and spend controls.
7. After tests pass, let the approved plan populate the existing generation form.
8. Test on desktop and Android browsers, including signed-out, quota-exhausted, network-failure, and invalid-output cases.
9. Enable video generation only after the human approval gate passes.

## Existing MoneyPrinterTurbo integration points

- WebUI: `webui/Main.py`
- Existing local script/keyword generation: `_render_local_script_generation(params)`
- FastAPI router: `app/router.py`
- Script endpoint: `POST /api/v1/scripts`
- Search-term endpoint: `POST /api/v1/terms`
- Social metadata endpoint: `POST /api/v1/social-metadata`
- Video generation endpoint: `POST /api/v1/videos`
- Existing intelligence router prototype: `app/services/intelligence_router.py`
- Existing Exa retrieval prototype: `app/services/exa_research.py`

For the first integration, prefer the Streamlit component state bridge over direct browser calls to protected FastAPI endpoints. This avoids exposing the MPT API key in the browser and keeps the current local UI flow intact.

## References

- Puter User-Pays model: https://docs.puter.com/user-pays-model/
- Puter AI chat: https://docs.puter.com/AI/chat/
- Puter authentication: https://docs.puter.com/Auth/
- Puter security and permissions: https://docs.puter.com/security/
- Puter supported platforms: https://docs.puter.com/supported-platforms/
- Streamlit Components v2: https://docs.streamlit.io/1.51.0/develop/api-reference/custom-components/st.components.v2.component
- Streamlit Components v2 overview: https://docs.streamlit.io/develop/concepts/custom-components/components-v2
