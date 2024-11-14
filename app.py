from flask import Flask, render_template, request, jsonify
import osmnx as ox
import pandas as pd

app = Flask(__name__)

def load_city_data(city_name="Kyiv, Ukraine"):
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
    
    city_boundary = ox.geocode_to_gdf(city_name)
    city_area_km2 = city_boundary.geometry.area[0] / 1e6
    population = get_city_population(city_name)
    
    return infrastructure_df, city_area_km2, population


def get_city_population(city_name):
    population_data = {
        "Kyiv, Ukraine": 2804000,
        "Lviv, Ukraine": 721301,
        "Odesa, Ukraine": 1019301,
        "Dnipro, Ukraine": 993000,
        "Kharkiv, Ukraine": 1443200,
        "Zaporizhzhia, Ukraine": 360000,
    }
    return population_data.get(city_name, 0)

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

if __name__ == '__main__':
    app.run(debug=True)
