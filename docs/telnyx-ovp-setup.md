# Telnyx Outbound Voice Profile Setup — Protectogram

This checklist captures the **exact** Outbound Voice Profile (OVP) settings we want for **Protectogram** in **staging** and **production**. No placeholders — use these names and values.

> Scope: Only OVP settings. (Voice API Application/webhooks are configured separately.)

---

## Overview (what we will create)

- Staging OVP: **protectogram-staging-ovp**
- Production OVP: **protectogram-prod-ovp**

Both profiles will be attached to their respective **Voice API (Call Control) Applications** and **Spanish DIDs**.

---

## 1) protectogram-staging-ovp — settings

- [ ] **Name:** `protectogram-staging-ovp`
- [ ] **Default Caller ID (ANI):** set to your **staging Spanish DID** (the one assigned to the staging Voice API App)
- [ ] **Allowed Destinations:** **Spain** only
- [ ] **Block premium/satellite ranges:** **Enabled**
- [ ] **Max price/min (if available):** **Enabled** with a conservative cap suitable for test calls
- [ ] **Calls Per Second (CPS):** **1–2 CPS** (pick the closest allowed value)
- [ ] **Max Concurrent Calls:** **2–4** (pick the closest allowed value)
- [ ] **Codec order / Media:** prefer **G.711 A-law (PCMA)** → fallback **µ-law (PCMU)** (disable exotic codecs you don’t need)
- [ ] **Max Call Duration:** **20–30 minutes** hard cap
- [ ] **Recording:** **Off** (do not enable at OVP level)
- [ ] **Fraud/Security:** leave any “Fraud Guard / High-cost destination blocks” **Enabled**
- [ ] **STIR/SHAKEN / CLI policy:** present **only** numbers you own (your staging DID)
- [ ] **Save** the profile

**Notes**
- Retry/ring strategy is handled **in the app** (25s ring, 120s retry).
- AMD is handled **in the app** (log only); ack requires **DTMF “1”**.

---

## 2) protectogram-prod-ovp — settings

- [ ] **Name:** `protectogram-prod-ovp`
- [ ] **Default Caller ID (ANI):** set to your **production Spanish DID**
- [ ] **Allowed Destinations:** **Spain** (add new countries here only when business requires)
- [ ] **Block premium/satellite ranges:** **Enabled**
- [ ] **Max price/min (if available):** **Enabled** with a production-appropriate ceiling
- [ ] **Calls Per Second (CPS):** start **3–5 CPS**; tune upward only after monitoring
- [ ] **Max Concurrent Calls:** start **10–20**; tune with demand
- [ ] **Codec order / Media:** **G.711 A-law (PCMA)** → **µ-law (PCMU)**
- [ ] **Max Call Duration:** **20–30 minutes** hard cap
- [ ] **Recording:** **Off** globally (enable per call later if ever needed)
- [ ] **Fraud/Security:** keep **high-cost destination blocks** enabled
- [ ] **STIR/SHAKEN / CLI policy:** present **only** your production DID
- [ ] **Save** the profile

**Notes**
- Application logic enforces ring/ retry/ cascade strategy and country/recipient allow-lists.
- Monitor answer rates and adjust CPS/concurrency cautiously.

---

## 3) Cross-checks after saving (both profiles)

- [ ] Attach the OVP to the correct **Voice API (Call Control) Application**:
  - Staging App: **protectogram-staging-app**
  - Production App: **protectogram-prod-app**
- [ ] Ensure the **Spanish DID** for each environment is set as the **Default Caller ID**.
- [ ] Place a **test call** from staging to a whitelisted mobile:
  - Answer should play RU TTS from the app (twice), DTMF “1” acknowledges.
- [ ] Attempt a call to a **blocked country** (temporarily) to confirm policy denies (revert after test).

---

## 4) What stays out of OVP (by design)

- Ring timeout, retry cadence, cascade order → **handled in Protectogram**.
- AMD-based decisions for acknowledgement → **not used** (ack requires **DTMF “1”**).
- TTS content/voice/language → **in app** (Call Control `speak/gather` RU).

---

## 5) Change management

- Keep **staging** strict (Spain-only, low CPS/concurrency).
- Raise **prod** limits only after observing real traffic and error rates.
- Document any country additions with date/reason; update app allow-lists accordingly.

---

**Done.** Use this file as your checklist while configuring the OVPs in Telnyx Mission Control.
