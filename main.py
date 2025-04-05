import folium
import openrouteservice as ors
import requests
from geopy.geocoders import Nominatim
from folium.plugins import MarkerCluster
from IPython.display import display
from shapely.geometry import LineString, Point
import numpy as np

# ====================== CONFIGURAÇÕES ======================
ORS_API_KEY = "5b3ce3597851110001cf62486c7c8af74cf646be838f6fc698c67fa8"

# Agora você pode modificar aqui:
ORIGIN = "Fortaleza, Ceará, Brasil"     # Origem como texto
DESTINATION = "Parauapebas, Pará, Brasil" # Destino como texto

MAX_DISTANCE_KM = 5  # Distância máxima dos postos à rota
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
    """Converte nome da cidade para coordenadas (lon, lat)."""
    geolocator = Nominatim(user_agent="truck_route_planner")
    location = geolocator.geocode(location_name)
    if location:
        return (location.longitude, location.latitude)
    raise ValueError(f"Localização não encontrada: {location_name}")

def calculate_route(client, start, end):
    """Calcula a rota considerando restrições de caminhão pesado."""
    try:
        return client.directions(
            coordinates=[start, end],
            profile=VEHICLE_PARAMS['profile'],
            format='geojson',
            extra_params={k: v for k, v in VEHICLE_PARAMS.items() if k != 'profile'}
        )
    except ors.exceptions.ApiError as e:
        raise Exception(f"Erro ORS: {str(e)}")

def fetch_fuel_stations(bbox):
    """Consulta postos de combustível via Overpass API."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["amenity"="fuel"]({bbox});
      way["amenity"="fuel"]({bbox});
      relation["amenity"="fuel"]({bbox});
    );
    out center;
    """
    response = requests.get(overpass_url, params={'data': query}, timeout=60)
    return response.json()

def filter_nearby_stations(route_coords, stations_data):
    """Filtra apenas os postos dentro do raio de 5 km da rota."""
    route_line = LineString(route_coords).simplify(SIMPLIFY_TOLERANCE)
    buffer_zone = route_line.buffer(MAX_DISTANCE_KM / 111)  # Aproximadamente graus

    valid_stations = []
    for station in stations_data['elements']:
        try:
            coords = (
                station['lon'] if 'lon' in station else station['center']['lon'],
                station['lat'] if 'lat' in station else station['center']['lat']
            )
            point = Point(coords)

            if buffer_zone.contains(point):
                distance_km = point.distance(route_line) * 111
                if distance_km <= MAX_DISTANCE_KM:
                    station['distance_km'] = round(distance_km, 2)
                    valid_stations.append(station)

        except Exception as e:
            print(f"Erro no posto {station.get('id')}: {str(e)}")

    return {'elements': valid_stations}

def create_route_map(route_geojson, start, end, stations):
    """Cria o mapa com a rota e os postos."""
    coords = route_geojson['features'][0]['geometry']['coordinates']
    center = np.mean(coords, axis=0)[::-1]  # (lat, lon)

    m = folium.Map(location=center, zoom_start=7, tiles='OpenStreetMap')

    # Rota
    folium.GeoJson(
        route_geojson,
        name='Rota do Caminhão',
        style_function=lambda x: {'color': '#1E90FF', 'weight': 5}
    ).add_to(m)

    # Postos
    cluster = MarkerCluster(name=f"Postos (≤{MAX_DISTANCE_KM} km)").add_to(m)

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
        ).add_to(cluster)

    # Origem e destino
    folium.Marker(
        location=start[::-1],
        icon=folium.Icon(color='red', icon='truck', prefix='fa'),
        popup='<b>ORIGEM</b>'
    ).add_to(m)

    folium.Marker(
        location=end[::-1],
        icon=folium.Icon(color='blue', icon='flag-checkered', prefix='fa'),
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

        print("⛽ Buscando postos próximos à rota...")
        bbox = f"{min(c[1] for c in route_coords)},{min(c[0] for c in route_coords)},{max(c[1] for c in route_coords)},{max(c[0] for c in route_coords)}"
        stations = fetch_fuel_stations(bbox)
        nearby_stations = filter_nearby_stations(route_coords, stations)
        print(f"✅ {len(nearby_stations['elements'])} postos encontrados dentro de {MAX_DISTANCE_KM} km")

        print("🗺️ Gerando mapa interativo...")
        display(create_route_map(route, start_point, end_point, nearby_stations))

    except Exception as e:
        print(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    main()