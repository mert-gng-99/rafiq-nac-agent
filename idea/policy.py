"""Rafiq - a pilgrim group safety agent that runs on the local SIM pack.

More than a million people arrive from abroad for Hajj in one season, and forty
to fifty of them often share a single guide. Many are old, tired and far from
home. When someone goes missing the guide calls again and again, and nobody
knows whether the phone is off, out of battery, out of signal, or simply not
heard in the noise.

The design decision that makes this buildable is the SIM. CAMARA location APIs
need the consent of the line owner, and a foreign SIM on roaming is where
Open Gateway demos quietly fall apart. Rafiq runs on the local SIM or eSIM pack
agencies already hand out on arrival, so the line sits on the home network and
one consent at hand-over covers the trip.

So the agent checks roaming *first*, for one unit. A line that is roaming is a
pilgrim still on their own foreign SIM, and the honest answer is not a location
reading of doubtful provenance - it is to go and swap them onto the agency SIM.

The other rule: act before anyone is lost. Congestion tells the guide the next
area is filling up while the group is still together, which is worth more than
any alert sent after a person is already gone.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.agent import Case
from core.camara import ApiResult
from core.signals import read_signal

LEVELS = ["settled", "nudge", "locate", "escalate"]


class RafiqPolicy:
    name = "rafiq"
    kind = "pilgrim_event"
    levels = LEVELS
    budget_units = 20.0

    tool_names = [
        "verify_number",
        "check_roaming",
        "verify_location",
        "check_reachability",
        "retrieve_location",
        "query_congestion",
        "watch_area",
        "reserve_quality",
    ]

    def system_prompt(self, case: Case) -> str:
        return (
            "You are Rafiq, the agent helping a pilgrimage guide keep a group of "
            "forty to fifty people together during Hajj. Many are elderly and do "
            "not speak the local language.\n\n"
            "The product runs on the local SIM pack the agency hands out on "
            "arrival. That matters to every decision you make:\n"
            "1. Check roaming first. It costs one unit. A line that is roaming is "
            "a pilgrim still using their own foreign SIM, which means you have no "
            "reliable consented location for them. Do not guess - tell the guide "
            "to swap them onto the agency SIM, and stop there.\n"
            "2. For a line on the home network, ask the yes/no area question "
            "about the group's zone before anything more revealing.\n"
            "3. When someone is inside the zone, the useful question is about the "
            "crowd, not the person. Congestion in the next cell lets the guide "
            "tighten the group before anyone is lost, which is worth more than "
            "any alarm raised afterwards.\n"
            "4. When someone has left the zone, do not raise an alarm yet. Ask "
            "whether the line can be reached at all. A pilgrim who answers needs "
            "a message; a silent line needs the guide and a last known area.\n"
            "5. PARTIAL and UNKNOWN are not emergencies. A dense crowd answers "
            "that way. Retrieve the area and send the guide; do not escalate.\n\n"
            "Access ends the day the trip ends. Never build a record of anyone's "
            "day beyond the question in front of you."
        )

    def describe_case(self, case: Case) -> str:
        f = case.facts
        return (
            "Pilgrim event: %s\n"
            "  pilgrim: %s, age %s, speaks %s\n"
            "  group: %s, guide %s\n"
            "  group zone: %s m around the camp point\n"
            "  line: %s (agency SIM pack)"
            % (
                f.get("event", "check"),
                f.get("pilgrim_name", "unknown"),
                f.get("age", "unknown"),
                f.get("language", "unknown"),
                f.get("group_id", "unknown"),
                f.get("guide", "unknown"),
                case.radius_m,
                case.subject,
            )
        )

    def interpret(self, tool: str, result: ApiResult, facts: Dict[str, Any]) -> Dict[str, Any]:
        return read_signal(tool, result)

    def next_tool(
        self, case: Case, facts: Dict[str, Any], used: List[str]
    ) -> Optional[Tuple[str, Dict[str, Any], str]]:
        if case.facts.get("event") == "enrol":
            return self._enrol(case, facts)

        # Roaming first, always. Everything after this depends on the line
        # sitting on the home network.
        if "roaming" not in facts:
            return (
                "check_roaming",
                {},
                "One unit, and it decides whether any of the rest is even valid. "
                "A roaming line is a pilgrim on their own foreign SIM.",
            )
        if facts.get("roaming"):
            return None  # the answer is a SIM swap at the desk, not more API calls

        if "location_result" not in facts:
            return (
                "verify_location",
                {},
                "Ask whether this line is still inside the group's zone. A yes/no "
                "question, no coordinates returned, two units.",
            )

        if facts.get("location_inside"):
            if "congestion" not in facts:
                return (
                    "query_congestion",
                    {},
                    "The pilgrim is with the group, so the useful question is about "
                    "the crowd. If the cell is filling up the guide can tighten the "
                    "group now, before anyone is lost.",
                )
            return None

        # Outside the zone, or an uncertain answer. Either way, reachability is
        # the next question and it is cheap.
        if "reachability" not in facts:
            return (
                "check_reachability",
                {},
                "Do not raise an alarm on a location answer alone. One unit tells "
                "us whether this person can be reached at all, which decides "
                "between a message and a search.",
            )

        if "has_last_known_point" not in facts:
            return (
                "retrieve_location",
                {},
                "The line is outside the zone. Now the guide needs somewhere to "
                "walk to, so the more revealing call has earned its place.",
            )

        if facts.get("silent") and "congestion" not in facts:
            return (
                "query_congestion",
                {},
                "Silent line. Check whether the cell is saturated before the guide "
                "tries to open a video call from inside the crowd.",
            )

        if facts.get("silent") and facts.get("cell_crowded") and "qod_session_id" not in facts:
            return (
                "reserve_quality",
                {"profile": "QOS_L", "duration_s": 900},
                "The cell is busy and the guide is about to need video. Reserve "
                "the quality instead of hoping for it.",
            )
        return None

    def _enrol(self, case: Case, facts: Dict[str, Any]):
        if "number_verified" not in facts:
            return (
                "verify_number",
                {},
                "Confirm the agency SIM is in the phone we are about to enrol.",
            )
        if not facts.get("number_verified"):
            return None
        if "geofence_id" not in facts:
            return (
                "watch_area",
                {"event": "left", "radius_m": case.radius_m},
                "Subscribe this one line to area-left events for the group zone. "
                "CAMARA geofencing is per line and consented, which is why every "
                "pilgrim is enrolled at hand-over rather than swept off a map.",
            )
        return None

    # -- the floor -----------------------------------------------------------

    def decide(self, case: Case, facts: Dict[str, Any]) -> Tuple[str, str, str, float]:
        if case.facts.get("event") == "enrol":
            return self._decide_enrol(case, facts)

        name = case.facts.get("pilgrim_name", "this pilgrim")
        language = case.facts.get("language", "their language")

        if "roaming" not in facts:
            return (
                "nudge",
                "Do a manual headcount for this pilgrim",
                "No network evidence was available for this line, so the guide has "
                "nothing from Rafiq and should fall back to counting heads.",
                0.35,
            )

        if facts.get("roaming"):
            return (
                "nudge",
                "Take %s to the desk and move them onto the agency SIM" % name,
                "This line is roaming on a visited network, which means %s is still "
                "using their own foreign SIM. Rafiq has no consented, reliable "
                "location for a roaming line, and pretending otherwise would be the "
                "dishonest answer. The fix is a SIM, not an API call." % name,
                0.9,
            )

        if facts.get("location_inside"):
            if facts.get("cell_saturated"):
                return (
                    "nudge",
                    "Tell the guide to close the group up before moving on",
                    "%s is with the group, and the cell serving them is already "
                    "saturated. This is the warning that arrives before anyone is "
                    "missing, which is the only kind worth much in a crowd." % name,
                    0.86,
                )
            if facts.get("cell_crowded"):
                return (
                    "nudge",
                    "Advise the guide the next area is filling up",
                    "%s is with the group and the serving cell is busy but not "
                    "saturated. Worth a word to the guide, not an intervention." % name,
                    0.8,
                )
            return (
                "settled",
                "Nothing to do",
                "%s is inside the group zone and the cell around them is quiet." % name,
                0.9,
            )

        if facts.get("silent"):
            extra = ""
            if facts.get("has_last_known_point"):
                extra = " A last known area has been retrieved for the guide"
                if facts.get("qod_session_id"):
                    extra += ", with a reserved quality session for the video call"
                extra += "."
            return (
                "escalate",
                "Send the guide to the last known area now and alert the agency",
                "%s is outside the group zone and the network cannot reach their "
                "line at all. A phone that is off or out of battery in a crowd of "
                "this size is the case that needs a person walking, not another "
                "message.%s" % (name, extra),
                0.9,
            )

        if facts.get("location_uncertain"):
            return (
                "locate",
                "Send one short message in %s, then have the guide walk toward the last known area" % language,
                "The network could not answer cleanly, which is what a dense crowd "
                "looks like rather than a person in trouble. %s is reachable, so a "
                "message comes first and the guide moves while waiting." % name,
                0.75,
            )

        return (
            "locate",
            "Send one short message in %s and watch which way they move" % language,
            "%s has left the group zone but the line is reachable, so this is "
            "someone who wandered rather than someone in danger. A message in "
            "their own language, then check the direction of travel again." % (name, ),
            0.85,
        )

    def _decide_enrol(self, case: Case, facts: Dict[str, Any]):
        name = case.facts.get("pilgrim_name", "this pilgrim")
        if not facts.get("number_verified", True):
            return (
                "nudge",
                "Check the SIM is seated properly and try enrolment again",
                "The network would not confirm this line is in this handset, so the "
                "enrolment cannot be trusted.",
                0.8,
            )
        if facts.get("geofence_active"):
            return (
                "settled",
                "%s is enrolled; the group fence is live" % name,
                "The agency SIM is confirmed in the handset and an area-left "
                "subscription is active for the group zone. One consent at "
                "hand-over covers the trip, and access ends when the trip does.",
                0.92,
            )
        return (
            "nudge",
            "Retry the geofence subscription for this line",
            "The line verified but the area subscription did not come back active.",
            0.6,
        )
