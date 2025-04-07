import folium
import openrouteservice as ors
import requests
from geopy.geocoders import Nominatim
from folium.plugins import MarkerCluster
from shapely.geometry import LineString, Point
import numpy as np
import webbrowser

# ====================== CONFIGURAÇÕES ======================
ORS_API_KEY = "SUA_CHAVE"

# Agora você pode modificar aqui:
ORIGIN = "Fortaleza, Ceará, Brasil"     # Origem como texto
DESTINATION = "Parauapebas, Pará, Brasil" # Destino como texto

MAX_DISTANCE_KM = 1  # Distância máxima dos pontos de interesse à rota
SIMPLIFY_TOLERANCE = 0.01  # Tolerância para simplificar rota

VEHICLE_PARAMS = {
    'profile': 'driving-hgv',
    'vehicle_type': 'truck',
    'weight': 120,
    'height': 4.3,
    'width': 5,
    'length': 70,
    'avoid_features': ['tollways', 'ferries', 'unpaved', 'tunnels']
}

# ====================== FUNÇÕES ======================
def get_coordinates(location_name):
    geolocator = Nominatim(user_agent="truck_route_planner")
    location = geolocator.geocode(location_name)
    if location:
        return (location.longitude, location.latitude)
    raise ValueError(f"Localização não encontrada: {location_name}")

def calculate_route(client, start, end):
    try:
        return client.directions(
            coordinates=[start, end],
            profile=VEHICLE_PARAMS['profile'],
            format='geojson',
            extra_params={k: v for k, v in VEHICLE_PARAMS.items() if k != 'profile'}
        )
    except ors.exceptions.ApiError as e:
        raise Exception(f"Erro ORS: {str(e)}")

def fetch_places(bbox, amenity):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["amenity"="{amenity}"]({bbox});
      way["amenity"="{amenity}"]({bbox});
      relation["amenity"="{amenity}"]({bbox});
    );
    out center;
    """
    response = requests.get(overpass_url, params={'data': query}, timeout=60)
    return response.json()

def filter_nearby_places(route_coords, places_data):
    route_line = LineString(route_coords).simplify(SIMPLIFY_TOLERANCE)
    buffer_zone = route_line.buffer(MAX_DISTANCE_KM / 111)

    valid_places = []
    for place in places_data['elements']:
        try:
            coords = (
                place['lon'] if 'lon' in place else place['center']['lon'],
                place['lat'] if 'lat' in place else place['center']['lat']
            )
            point = Point(coords)

            if buffer_zone.contains(point):
                distance_km = point.distance(route_line) * 111
                if distance_km <= MAX_DISTANCE_KM:
                    place['distance_km'] = round(distance_km, 2)
                    valid_places.append(place)

        except Exception as e:
            print(f"Erro no local {place.get('id')}: {str(e)}")

    return {'elements': valid_places}

def create_route_map(route_geojson, start, end, stations, rest_places):
    coords = route_geojson['features'][0]['geometry']['coordinates']
    center = np.mean(coords, axis=0)[::-1]

    m = folium.Map(location=center, zoom_start=7, tiles='OpenStreetMap')

    folium.GeoJson(
        route_geojson,
        name='Rota do Caminhão',
        style_function=lambda x: {'color': '#1E90FF', 'weight': 5}
    ).add_to(m)

    fuel_cluster = MarkerCluster(name=f"Postos (≤{MAX_DISTANCE_KM} km)").add_to(m)
    for station in stations['elements']:
        coords = (
            station.get('lon') or station['center']['lon'],
            station.get('lat') or station['center']['lat']
        )

        folium.Marker(
            location=coords[::-1],
            popup=f"""
            <b>{station.get('tags', {}).get('name', 'Posto')}</b><br>
            <b>Marca:</b> {station.get('tags', {}).get('brand', 'Desconhecida')}<br>
            <b>Distância:</b> {station['distance_km']} km
            """,
            icon=folium.Icon(
                color='green' if station['distance_km'] <= 2 else 'orange',
                icon='gas-pump',
                prefix='fa'
            )
        ).add_to(fuel_cluster)

    rest_cluster = MarkerCluster(name=f"Descanso/Alimentação (≤{MAX_DISTANCE_KM} km)").add_to(m)
    for place in rest_places['elements']:
        coords = (
            place.get('lon') or place['center']['lon'],
            place.get('lat') or place['center']['lat']
        )
        
        place_type = place.get('tags', {}).get('amenity', '')
        if place_type == 'restaurant':
            icon_color = 'red'
            icon_type = 'cutlery'
        elif place_type == 'hotel':
            icon_color = 'purple'
            icon_type = 'bed'
        else:
            icon_color = 'blue'
            icon_type = 'info-sign'
        
        folium.Marker(
            location=coords[::-1],
            popup=f"""
            <b>{place.get('tags', {}).get('name', 'Local de Descanso')}</b><br>
            <b>Tipo:</b> {place_type}<br>
            <b>Distância:</b> {place['distance_km']} km
            """,
            icon=folium.Icon(
                color=icon_color,
                icon=icon_type,
                prefix='fa'
            )
        ).add_to(rest_cluster)

    folium.Marker(
        location=start[::-1],
        icon=folium.Icon(color='black', icon='truck', prefix='fa'),
        popup='<b>ORIGEM</b>'
    ).add_to(m)

    folium.Marker(
        location=end[::-1],
        icon=folium.Icon(color='darkblue', icon='flag-checkered', prefix='fa'),
        popup='<b>DESTINO</b>'
    ).add_to(m)

    folium.LayerControl().add_to(m)
    folium.plugins.Fullscreen(position='topright').add_to(m)
    folium.plugins.MeasureControl(position='bottomleft').add_to(m)

    return m

# ====================== EXECUÇÃO ======================
def main():
    print("🛢️ Iniciando planejamento de rota para caminhão pesado...")

    try:
        client = ors.Client(key=ORS_API_KEY)

        start_point = get_coordinates(ORIGIN)
        end_point = get_coordinates(DESTINATION)
        print(f"📍 Rota: {ORIGIN.split(',')[0]} → {DESTINATION.split(',')[0]}")

        print("🛣️ Calculando melhor rota para o veículo...")
        route = calculate_route(client, start_point, end_point)
        route_coords = [(lon, lat) for lon, lat in route['features'][0]['geometry']['coordinates']]

        print("⛽ Buscando postos de combustível próximos à rota...")
        bbox = f"{min(c[1] for c in route_coords)},{min(c[0] for c in route_coords)},{max(c[1] for c in route_coords)},{max(c[0] for c in route_coords)}"
        
        stations = fetch_places(bbox, "fuel")
        nearby_stations = filter_nearby_places(route_coords, stations)
        print(f"✅ {len(nearby_stations['elements'])} postos encontrados dentro de {MAX_DISTANCE_KM} km")

        print("🛏️ Buscando locais de descanso e alimentação...")
        rest_places = {'elements': []}
        for amenity in ['restaurant', 'hotel', 'motel', 'cafe']:
            places = fetch_places(bbox, amenity)
            filtered = filter_nearby_places(route_coords, places)
            rest_places['elements'].extend(filtered['elements'])
        print(f"✅ {len(rest_places['elements'])} locais de descanso/alimentação encontrados")

        print("🗺️ Gerando mapa interativo...")
        mapa = create_route_map(route, start_point, end_point, nearby_stations, rest_places)
        mapa.save("mapa_interativo.html")
        print("✅ Mapa salvo como 'mapa_interativo.html'. Abrindo no navegador...")
        webbrowser.open("mapa_interativo.html")

    except Exception as e:
        print(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    main()
