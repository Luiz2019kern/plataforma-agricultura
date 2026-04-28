import folium

def add_ee_layer(folium_map, ee_image, vis_params, name):
    map_id = ee_image.getMapId(vis_params)

    folium.raster_layers.TileLayer(
        tiles=map_id["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True
    ).add_to(folium_map)


def add_boundary(folium_map, gdf, name="Limite do talhão"):
    folium.GeoJson(
        gdf,
        name=name,
        style_function=lambda x: {
            "color": "blue",
            "weight": 2,
            "fillOpacity": 0
        }
    ).add_to(folium_map)