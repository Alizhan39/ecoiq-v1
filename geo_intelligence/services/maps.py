"""
geo_intelligence/services/maps.py — builds the Kazakhstan Geo Intelligence
Folium map: one interactive Leaflet map with a toggleable FeatureGroup per
intelligence layer (Companies/Assets, Climate Risk, Investment Opportunities).
Rendered server-side to static HTML and embedded directly in the page —
no client-side map JS to maintain beyond what Folium already generates.
"""
import folium

from geo_intelligence.services.spatial import cluster_bounding_box

KAZAKHSTAN_CENTRE = (48.0, 68.0)
DEFAULT_ZOOM = 5

SEVERITY_COLORS = {'low': '#58a6ff', 'medium': '#f4a261', 'high': '#e63946'}
PRIORITY_COLORS = {'not_assessed': '#94a3b8', 'low': '#58a6ff', 'medium': '#f4a261', 'high': '#e63946'}
ASSET_ICON_COLORS = {
    'city': 'lightgray', 'company_office': 'blue', 'factory': 'darkred', 'power_plant': 'orange',
    'cold_store': 'cadetblue', 'heating_unit': 'red', 'stewardship_site': 'green', 'other': 'gray',
}


_DEMO_BADGE = '<span style="color:#f4a261;font-weight:700;">DEMO DATA</span>'


def _asset_popup_html(asset):
    priority_color = PRIORITY_COLORS.get(asset['modernisation_priority'], '#94a3b8')
    exposure = asset['climate_exposure_score']
    lines = [
        '<div style="font-family:-apple-system,sans-serif;min-width:200px;">',
        f'<strong>{asset["name"]}</strong><br>',
        f'<span style="color:#64748b;">{asset["asset_type_display"]}</span><br>',
    ]
    if asset['region']:
        lines.append(f'Region: {asset["region"]}<br>')
    if asset['sector']:
        lines.append(f'Sector: {asset["sector"]}<br>')
    lines.append(
        f'Modernisation priority: <span style="color:{priority_color};font-weight:700;">'
        f'{asset["modernisation_priority_display"]}</span><br>',
    )
    if exposure is not None:
        lines.append(f'Climate exposure: {exposure:.0f}/100<br>')
    else:
        lines.append('Climate exposure: not yet measured<br>')
    if asset['is_demo']:
        lines.append(_DEMO_BADGE)
    lines.append('</div>')
    return ''.join(lines)


def _risk_zone_popup_html(zone):
    color = SEVERITY_COLORS.get(zone['severity'], '#94a3b8')
    confidence = zone['confidence']
    lines = [
        '<div style="font-family:-apple-system,sans-serif;min-width:200px;">',
        f'<strong>{zone["name"]}</strong><br>',
        f'<span style="color:{color};font-weight:700;">{zone["risk_type_display"]} — {zone["severity_display"]}</span><br>',
    ]
    if confidence is not None:
        lines.append(f'Confidence: {confidence:.0f}%<br>')
    lines.append(f'Source: {zone["source"] or "—"}<br>')
    if zone['is_demo']:
        lines.append(_DEMO_BADGE)
    lines.append('</div>')
    return ''.join(lines)


def _opportunity_popup_html(opp):
    score = opp['investment_score']
    lines = [
        '<div style="font-family:-apple-system,sans-serif;min-width:220px;">',
        f'<strong>{opp["title"]}</strong><br>',
        f'<span style="color:#64748b;">{opp["opportunity_type_display"]}</span><br>',
    ]
    if opp['estimated_impact']:
        lines.append(f'Estimated impact: {opp["estimated_impact"]}<br>')
    if score is not None:
        lines.append(f'Investment score: {score:.0f}/100<br>')
    else:
        lines.append('Investment score: not yet measured<br>')
    lines.append(f'Risk level: {opp["risk_level_display"]}<br>')
    if opp['recommended_action']:
        lines.append(f'Recommended action: {opp["recommended_action"]}<br>')
    if opp['is_demo']:
        lines.append(_DEMO_BADGE)
    lines.append('</div>')
    return ''.join(lines)


def build_kazakhstan_geo_map(assets, risk_zones, opportunities):
    """
    assets/risk_zones/opportunities: lists of plain dicts (already filtered
    by the view). Returns the map's HTML `<div>`+`<script>` fragment ready
    to embed directly in a template (Folium's `_repr_html_()` output), plus
    a bounding-box-fitted initial view when there is anything to plot.
    """
    all_points = (
        [{'latitude': a['latitude'], 'longitude': a['longitude']} for a in assets]
        + [{'latitude': z['latitude'], 'longitude': z['longitude']} for z in risk_zones]
        + [{'latitude': o['latitude'], 'longitude': o['longitude']} for o in opportunities]
    )
    bbox = cluster_bounding_box(all_points)

    fmap = folium.Map(location=KAZAKHSTAN_CENTRE, zoom_start=DEFAULT_ZOOM, tiles='CartoDB dark_matter')

    assets_layer = folium.FeatureGroup(name='Companies & Assets', show=True)
    for asset in assets:
        folium.Marker(
            location=[asset['latitude'], asset['longitude']],
            popup=folium.Popup(_asset_popup_html(asset), max_width=280),
            tooltip=asset['name'],
            icon=folium.Icon(color=ASSET_ICON_COLORS.get(asset['asset_type'], 'gray'), icon='building', prefix='fa'),
        ).add_to(assets_layer)
    assets_layer.add_to(fmap)

    risk_layer = folium.FeatureGroup(name='Climate Risk Zones', show=True)
    for zone in risk_zones:
        color = SEVERITY_COLORS.get(zone['severity'], '#94a3b8')
        folium.Circle(
            location=[zone['latitude'], zone['longitude']],
            radius=zone['radius_km'] * 1000,
            color=color, fill=True, fill_color=color, fill_opacity=0.18, weight=2,
            popup=folium.Popup(_risk_zone_popup_html(zone), max_width=280),
            tooltip=zone['name'],
        ).add_to(risk_layer)
    risk_layer.add_to(fmap)

    opportunity_layer = folium.FeatureGroup(name='Investment Opportunities', show=True)
    for opp in opportunities:
        folium.Marker(
            location=[opp['latitude'], opp['longitude']],
            popup=folium.Popup(_opportunity_popup_html(opp), max_width=280),
            tooltip=opp['title'],
            icon=folium.Icon(color='green', icon='chart-line', prefix='fa'),
        ).add_to(opportunity_layer)
    opportunity_layer.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)

    if bbox:
        fmap.fit_bounds([[bbox['min_lat'], bbox['min_lon']], [bbox['max_lat'], bbox['max_lon']]])

    # `_repr_html_()` is built for Jupyter (it prints a "Trust Notebook" notice
    # inside the iframe) — not appropriate on a real page. `get_root().render()`
    # gives the complete standalone document instead, which we embed in our
    # own plain iframe.
    document_html = fmap.get_root().render()
    escaped = document_html.replace('"', '&quot;')
    return (
        f'<iframe srcdoc="{escaped}" style="width:100%;height:100%;border:none;" '
        f'title="EcoIQ Kazakhstan Geo Intelligence map"></iframe>'
    )
