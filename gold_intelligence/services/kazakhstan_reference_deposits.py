"""Sourced *names-only* Kazakhstan gold bibliography.

Source-backed names of established deposits are NOT new prospects.
A web-page citation is not surveyed WGS84 geometry or a mining title.
Do not insert these records into GoldTarget without independently surveyed
site geometry and an explicit geologist review.
"""
from copy import deepcopy

ALTY_SOURCE = "https://www.altynalmas.kz/blog/news/37"
TAUKEN_SOURCE = "https://tks.kz/ru/investmentprojects/razvedka-zolota-na-mestorozhdeniyah-shokpar-i-gagarinskoe-v-zhambylskoj-oblasti/"

SOURCE_GROUPS = (
    {
        "issuer": "JSC AK Altynalmas",
        "source_url": ALTY_SOURCE,
        "published_on": "2022-06-07",
        "claim": "Named deposits from which Akbakay facility processes gold-bearing ores",
        "deposit_names": ("Akbakay", "Beskempir", "Karyernoye", "Aksakal", "Svetinskoye", "Kenzhem"),
        "administrative_location": None,
    },
    {
        "issuer": "Tau-Ken Samruk",
        "source_url": TAUKEN_SOURCE,
        "published_on": None,
        "claim": "Gold deposit exploration project summary",
        "deposit_names": ("Shokpar", "Gagarinskoye"),
        "administrative_location": "Korday district, Zhambyl Oblast, Kazakhstan",
    },
)


def named_gold_reference_catalog():
    rows = []
    for source in SOURCE_GROUPS:
        for name in source["deposit_names"]:
            rows.append({
                "name": name,
                "type": "source_reported_existing_gold_deposit",
                "issuer": source["issuer"],
                "source_url": source["source_url"],
                "source_published_on": source["published_on"],
                "source_claim": source["claim"],
                "administrative_location": source["administrative_location"],
                "verified_wgs84_geometry": None,
                "target_au_score": None,
                "current_licence_status": "unknown",
                "available_for_application": None,
                "is_new_discovery": False,
                "drilling_authorized": False,
                "review_state": "source_name_transcribed_requires_geological_geometry_review",
            })
    return {
        "catalog_version": "kazakhstan-sourced-names-v1",
        "record_count": len(rows),
        "record_meaning": "Referenced names from operator publications; not imported point occurrences",
        "ready_for_map_geocoding": False,
        "records": deepcopy(rows),
    }
