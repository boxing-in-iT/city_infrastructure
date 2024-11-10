from flask import Flask, render_template, request, jsonify
import osmnx as ox
import pandas as pd

app = Flask(__name__)

# Load city infrastructure data
def load_city_data(city_name="Kyiv, Ukraine"):
    # Загружаем данные по инфраструктуре
    schools = ox.features_from_place(city_name, tags={'amenity': 'school'})
    hospitals = ox.features_from_place(city_name, tags={'amenity': 'hospital'})
    
    # Создаем DataFrame
    schools_df = pd.DataFrame(schools[['name', 'geometry']])
    hospitals_df = pd.DataFrame(hospitals[['name', 'geometry']])
    schools_df['type'] = 'school'
    hospitals_df['type'] = 'hospital'
    
    # Объединяем в один DataFrame
    infrastructure_df = pd.concat([schools_df, hospitals_df], ignore_index=True)
    
    # Получаем площадь города
    city_boundary = ox.geocode_to_gdf(city_name)
    city_area_km2 = city_boundary.geometry.area[0] / 1e6  # Перевод из м² в км²
    
    return infrastructure_df, city_area_km2

# Load city data and area at startup
city_data, city_area_km2 = load_city_data()

# Main page
@app.route('/')
def index():
    return render_template('index.html')

# Recommendation endpoint
@app.route('/recommend', methods=['POST'])
def recommend():
    category = request.json.get('category')
    feedback = request.json.get('feedback')
    
    # Устанавливаем порог на основе площади города
    min_objects_per_km2 = 0.5  # Минимум 0.5 объектов на км²
    min_required_objects = int(city_area_km2 * min_objects_per_km2)
    
    # Фильтруем данные по выбранной категории
    filtered_data = city_data[city_data['type'] == category].dropna(subset=["name"])
    
    # Извлекаем информацию для отображения и обрабатываем NaN значения
    locations = [
        {
            "name": row["name"] if pd.notna(row["name"]) else "Unnamed Location",
            "lat": row["geometry"].centroid.y if pd.notna(row["geometry"].centroid.y) else None,
            "lon": row["geometry"].centroid.x if pd.notna(row["geometry"].centroid.x) else None,
        }
        for _, row in filtered_data.iterrows()
    ]
    
    # Проверяем, достаточно ли объектов
    recommendation = (
        f"Недостаточно объектов категории {category}. Рекомендуется добавить."
        if len(filtered_data) < min_required_objects
        else f"В категории {category} достаточно объектов."
    )
    
    # Обработка обратной связи
    if feedback == "подтвердить":
        recommendation += " Спасибо за подтверждение."
    elif feedback == "отклонить":
        recommendation += " Мы учтем ваш отзыв и улучшим рекомендацию."
    
    return jsonify({"recommendation": recommendation, "locations": locations})

if __name__ == '__main__':
    app.run(debug=True)
