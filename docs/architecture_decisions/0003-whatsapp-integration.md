# 0003. How we connect to WhatsApp

- **Status:** Proposed. Open for discussion.
- **Date:** 2026-09-24
- **Deciders:** @DaniPopov

## Context

Muninn only has value if it can **receive** messages (text + voice) and **send**
messages on its own schedule (reminders). There are two families of ways to do this,
with very different trade-offs for a self-hosted, open-source project.

One detail matters a lot for us: **reminders are messages Muninn starts by itself**,
sometimes days after the user last wrote.

## Options considered

### Option A: Official WhatsApp Business Cloud API (Meta)

- 👍 Official, stable, allowed by WhatsApp's terms. No risk of the number being banned.
- 👍 Plain HTTPS webhooks + REST. Works from any language.
- 👎 Setup is heavy for a non-technical self-hoster: Meta developer account,
  a Business app, a dedicated phone number, a public HTTPS URL for webhooks.
- 👎 **24-hour window rule:** you can only send free-form messages within 24h of the
  user's last message. After that you need a pre-approved **message template**.
  Reminders set days in advance will hit this. We'd need an approved
  "reminder" template like `⏰ Reminder: {{1}}`.
- 👎 Conversations may cost money depending on region and message category.

### Option B: Unofficial bridge (Baileys, whatsapp-web.js, or wrappers like WAHA / Evolution API)

These connect as a "linked device", like WhatsApp Web, by scanning a QR code.

- 👍 Very easy setup: scan a QR code, done. No Meta account.
- 👍 No 24-hour window, no templates, no per-message cost.
- 👎 **Against WhatsApp's Terms of Service.** The number can be banned at any time.
- 👎 Breaks when WhatsApp changes its protocol; depends on reverse-engineered libraries.
- 👎 Node-only libraries (can be run as a separate container with an HTTP API).
- 👎 An open-source project recommending a ToS-violating method by default is risky
  for users and for the project.

## Decision (proposed)

1. Define a small **`Channel` interface** in the backend (`receive message`,
   `download media`, `send text`, `send reminder`). The core agent never talks
   to WhatsApp directly.
2. Ship the **official Cloud API adapter first** and make it the documented default.
   Include a ready-to-submit reminder template and a step-by-step setup guide.
3. Allow a community-maintained **bridge adapter** (e.g. WAHA) later, clearly marked
   as unofficial with a ban-risk warning.

## Consequences

- The setup guide for the Cloud API has to be really good. It's the hardest part
  of self-hosting Muninn.
- Reminders must use a template when outside the 24h window. The scheduler needs
  to know when the user last wrote.
- The `Channel` interface also makes testing easy (a fake channel in tests), and
  leaves the door open for Telegram or Signal later.
