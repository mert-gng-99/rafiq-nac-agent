# Rafiq

> A pilgrim group safety agent that runs on the local SIM pack

**MENA Ignite Hackathon - GSMA Open Gateway - Theme 3: Tourism, Pilgrimage & Cultural Experience Innovation**

Forty pilgrims, one guide, and a crowd. Rafiq runs on the agency SIM so consent and location actually work, and it warns the guide before anyone is lost.

Rafiq is an AI agent for pilgrimage agencies and group guides. It runs on the local SIM pack agencies already hand out on arrival, which removes the roaming consent problem instead of hiding from it, and it acts on crowd congestion before anyone is missing.

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000. You need no credentials, because the app starts in
`simulator` mode and every answer is tagged with its source.

Full instructions, including the Gemini planner and the live Nokia gateway, are
in **INSTRUCTIONS.md**. The design is in **ARCHITECTURE.md**.

## What it is

An AI agent that decides *which* CAMARA network check is worth making for a
given case, spends against a budget, refuses calls it has no consent for, and
explains every decision with the network answers behind it.

- **7 scenarios** ship with it, all reaching the outcome they claim
- **7 CAMARA APIs** on the Nokia Network-as-Code platform
- **67.9% cheaper** than calling every available check on every case
- **1 to 6 calls** per case, depending on what the case deserves

## Scenarios

- Routine check, pilgrim with the group. Inside the 600 m zone, serving cell quiet (expects `settled`)
- The next area is filling up. Pilgrim still with the group, but the cell is saturated (expects `nudge`)
- Outside the zone, phone answering. 1.8 km from the group and reachable on data (expects `locate`)
- Outside the zone and unreachable. 2.4 km away, network cannot reach the line at all, cell saturated (expects `escalate`)
- The network answers PARTIAL. On the zone boundary in a dense crowd, line reachable (expects `locate`)
- Still on their own foreign SIM. Line is roaming, so there is no reliable consented location (expects `nudge`)
- Enrol a pilgrim at SIM hand-over. Verify the agency SIM, then subscribe the group fence for that line (expects `settled`)

## CAMARA APIs used

| CAMARA API | What the agent asks it | Cost | Reveals |
| --- | --- | --- | --- |
| `number-verification` | Confirm the line on the phone | 1 | boolean |
| `device-status` | Is the line roaming, and where | 1 | enum |
| `location-verification` | Is the line inside this area | 2 | boolean |
| `device-status` | Can the line be reached | 1 | enum |
| `location-retrieval` | Where is the line | 4 | area |
| `congestion-insights` | How loaded is the serving cell | 1 | enum |
| `geofencing-subscriptions` | Notify me when the line leaves or enters an area | 2 | area |
| `quality-on-demand` | Reserve network quality for this line | 8 | mutates |

## The agent

```
planner proposes one call  ->  runtime checks allowlist, consent, budget
      ^                                        |
      |                                        v
  answer becomes a fact   <-   CAMARA call recorded with provenance
      |
      +--> planner submits a decision  ->  policy floor applied  ->  ledger
```

The planner is Google AI Studio (Gemini) through Pydantic AI when
`AGENT_PROVIDER=gemini` and a `GEMINI_API_KEY` are both set, and a deterministic
policy ladder otherwise. Pydantic AI returns a typed proposal only; the runtime
still holds the budget, allowlist and consent gate, and the policy holds a floor
the model cannot talk its way under.

## Tests

```bash
pytest -q
```

## What this does not do

- Rafiq tracks a line, not a person. A pilgrim who leaves their phone in the tent reads as a pilgrim in the tent, and no network API can fix that.
- It depends on the agency actually issuing local SIMs. An agency that does not cannot use this product, and we would rather say so than claim roaming coverage we cannot deliver.
- Location resolution is cell and area level. It puts a guide in the right few hundred metres; it does not point at a person in a crowd.
- Congestion insights describe the network, not the crowd. A saturated cell is strong evidence of density, but it is evidence and not a headcount.

## Layout

```
main.py            uvicorn entry point
app_spec.py        re-exports this product's spec
core/              shared platform: CAMARA client, agent, consent, ledger, UI
  camara.py        the eleven CAMARA API families, live + simulator
  simulator.py     deterministic network simulator
  agent.py         the agent loop, budget, guardrail
  tools.py         CAMARA tool registry with cost and reveal metadata
  consent.py       consent ledger enforced in the transport path
  ledger.py        SQLite decision ledger
  signals.py       CAMARA answers -> named facts
  server.py        FastAPI app
  webui.py         the operator console
idea/              this product: policy, scenarios, demo lines, copy
tests/             pytest suite
```

## Licence

MIT. See LICENSE.
