# Coarena provider setup and security

Coarena is registered as a native MoneyPrinterTurbo LLM provider. It uses the
OpenAI-compatible Chat Completions API, so the existing server-side Python
provider adapter sends the request. The browser does not need the Coarena key.

## Provider settings

In MoneyPrinterTurbo, open Settings, then LLM Settings, and select **Coarena**.

- API key: your personal Coarena key.
- Base URL: `https://coarena.ai/api/v1`.
- Model: use an exact ID from the live catalogue at
  https://coarena.ai/docs. The initial default is `claude-sonnet-5-5`.
- Save the settings and use MoneyPrinterTurbo's **Test Model Connection**
  control before generating a script.

The API is OpenAI-compatible at `POST /api/v1/chat/completions`. Coarena's
model list and API details are published at https://coarena.ai/docs and
https://coarena.ai/developers.

## Create a restricted key

1. Open https://coarena.ai/account/api while signed in.
2. Create a new personal key named `MoneyPrinterTurbo-private`.
3. Grant only `inference:write` for normal model calls. Do not grant
   `inference:read` unless you intentionally want this key to read request
   history and usage.
4. Choose the shortest available expiry, 30 days, then create the key.
5. Copy it once directly into the private MoneyPrinterTurbo settings. Do not
   paste it into chat, a public issue, a screenshot, source code, or a public
   deployment variable.

Coarena shows a new key only once. If it is exposed or lost, revoke it and
create a replacement. Revocation is documented to take effect within about
10 seconds.

## Keep other people from spending your allowance

A server-side key protects the secret from browser users, but it does not by
itself stop people who can use an exposed MoneyPrinterTurbo instance from
submitting model requests through the app.

For a private local installation:

- Keep the instance on your own device.
- Set `listen_host = "127.0.0.1"` in your private `config.toml` unless a
  private reverse proxy needs to reach it.
- Do not forward the WebUI/API port to the public internet or share a public
  tunnel.

For a hosted installation:

- Put the whole WebUI behind an identity-aware access gateway or VPN.
- Permit only your own account/devices.
- Keep the service port private behind the gateway.
- Add application-level rate limits and a daily request/spend ceiling before
  inviting other users.
- Keep the Coarena key in the host's secret manager or private runtime
  `config.toml`, not in GitHub or browser JavaScript.

MoneyPrinterTurbo's optional `app.api_key` setting protects its FastAPI API
routes and generated task files when configured. It is not a substitute for
access control on the entire WebUI. Use a separate access gateway or VPN for
the WebUI.

## Privacy and cost constraints

Coarena's current Model API documentation says every request and response is
stored regardless of the client's `store` setting. Its terms say submitted
prompts and replies remain in Coarena's data and datasets and cannot be withdrawn
later, except where the law requires deletion. Do not submit passwords, API
secrets, financial or government identifiers, health information, private
customer data, personal records, unpublished confidential material, or other
sensitive information through Coarena.

Before the first model request, sign in to the Coarena account page and confirm
that the current Model API terms have been accepted. Until accepted, the API
returns HTTP 403 with `model_api_terms_required`. Coarena's current terms also
require Model API users to be at least 18 years old.

The documented free allowance is up to $5 of model use per day, with 30
requests per minute and 2 concurrent requests. An account-level daily request
limit may also apply. These are Coarena account limits, not a guarantee of
unlimited or permanent free usage. Check your limits and usage from the
Coarena API page.

Coarena also says its free Model API may route some requests to a lower-cost
model than the one requested. The actual model is reported in the response and
in Coarena's request history. MoneyPrinterTurbo currently consumes the returned
text without displaying the actual Coarena model in its main UI, so check the
Coarena request history when model identity matters.

## Safe connection test

1. Configure the key only in the private MoneyPrinterTurbo runtime.
2. Select Coarena and the exact model ID.
3. Run **Test Model Connection** with a harmless prompt such as
   `Reply with the word READY.`
4. Confirm the UI reports a successful connection and verify usage in Coarena.
5. Generate one short test script. Check usage again before any larger job.

This test confirms text-model access only. It does not prove that stock media,
voice, image/video generation, rendering, or publishing are free. Those
services remain separately configured.

## Security boundary

The key is not included in this repository. Only the provider name, default
endpoint, example configuration fields, and setup guidance are committed.
