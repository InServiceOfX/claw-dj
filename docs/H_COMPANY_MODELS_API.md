# H Company for DJ planning

Researched 2026-10-05/06 against H's own documentation. H offers two different
API products. The **Models API** is a direct inference endpoint and fits our
text-in/text-out provider interface. The **Agents API** manages environments,
tools and sessions; the former h-agent route used that platform even though it
was only asking a planning question. Curation and mix planning now use only
the Models API.

- POST `https://api.hcompany.ai/v1/chat/completions`.
- Bearer authentication using `HAI_API_KEY` in the repo's ignored `.env` or
  process environment. We do not search Holo's credential files or run login.
- Standard messages support string content, so screenshots are unnecessary.
  Answers arrive in `choices[0].message.content`; reasoning is a separate
  read-only field and is not parsed as a candidate list.
- H documents `holo3-1-35b-a3b` for free access (10 requests per minute, 64K
  context; Holo3 maximum output is 8,192 tokens). This is our conservative
  default so a configured key alone enables the option.
- `CLAWDJ_HCOMPANY_MODEL` can select another served model. H currently recommends
  `holo4-35b-a3b` for production, with `holo4-27b` for denser reasoning; Holo4
  requires funded API access. We do not automatically upgrade or purchase access.
- We request text only, low temperature, at most 8,192 output tokens and disabled
  thinking for these single-shot calls. No tools, web agent or desktop bridge.
- 401/403, model errors, rate limits and malformed/truncated replies are surfaced
  as provider errors. Mix planning keeps its guarded local optimizer fallback;
  curation and note previews report failure without mutating the collection.

The API protocol supports our integration. It does **not** establish Holo's
quality as a music curator or DJ; that needs comparison on the same briefs and
audible acceptance of resulting plans. Provider availability currently means
the key is configured, not that account entitlement has been live-verified.
No H Company completion was made during this change because HAI_API_KEY was
not configured in the repo environment. Local llama-server was tested separately
with a synthetic catalog, without sending private library data.

Sources:

- [Models introduction](https://hub.hcompany.ai/models-api/introduction)
- [Quickstart](https://hub.hcompany.ai/models-api/quickstart)
- [Chat completion reference](https://hub.hcompany.ai/models-api/chat-completions)
- [Authentication, rate limits and errors](https://hub.hcompany.ai/models-api/api-reference)
- [Served models and pricing](https://hcompany.ai/models-api)

Add your key to `.env`, then press **Refresh models** on Curate or Create the
mix. Choose **H Company Holo API key**. Never paste a key into a DJ brief.

```dotenv
HAI_API_KEY=your-key-here
# Current flagship, checked 2026-10-06; funded access required.
CLAWDJ_HCOMPANY_MODEL=holo4-27b
# Faster/lower-cost Holo4 alternative: holo4-35b-a3b.
# Omit the override for previous-generation free-tier holo3-1-35b-a3b.
```
