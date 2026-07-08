"""
geo_intelligence/services/spatial.py — GeoPandas/Shapely spatial analysis.

Every function takes plain lat/lng (EPSG:4326, the GPS coordinate system)
and reprojects into a per-query Azimuthal Equidistant CRS centred on the
reference point before measuring distances or building buffers, rather
than a fixed global projection like Web Mercator. Web Mercator distorts
distance more the further a point sits from the equator, and was tried
first here — it overestimated real-world Almaty-to-Astana distance by
~49% (1437km computed vs the true ~965km). An Azimuthal Equidistant CRS
centred on the reference point is, by construction, exact for distance
measured *from that centre* at any latitude, which is exactly the shape
of every query below (distance from a point, or containment within a
radius of a point) — so it fixes the error without adding a dependency,
since pyproj already ships with GeoPandas.
"""
import geopandas as gpd
import pandas as pd
from pyproj import CRS
from shapely.geometry import Point

WGS84 = 'EPSG:4326'


def _azimuthal_equidistant_crs(lat, lon):
    return CRS.from_proj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs')


def _to_gdf(rows, crs=WGS84):
    df = pd.DataFrame(rows)
    if df.empty:
        return gpd.GeoDataFrame(df, geometry=[], crs=crs)
    geometry = [Point(lon, lat) for lat, lon in zip(df['latitude'], df['longitude'])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs=WGS84 if crs == WGS84 else crs)


def distance_km(lat1, lon1, lat2, lon2):
    """Geodesically exact distance between two points, in kilometres."""
    local_crs = _azimuthal_equidistant_crs(lat1, lon1)
    gdf = _to_gdf([{'latitude': lat1, 'longitude': lon1}, {'latitude': lat2, 'longitude': lon2}]).to_crs(local_crs)
    meters = gdf.geometry.iloc[0].distance(gdf.geometry.iloc[1])
    return round(meters / 1000.0, 2)


def nearest_row(lat, lon, candidate_rows):
    """
    candidate_rows: list of dicts with 'latitude'/'longitude' (any extra keys
    are returned unchanged). Returns (nearest_row, distance_km) or (None, None)
    if candidate_rows is empty.
    """
    if not candidate_rows:
        return None, None
    local_crs = _azimuthal_equidistant_crs(lat, lon)
    origin_proj = _to_gdf([{'latitude': lat, 'longitude': lon}]).to_crs(local_crs).geometry.iloc[0]

    candidates_gdf = _to_gdf(candidate_rows).to_crs(local_crs)
    distances = candidates_gdf.geometry.distance(origin_proj)
    best_idx = distances.idxmin()
    best_row = candidate_rows[best_idx]
    return best_row, round(distances.loc[best_idx] / 1000.0, 2)


def assets_within_risk_zone(risk_zone, asset_rows):
    """
    risk_zone: dict with 'latitude', 'longitude', 'radius_km'.
    asset_rows: list of dicts with 'latitude'/'longitude' (plus any other keys).
    Returns the subset of asset_rows whose point falls inside a Shapely
    buffer of radius_km around the risk zone's centre — a real spatial
    predicate (buffer + within), exact at the zone's own centre regardless
    of latitude, not a bounding-box approximation.
    """
    if not asset_rows:
        return []
    local_crs = _azimuthal_equidistant_crs(risk_zone['latitude'], risk_zone['longitude'])
    centre_proj = _to_gdf(
        [{'latitude': risk_zone['latitude'], 'longitude': risk_zone['longitude']}],
    ).to_crs(local_crs).geometry.iloc[0]
    buffer_geom = centre_proj.buffer(risk_zone['radius_km'] * 1000.0)

    assets_gdf = _to_gdf(asset_rows).to_crs(local_crs)
    inside_mask = assets_gdf.geometry.within(buffer_geom)
    return [row for row, inside in zip(asset_rows, inside_mask) if inside]


def cluster_bounding_box(rows):
    """
    rows: list of dicts with 'latitude'/'longitude'. Returns the WGS84
    bounding box (min_lat, min_lon, max_lat, max_lon) covering every point,
    used to auto-fit the Folium map's initial view to whatever is plotted.
    """
    if not rows:
        return None
    lats = [r['latitude'] for r in rows]
    lons = [r['longitude'] for r in rows]
    return {'min_lat': min(lats), 'min_lon': min(lons), 'max_lat': max(lats), 'max_lon': max(lons)}
