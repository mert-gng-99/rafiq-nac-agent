"""Rafiq product spec: theme 3, tourism, pilgrimage and cultural experience."""

from __future__ import annotations

from core.agent import Case
from core.idea import ConsentPlan, IdeaSpec, LevelStyle, Scenario, UiSpec
from core.simulator import LineProfile

from .policy import RafiqPolicy

POLICY = RafiqPolicy()

# The group's camp in Mina, and a 600 m zone that follows them through the day.
CAMP = (21.4133, 39.8933)
ZONE_RADIUS_M = 600
_M_PER_DEG_LAT = 111320.0


def _away(metres: float) -> tuple:
    return (CAMP[0] + metres / _M_PER_DEG_LAT, CAMP[1])


# Agency SIM pack numbers: on the home network, which is the whole design.
LINE_SETTLED = LineProfile(
    msisdn="+966560000301",
    label="With the group, quiet cell",
    latitude=CAMP[0],
    longitude=CAMP[1],
    location_accuracy_m=180,
    congestion="low",
    notes="The ordinary case: two calls and nothing to do.",
)

LINE_CROWD = LineProfile(
    msisdn="+966560000302",
    label="With the group, but the cell is saturated",
    latitude=CAMP[0],
    longitude=CAMP[1],
    location_accuracy_m=180,
    congestion="high",
    congestion_confidence=88,
    notes="The warning that arrives before anyone is missing.",
)

LINE_STRAYED = LineProfile(
    msisdn="+966560000303",
    label="1.8 km from the group, phone answering",
    latitude=_away(1800)[0],
    longitude=_away(1800)[1],
    location_accuracy_m=250,
    notes="Wandered, not in danger.",
)

LINE_SILENT = LineProfile(
    msisdn="+966560000304",
    label="2.4 km from the group and unreachable",
    latitude=_away(2400)[0],
    longitude=_away(2400)[1],
    location_accuracy_m=400,
    reachability="NOT_CONNECTED",
    congestion="high",
    notes="Elderly pilgrim, phone dead or off. The case the guide cannot solve by calling.",
)

LINE_UNCERTAIN = LineProfile(
    msisdn="+966560000305",
    label="Somewhere on the zone boundary in a dense crowd",
    latitude=_away(620)[0],
    longitude=_away(620)[1],
    location_accuracy_m=500,
    force_verification="PARTIAL",
    notes="An uncertain answer is not an emergency.",
)

LINE_FOREIGN_SIM = LineProfile(
    msisdn="+92300000306",
    label="Still on their own Pakistani SIM, roaming",
    roaming=True,
    country_code=966,
    country_name="SAU",
    latitude=CAMP[0],
    longitude=CAMP[1],
    notes="The roaming problem, answered honestly instead of hidden.",
)

LINE_ENROL = LineProfile(
    msisdn="+966560000307",
    label="Just handed an agency SIM at the airport",
    latitude=CAMP[0],
    longitude=CAMP[1],
    location_accuracy_m=180,
    notes="Enrolment: verify the SIM, then subscribe the group fence.",
)


def _check(subject: str, name: str, age: int, language: str, label: str) -> Case:
    return Case(
        subject=subject,
        kind="pilgrim_event",
        label=label,
        facts={
            "event": "check",
            "pilgrim_name": name,
            "age": age,
            "language": language,
            "group_id": "MIN-42",
            "guide": "Abu Omar",
        },
        latitude=CAMP[0],
        longitude=CAMP[1],
        radius_m=ZONE_RADIUS_M,
        params={"qos_profile": "QOS_L", "qos_duration_s": 900},
    )


SCENARIOS = [
    Scenario(
        id="group-settled",
        title="Routine check, pilgrim with the group",
        subtitle="Inside the 600 m zone, serving cell quiet",
        expect_level="settled",
        lines=[LINE_SETTLED],
        narrative="What most checks look like.",
        teaches=(
            "Roaming first for one unit, then the yes/no zone question, then the "
            "crowd. Three cheap calls, nothing revealing, nothing to do."
        ),
        build_case=lambda: _check(
            LINE_SETTLED.msisdn, "Hafiza", 68, "Urdu", "Routine check"
        ),
    ),
    Scenario(
        id="crowd-building",
        title="The next area is filling up",
        subtitle="Pilgrim still with the group, but the cell is saturated",
        expect_level="nudge",
        lines=[LINE_CROWD],
        narrative="Acting before anyone is missing.",
        teaches=(
            "Nobody is lost here. Congestion insights let the guide close the group "
            "up before they walk into a crowded cell, which is the part of crowd "
            "safety that happens before an alert."
        ),
        build_case=lambda: _check(
            LINE_CROWD.msisdn, "Ismail", 71, "Urdu", "Crowd building ahead"
        ),
    ),
    Scenario(
        id="strayed-reachable",
        title="Outside the zone, phone answering",
        subtitle="1.8 km from the group and reachable on data",
        expect_level="locate",
        lines=[LINE_STRAYED],
        narrative="A wanderer, not an emergency.",
        teaches=(
            "Leaving the zone raises no alarm on its own. The agent asks whether "
            "the line is reachable first, and a pilgrim who can be messaged gets a "
            "message in their own language before a guide is sent running."
        ),
        build_case=lambda: _check(
            LINE_STRAYED.msisdn, "Kareem", 54, "Arabic", "Strayed but reachable"
        ),
    ),
    Scenario(
        id="strayed-silent",
        title="Outside the zone and unreachable",
        subtitle="2.4 km away, network cannot reach the line at all, cell saturated",
        expect_level="escalate",
        lines=[LINE_SILENT],
        narrative="The case this product exists for.",
        teaches=(
            "The reachability answer is what turns a missed call into an "
            "escalation. Then a last known area for the guide, and because the cell "
            "is saturated, a reserved quality session so the video call connects."
        ),
        build_case=lambda: _check(
            LINE_SILENT.msisdn, "Fatima", 74, "Urdu", "Silent and outside the zone"
        ),
    ),
    Scenario(
        id="uncertain-in-crowd",
        title="The network answers PARTIAL",
        subtitle="On the zone boundary in a dense crowd, line reachable",
        expect_level="locate",
        lines=[LINE_UNCERTAIN],
        narrative="Refusing to panic on an uncertain answer.",
        teaches=(
            "PARTIAL is what a dense crowd looks like, not what a person in trouble "
            "looks like. The agent sends a message and moves the guide, and does not "
            "spend the agency's escalation on a boundary case."
        ),
        build_case=lambda: _check(
            LINE_UNCERTAIN.msisdn, "Bilqis", 66, "Urdu", "Uncertain fix in a crowd"
        ),
    ),
    Scenario(
        id="foreign-sim-roaming",
        title="Still on their own foreign SIM",
        subtitle="Line is roaming, so there is no reliable consented location",
        expect_level="nudge",
        lines=[LINE_FOREIGN_SIM],
        narrative="The objection most Open Gateway pitches talk around.",
        teaches=(
            "Rafiq checks roaming first and stops there. A roaming foreign SIM has "
            "no reliable consented location, so the honest action is to walk the "
            "pilgrim to the desk and swap the SIM - not to produce a location "
            "reading nobody should trust."
        ),
        build_case=lambda: _check(
            LINE_FOREIGN_SIM.msisdn, "Nadir", 59, "Urdu", "Pilgrim on a roaming SIM"
        ),
    ),
    Scenario(
        id="enrol-at-handover",
        title="Enrol a pilgrim at SIM hand-over",
        subtitle="Verify the agency SIM, then subscribe the group fence for that line",
        expect_level="settled",
        lines=[LINE_ENROL],
        narrative="Where consent is actually taken.",
        teaches=(
            "CAMARA geofencing is per line and consented; there is no API that asks "
            "who is inside an area. So enrolment happens at hand-over, one line at "
            "a time, and the subscription is what the rest of the trip runs on."
        ),
        build_case=lambda: Case(
            subject=LINE_ENROL.msisdn,
            kind="pilgrim_event",
            label="Enrolment at the airport desk",
            facts={
                "event": "enrol",
                "pilgrim_name": "Salma",
                "age": 63,
                "language": "Urdu",
                "group_id": "MIN-42",
                "guide": "Abu Omar",
            },
            latitude=CAMP[0],
            longitude=CAMP[1],
            radius_m=ZONE_RADIUS_M,
            params={"webhook_url": "https://rafiq.example/hooks/geofence"},
        ),
    ),
]

SPEC = IdeaSpec(
    slug="rafiq",
    name="Rafiq",
    tagline="A pilgrim group safety agent that runs on the local SIM pack",
    theme_number=3,
    theme_name="Tourism, Pilgrimage & Cultural Experience Innovation",
    submission_title="Rafiq - a pilgrim group safety agent that runs on the local SIM pack",
    submission_description=(
        "Rafiq is an AI agent for pilgrimage agencies and group guides. It runs on "
        "the local SIM pack agencies already hand out on arrival, which removes the "
        "roaming consent problem instead of hiding from it, and it acts on crowd "
        "congestion before anyone is missing."
    ),
    policy=POLICY,
    scenarios=SCENARIOS,
    lines=[
        LINE_SETTLED,
        LINE_CROWD,
        LINE_STRAYED,
        LINE_SILENT,
        LINE_UNCERTAIN,
        LINE_FOREIGN_SIM,
        LINE_ENROL,
    ],
    consent=ConsentPlan(
        moment="at SIM hand-over on arrival, in one clear line with the pack",
        scopes=[
            "identity:verify",
            "device:status",
            "location:verify",
            "location:retrieve",
            "location:geofence",
            "network:insights",
            "network:qod",
        ],
        who_consents=(
            "the pilgrim, who owns the agency SIM for the duration of the trip and "
            "is the line owner CAMARA requires"
        ),
        duration_note="The grant expires the day the trip ends, with no action needed by anyone.",
        revocation=(
            "A pilgrim can hand the SIM back or ask to be removed at any time, which "
            "cancels the geofence subscription immediately."
        ),
    ),
    ui=UiSpec(
        accent="#0f8f8f",
        accent_soft="#e3f4f4",
        hero_kicker=(
            "Forty pilgrims, one guide, and a crowd. Rafiq runs on the agency SIM so "
            "consent and location actually work, and it warns the guide before "
            "anyone is lost."
        ),
        subject_label="Pilgrim line (agency SIM)",
        case_label="Pilgrim check",
        run_all_label="Run all seven checks",
        ad_hoc_placeholder="+966560000304",
        ad_hoc_help=(
            "An ad-hoc check runs the routine path against the Mina camp zone. "
            "Try a number starting +92 to see the roaming branch."
        ),
        levels=[
            LevelStyle("settled", "Settled - nothing to do", "calm",
                       "With the group, quiet cell."),
            LevelStyle("nudge", "Nudge the guide", "watch",
                       "A word to the guide, before anything goes wrong."),
            LevelStyle("locate", "Locate - message and walk", "warn",
                       "Outside the zone but reachable."),
            LevelStyle("escalate", "Escalate - send the guide now", "alarm",
                       "Outside the zone and unreachable."),
        ],
    ),
    honest_limits=[
        "Rafiq tracks a line, not a person. A pilgrim who leaves their phone in the "
        "tent reads as a pilgrim in the tent, and no network API can fix that.",
        "It depends on the agency actually issuing local SIMs. An agency that does "
        "not cannot use this product, and we would rather say so than claim roaming "
        "coverage we cannot deliver.",
        "Location resolution is cell and area level. It puts a guide in the right "
        "few hundred metres; it does not point at a person in a crowd.",
        "Congestion insights describe the network, not the crowd. A saturated cell "
        "is strong evidence of density, but it is evidence and not a headcount.",
    ],
    buyers=[
        "Pilgrimage agencies paying a small fee per traveller for the trip",
        "Mobile operators, who sell Rafiq with the pilgrim SIM pack and earn per API call",
        "Later: stadiums, festivals, school trips and city marathons",
    ],
    repo_name="rafiq-nac-agent",
    demo_notes=(
        "Run the roaming scenario early. It is the question a judge who knows "
        "CAMARA will ask, and the product answers it in the first API call."
    ),
)
