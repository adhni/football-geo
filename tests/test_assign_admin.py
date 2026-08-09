import geopandas as gpd
from shapely.geometry import Polygon

from src.ftg.assign_admin import normalize_boundaries


def test_normalize_geoboundaries_columns():
    source = gpd.GeoDataFrame(
        {
            "shapeID": ["ITA-1"],
            "shapeName": ["Tuscany"],
            "shapeGroup": ["ITA"],
        },
        geometry=[Polygon([(9, 42), (12, 42), (12, 44), (9, 44)])],
        crs="EPSG:4326",
    )
    output = normalize_boundaries(source, "adm1")
    assert output.loc[0, "adm0_code"] == "ITA"
    assert output.loc[0, "adm1_code"] == "ITA-1"
    assert output.loc[0, "adm1_name"] == "Tuscany"
