from flask import Flask, render_template, request, jsonify
import osmnx as ox
import pandas as pd
import geonamescache
from geopy.geocoders import Nominatim

app = Flask(__name__)

def load_city_data(city_name="Lviv, Ukraine"):
    infrastructure_tags = {
        'school': {'amenity': 'school'},
        'hospital': {'amenity': 'hospital'},
        'park': {'leisure': 'park'},
        'restaurant': {'amenity': 'restaurant'},
        'pharmacy': {'amenity': 'pharmacy'},
        'gym': {'leisure': 'fitness_centre'},
        'library': {'amenity': 'library'},
        'mall': {'shop': 'mall'}
    }

    infrastructure_data = {}
    for name, tags in infrastructure_tags.items():
        data = ox.features_from_place(city_name, tags=tags)
        infrastructure_data[name] = pd.DataFrame(data[['name', 'geometry']])
        infrastructure_data[name]['type'] = name

    infrastructure_df = pd.concat(infrastructure_data.values(), ignore_index=True)

    # Получаем границы города и преобразуем геометрию в метры (EPSG:3395)
    city_boundary = ox.geocode_to_gdf(city_name)
    if not city_boundary.empty:
        city_boundary = city_boundary.to_crs(epsg=3395)  # Преобразуем в проекцию с метрами
        city_area_km2 = city_boundary.geometry.area[0] / 1e6  # Площадь в квадратных километрах
    else:
        city_area_km2 = 0  # Если не удалось получить границы, ставим 0

    # Заглушка для площади (например, для Киева)
    if city_area_km2 == 0:
        city_area_km2 = 850  # Площадь Киева в км²

    population = get_real_city_population(city_name)

    return infrastructure_df, city_area_km2, population

def get_real_city_population(city_name):
    """Fetch real population data using geonamescache or another API."""
    gc = geonamescache.GeonamesCache()
    cities = gc.get_cities()
    
    # Find population data for the city
    city_info = next(
        (city for city in cities.values() if city['name'] == city_name.split(',')[0]), None
    )
    if city_info:
        return city_info.get('population', 0)
    else:
        # Default or fallback if city is not in cache (API or default value)
        return 2804000  # Placeholder for Kyiv or implement API fallback

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    category = request.json.get('category')
    feedback = request.json.get('feedback')
    city_name = request.json.get('city', 'Kyiv, Ukraine')

    city_data, city_area_km2, population = load_city_data(city_name)

    min_objects_per_100k = 5
    min_required_objects = int((population / 100000) * min_objects_per_100k)

    filtered_data = city_data[city_data['type'] == category].dropna(subset=["name"])

    locations = [
        {
            "name": row["name"] if pd.notna(row["name"]) else "Невідома локація",
            "lat": row["geometry"].centroid.y if pd.notna(row["geometry"].centroid.y) else None,
            "lon": row["geometry"].centroid.x if pd.notna(row["geometry"].centroid.x) else None,
        }
        for _, row in filtered_data.iterrows()
    ]

    current_object_count = len(filtered_data)
    if current_object_count < min_required_objects:
        additional_objects_needed = min_required_objects - current_object_count
        recommendation = (
            f"Недостатньо об'єктів категорії '{category}'. "
            f"Рекомендується додати ще {additional_objects_needed} об'єктів."
        )
    else:
        recommendation = f"У категорії '{category}' достатньо об'єктів."

    recommendation += f" Знайдено {current_object_count} об'єктів."

    if feedback == "підтвердити":
        recommendation += " Дякуємо за підтвердження."
    elif feedback == "відхилити":
        recommendation += " Ми врахуємо ваш відгук."

    return jsonify({"recommendation": recommendation, "locations": locations})

@app.route('/analytics', methods=['POST'])
def analytics():
    city_name = request.json.get('city', 'Kyiv, Ukraine')
    city_data, city_area_km2, population = load_city_data(city_name)
    
    norms_per_100k = {
        'school': 7,
        'hospital': 1.5,
        'park': 5.5,
        'restaurant': 17,
        'pharmacy': 7,
        'gym': 2.5,
        'library': 1.5,
        'mall': 1.5,
    }
    
    analytics_data = {}
    for category, norm in norms_per_100k.items():
        count = len(city_data[city_data['type'] == category])
        per_capita = (count / population) * 100000  # Facilities per 100,000 people
        analytics_data[category] = {
            "count": count,
            "per_capita": round(per_capita, 2),
            "norm_per_100k": norm
        }
    
    return jsonify({
        "population": population,
        "area_km2": city_area_km2,
        "analytics": analytics_data
    })

if __name__ == '__main__':
    app.run(debug=True)
