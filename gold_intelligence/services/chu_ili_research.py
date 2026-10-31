"""Source-backed *desktop-study workflow* for Kazakhstan's Chu–Ili / Qonaev area.

A research-priority order is NOT a geological prospectivity ranking.
No licensed coordinates, mineral resource estimates or drill targets are
generated. Pilot extent is operator-defined, not a geological boundary.
"""
from copy import deepcopy

PILOT_ID = "chu_ili_qonaev"
PILOT_ENVELOPE = [74.0, 42.0, 80.0, 46.0]  # west, south, east, north, EPSG:4326

REFERENCE_SOURCES = {
    "zhambyl_gold_guide": "https://www.geokniga.org/bookfiles/geokniga-zhambylskaya-oblast-zoloto-spravochnik.pdf",
    "tau_ken_shokpar": "https://tks.kz/ru/investmentprojects/razvedka-zolota-na-mestorozhdeniyah-shokpar-i-gagarinskoe-v-zhambylskoj-oblasti/",
    "qonaev_geonames": "https://geonames.nga.mil/geon-ags/rest/services/RESEARCH/GIS_OUTPUT/MapServer/0/query?outFields=%2A&where=ufi+%3D+-2342674",
    "chu_ili_range": "https://en.wikipedia.org/wiki/Chu-Ili_Range",
    "official_cadastre": "https://minerals.e-qazyna.kz/ru/contracts-map",
}

# Ordering represents which desk-study workstream to research first, based
# on available public documentation. It is NOT gold prospectivity, tenement
# availability, resource quantity, drilling priority or an investment ranking.
RESEARCH_WORKSTREAMS = (
    {
        "workflow_rank": 1,
        "id": "chu-ili-shokpar-gagarin",
        "name": "Shokpar / Gagarinskoye (Korday district)",
        "evidence_stage": "documented_existing_deposits",
        "reason": "Official project description names gold mineralization and a known exploration project.",
        "source_ids": ["tau_ken_shokpar"],
        "next_action": "Obtain original reports, claim boundary and licence chronology; use as a geological benchmark.",
    },
    {
        "workflow_rank": 2,
        "id": "chu-ili-regional-fields",
        "name": "Chu–Ili belt: Mynaral, Khantau, Kogadyr and Chokpar field references",
        "evidence_stage": "published_regional_metallogeny",
        "reason": "A regional gold reference documents ore fields; the actual mineralized geometries are not georeferenced here.",
        "source_ids": ["zhambyl_gold_guide"],
        "next_action": "Acquire map sheets and original survey records; georeference faults, samples and mineral occurrences.",
    },
    {
        "workflow_rank": 3,
        "id": "northwest-qonaev-kurty-shilibastau",
        "name": "Qonaev / Kurty / Shilibastau user-defined research focus",
        "evidence_stage": "unverified_local_gold_occurrence",
        "reason": "Geographic area of interest only; a specific local gold occurrence is not verified in this pilot.",
        "source_ids": ["qonaev_geonames"],
        "next_action": "Verify bedrock exposure, official geology, archives and cadastral restrictions before defining a target.",
    },
)


def pilot_research_queue():
    priorities = []
    for item in RESEARCH_WORKSTREAMS:
        row = deepcopy(item)
        row.update({
            "sources": {key: REFERENCE_SOURCES[key] for key in row.pop("source_ids")},
            "mineral_prospectivity_score": None,
            "verified_gold_occurrences_imported": None,
            "licence_status": "unknown",
            "proven_drill_target": False,
        })
        priorities.append(row)
    return {
        "pilot_id": PILOT_ID,
        "research_area_bbox_wgs84": PILOT_ENVELOPE[:],
        "research_area_definition": "operator-selected desktop search envelope, NOT an ore belt boundary",
        "ranking_basis": "qualitative research sequence based on source-document readiness, NOT mineral prospectivity",
        "rights_status": "unknown",
        "drilling_authorized": False,
        "ranked_research_workstreams": priorities,
        "evidence_source_cadastre": REFERENCE_SOURCES["official_cadastre"],
    }


def pilot_reference_geojson():
    """Map *orientation* data only: never insert into GoldTarget as ore points."""
    west, south, east, north = PILOT_ENVELOPE
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature", "id": "pilot-research-envelope",
                "geometry": {"type": "Polygon", "coordinates": [
                    [[west, south], [east, south], [east, north], [west, north], [west, south]]
                ]},
                "properties": {
                    "name": "Chu–Ili / Qonaev operator-defined research envelope",
                    "feature_kind": "research_envelope",
                    "source_type": "research_scope_not_geological_evidence",
                    "gold_occurrence_confirmed": False,
                    "licence_status": "unknown",
                },
            },
            {
                "type": "Feature", "id": "orientation-qonaev",
                "geometry": {"type": "Point", "coordinates": [77.06600313, 43.86196303]},
                "properties": {
                    "name": "Qonaev geographic reference (not mineral occurrence)",
                    "feature_kind": "orientation_point",
                    "source_reference": REFERENCE_SOURCES["qonaev_geonames"],
                    "gold_occurrence_confirmed": False,
                },
            },
            {
                "type": "Feature", "id": "orientation-chu-ili",
                "geometry": {"type": "Point", "coordinates": [75.0, 44.0]},
                "properties": {
                    "name": "Chu–Ili range approximate regional anchor (not mineral occurrence)",
                    "feature_kind": "orientation_point",
                    "source_reference": REFERENCE_SOURCES["chu_ili_range"],
                    "gold_occurrence_confirmed": False,
                },
            },
        ],
        "metadata": {
            "pilot_id": PILOT_ID,
            "verified_gold_occurrences_included": 0,
            "licences_verified": 0,
            "is_official_geological_boundary": False,
            "drilling_authorized": False,
            "crs": "EPSG:4326",
        },
    }
