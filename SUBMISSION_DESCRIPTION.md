## Rafiq - A pilgrim group safety agent that runs on the local SIM pack

Rafiq is an AI agent for pilgrimage agencies and group guides. It runs on the local SIM pack agencies already hand out on arrival, which removes the roaming consent problem instead of hiding from it, and it acts on crowd congestion before anyone is missing.

### The problem

Forty pilgrims, one guide, and a crowd. Rafiq runs on the agency SIM so consent and location actually work, and it warns the guide before anyone is lost.

### What the prototype actually does

Rafiq is a working web application with an operator console, a REST API, and
a live WebSocket feed of the agent's reasoning. Open it, click a scenario, and
you watch the agent choose CAMARA calls one at a time and then justify its
decision with the network answers behind it.

It runs in three modes. `simulator` needs no credentials and answers every
CAMARA call in the real CAMARA response shape, which is how the organisers
recommend demonstrating and how the test suite stays deterministic. `live`
calls the Nokia Network-as-Code gateway with your own key. `hybrid` uses live
where credentials allow and falls back per call. Every answer is tagged with
its source in the UI, so a simulated result can never pass itself off as a real
network answer.

### The AI agent layer

The agent is a planner over a CAMARA tool registry, not a script with an LLM
bolted on. Each tool in the registry carries its price, its typical latency and
how much it reveals about a person, and the planner is judged on choosing well:

1. The planner proposes one call, with a stated reason.
2. The runtime, never the model, checks it against the tool allowlist, the
   consent ledger and the remaining budget.
3. The CAMARA answer is recorded with full provenance and turned into a fact.
4. Repeat until the planner submits a decision, or the budget runs out.

The planner is Google AI Studio (Gemini) through **Pydantic AI**'s typed,
structured-output path. It is enabled by setting `AGENT_PROVIDER=gemini`
alongside a `GEMINI_API_KEY`. A model turn may only propose a next CAMARA check
or a decision; it cannot execute a network call itself. The runtime remains the
only executor of consent, the tool allowlist, argument filtering and budget.

Gemini is opt-in on both counts deliberately: a key sitting in the environment
should not be enough to start spending on a model. Otherwise a deterministic
policy planner implementing the same escalation ladder takes over, so the
prototype is demonstrable offline and CI has something stable to assert. If a
configured model cannot complete a turn, the finished case is explicitly
labelled `policy-fallback` with a bounded error reason. It is never presented
as a successful Gemini-planned decision.

**The guardrail is the part worth looking at.** The policy computes a floor for
every case from the facts alone. If the model proposes something less cautious
than the floor, the floor wins and the disagreement is written into the
decision record. A language model should choose which checks to buy; it should
not be able to clear a case the evidence says to escalate. There is a test for
exactly this.

### Results from the shipped scenarios

7 scenarios ship with the prototype, and all 7 reach the
outcome they claim. The demo and the test suite assert the same thing, so a
scenario drifting from the pitch is a build failure.

- Outcome levels reached: `settled`, `nudge`, `locate`, `escalate`
- CAMARA calls per case: 1 to 6 (average 3.3)
- Total spend across all scenarios: 45 units, against 140 if
  every available check were called on every case, a saving of 67.9%

| Scenario | Outcome | CAMARA calls | Spend |
| --- | --- | --- | --- |
| Routine check, pilgrim with the group | `settled` | 3 | 4 |
| The next area is filling up | `nudge` | 3 | 4 |
| Outside the zone, phone answering | `locate` | 4 | 8 |
| Outside the zone and unreachable | `escalate` | 6 | 17 |
| The network answers PARTIAL | `locate` | 4 | 8 |
| Still on their own foreign SIM | `nudge` | 1 | 1 |
| Enrol a pilgrim at SIM hand-over | `settled` | 2 | 3 |

The cheapest case, *Still on their own foreign SIM*, resolves in 1 call(s). The
most expensive, *Outside the zone and unreachable*, earns 6. That gap is the product:
an agent that calls everything on everyone is safe, useless and unaffordable.

### CAMARA APIs on Nokia Network as Code

`number-verification`, `device-status`, `location-verification`, `location-retrieval`, `congestion-insights`, `geofencing-subscriptions`, `quality-on-demand`

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

### Consent

CAMARA identity, location and geofencing APIs are only lawful with the consent
of the line owner, so consent is enforced in the transport path rather than
described in a policy document. An ungranted call raises before a request is
built.

Consent is taken at SIM hand-over on arrival, in one clear line with the pack,
from the pilgrim, who owns the agency SIM for the duration of the trip and is
the line owner CAMARA requires. The grant expires the day the trip ends, with
no action needed by anyone. A pilgrim can hand the SIM back or ask to be
removed at any time, which cancels the geofence subscription immediately.

You can prove this in the running app: press **Withdraw consent**, run the same
case again, and watch the agent get refused at the transport layer with zero
CAMARA calls made.

### What this does not do

- Rafiq tracks a line, not a person. A pilgrim who leaves their phone in the tent reads as a pilgrim in the tent, and no network API can fix that.
- It depends on the agency actually issuing local SIMs. An agency that does not cannot use this product, and we would rather say so than claim roaming coverage we cannot deliver.
- Location resolution is cell and area level. It puts a guide in the right few hundred metres; it does not point at a person in a crowd.
- Congestion insights describe the network, not the crowd. A saturated cell is strong evidence of density, but it is evidence and not a headcount.

### Who pays

- Pilgrimage agencies paying a small fee per traveller for the trip
- Mobile operators, who sell Rafiq with the pilgrim SIM pack and earn per API call
- Later: stadiums, festivals, school trips and city marathons

### Verification

Run `pytest -q` in the repository. The suite covers the CAMARA transport and
its provenance, the consent gate, budget enforcement, the tool allowlist, the
guardrail floor overruling an over-confident model, the LLM planner loop
against a scripted model, the full HTTP surface, and every shipped scenario.
