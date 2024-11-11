from flask import Flask, render_template, request, jsonify
import osmnx as ox
import pandas as pd

app = Flask(__name__)

# Загрузка данных по городу и инфраструктуре
def load_city_data(city_name="Kyiv, Ukraine"):
    # Загружаем данные по инфраструктуре и кешируем
    infrastructure_tags = {'school': {'amenity': 'school'},
                           'hospital': {'amenity': 'hospital'},
                           'park': {'leisure': 'park'},
                           'restaurant': {'amenity': 'restaurant'}}
    
    infrastructure_data = {}
    for name, tags in infrastructure_tags.items():
        data = ox.features_from_place(city_name, tags=tags)
        infrastructure_data[name] = pd.DataFrame(data[['name', 'geometry']])
        infrastructure_data[name]['type'] = name
    
    infrastructure_df = pd.concat(infrastructure_data.values(), ignore_index=True)
    
    # Получаем площадь и численность населения города
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
        # Добавьте другие города
    }
    return population_data.get(city_name, 0)

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Эндпоинт рекомендаций
@app.route('/recommend', methods=['POST'])
def recommend():
    category = request.json.get('category')
    feedback = request.json.get('feedback')
    city_name = request.json.get('city', 'Kyiv, Ukraine')
    
    # Загрузка данных города
    city_data, city_area_km2, population = load_city_data(city_name)
    
    # Определяем требуемое количество объектов с учетом плотности населения и площади
    min_objects_per_100k = 5
    min_required_objects = int((population / 100000) * min_objects_per_100k)
    
    # Фильтруем данные по категории
    filtered_data = city_data[city_data['type'] == category].dropna(subset=["name"])
    
    locations = [
        {
            "name": row["name"] if pd.notna(row["name"]) else "Unnamed Location",
            "lat": row["geometry"].centroid.y if pd.notna(row["geometry"].centroid.y) else None,
            "lon": row["geometry"].centroid.x if pd.notna(row["geometry"].centroid.x) else None,
        }
        for _, row in filtered_data.iterrows()
    ]
    
    # Проверка на количество объектов
    current_object_count = len(filtered_data)
    if current_object_count < min_required_objects:
        additional_objects_needed = min_required_objects - current_object_count
        recommendation = (
            f"Недостаточно объектов категории '{category}'. "
            f"Рекомендуется добавить ещё {additional_objects_needed} объектов."
        )
    else:
        recommendation = f"В категории '{category}' достаточно объектов."
    
    recommendation += f" Найдено {current_object_count} объектов."
    
    # Обработка обратной связи
    if feedback == "подтвердить":
        recommendation += " Спасибо за подтверждение."
    elif feedback == "отклонить":
        recommendation += " Мы учтем ваш отзыв."
    
    return jsonify({"recommendation": recommendation, "locations": locations})

if __name__ == '__main__':
    app.run(debug=True)
