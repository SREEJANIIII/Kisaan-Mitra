import requests
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
import os # Kept for potential future API key usage, although Open-Meteo is keyless

# --- Utility Functions (Adapted from soil.py and weather.py) ---

def interpret_weather_code(code: int) -> str:
    """Convert WMO weather code to human-readable condition."""
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
        55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(code, "Unknown")

def get_climate_zone(lat, temp, precip) -> str:
    """Simple climate classification based on location, temp, and precipitation."""
    
    # 1. Determine general latitude band
    if abs(lat) <= 23.5:  # Tropical Zone
        zone_prefix = 'tropical'
    elif abs(lat) <= 35:  # Subtropical Zone
        zone_prefix = 'subtropical'
    elif abs(lat) <= 66:  # Temperate Zone
        zone_prefix = 'temperate'
    else:  # Polar Zone
        return 'polar'
    
    # 2. Refine based on weather data (using simple thresholds)
    if zone_prefix == 'tropical':
        if temp > 25 and precip > 60:
            return 'tropical rainforest'
        elif temp > 25:
            return 'tropical savanna'
    elif zone_prefix == 'subtropical':
        if precip > 20:
            return 'subtropical monsoon'
    
    return zone_prefix # Fallback to general zone


def predict_soil_characteristics(lat, climate_zone) -> Dict:
    """Predict soil characteristics and suitable crops based on location and climate."""
    climate_zone_lower = climate_zone.lower()
    
    if abs(lat) <= 23.5:  # Tropical zone
        if 'rainforest' in climate_zone_lower or 'monsoon' in climate_zone_lower:
            return {
                'type': 'Lateritic Soil',
                'fertility': 'Medium (prone to leaching)',
                'erosion': 'High',
                'crops': ['Rice', 'Tropical Fruits', 'Coffee', 'Rubber'],
                'notes': 'Rich in iron oxides; needs careful erosion control and organic matter.'
            }
        else:  # Tropical savanna
            return {
                'type': 'Red and Yellow Soil',
                'fertility': 'Medium',
                'erosion': 'Medium to High',
                'crops': ['Maize', 'Millet', 'Cotton', 'Pulses'],
                'notes': 'Seasonal rainfall dependent; deep ploughing helps water retention.'
            }
    elif abs(lat) <= 35:  # Subtropical zone (Mediterranean/Humid)
        return {
            'type': 'Subtropical Loam/Alluvial Soil',
            'fertility': 'High',
            'erosion': 'Low to Medium',
            'crops': ['Citrus fruits', 'Wheat', 'Vegetables', 'Olives', 'Grapes'],
            'notes': 'Very versatile soil; careful water management is key, especially during dry spells.'
        }
    elif abs(lat) <= 66:  # Temperate zone
        return {
            'type': 'Brown Earth/Forest Soil',
            'fertility': 'High',
            'erosion': 'Low',
            'crops': ['Wheat', 'Corn', 'Soybeans', 'Root crops', 'Barley'],
            'notes': 'Well-suited for extensive farming; lime may be needed to adjust pH.'
        }
    else:  # Polar/Subpolar zone
        return {
            'type': 'Tundra Soil',
            'fertility': 'Low',
            'erosion': 'Medium',
            'crops': ['Hardy vegetables (e.g., kale)', 'Short-season berries'],
            'notes': 'Limited growing season; focus on raised beds and protecting from permafrost.'
        }

# --- Main Agent Class ---

class AgriAgent:
    """A combined agent for fetching location, weather, soil, and generating agricultural advice."""
    
    def __init__(self):
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
    
    def get_coordinates(self, location: str) -> Optional[Tuple[float, float, str]]:
        """Geocode location and return coordinates and formatted name."""
        try:
            params = {
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            
            response = requests.get(self.geocoding_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                lat = result["latitude"]
                lon = result["longitude"]
                name = result["name"]
                country = result.get("country", "")
                admin1 = result.get("admin1", "")
                
                full_name = f"{name}"
                if admin1:
                    full_name += f", {admin1}"
                if country:
                    full_name += f", {country}"
                
                return (lat, lon, full_name)
            else:
                return None
                
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
    
    def fetch_combined_data(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Fetch detailed weather data (current + daily for climate)
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,precipitation_sum", # Used for climate classification
                "hourly": "precipitation_probability",
                "timezone": "auto",
                "forecast_days": 1 # Only need current and one day daily summary
            }
            
            response = requests.get(self.weather_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Weather API error: {e}")
            return None
            
    def generate_advice(self, weather: Dict, soil: Dict) -> str:
        """
        Generate comprehensive advice based on combined soil and weather data.
        """
        
        advice = []
        
        # 1. Soil-based advice
        soil_type = soil['type']
        erosion = soil['erosion']
        
        advice.append(f"Soil Type: This location features **{soil_type}**.")
        
        if 'Lateritic Soil' in soil_type or erosion == 'High':
            advice.append("⚠️ **Erosion Risk:** The high erosion risk means you should implement terrace farming or heavy mulching immediately.")
        
        # 2. Weather-based advice (Current conditions)
        current = weather.get("current", {})
        temp = current.get("temperature_2m", 0)
        precip = current.get("precipitation", 0)
        wind = current.get("wind_speed_10m", 0)
        code = current.get("weather_code", 0)
        condition = interpret_weather_code(code)

        if temp > 30:
            advice.append("🌡️ **Heat Alert:** Current high temperatures require increased **irrigation frequency** to prevent crop dehydration.")
        elif temp < 10:
            advice.append("🥶 **Cool Weather:** Consider protecting vulnerable crops from cold shock, possibly using temporary covers.")
        
        if precip > 0 or code in [61, 63, 65, 80, 81, 82]:
            advice.append("☔ **Rainfall:** Due to current rain, postpone any major field work (ploughing, spraying) for at least 24 hours to prevent soil compaction.")
            
        if wind > 30:
            advice.append("🌬️ **Wind Warning:** Strong winds could cause lodging. Ensure taller crops are adequately staked or sheltered.")
            
        # 3. Combined/Crop Suitability advice
        best_crops = ", ".join(soil['crops'])
        advice.append(f"\n🌱 **Best Crop Strategy:** The most suitable crops are: **{best_crops}**.")
        advice.append(f"Fertility: The soil has **{soil['fertility']}** fertility. Supplement with organic compost before planting the next cycle.")

        if not advice:
            advice.append("Conditions are stable. Proceed with routine maintenance and monitoring.")
        
        return "\n".join(advice)
        
    def get_agricultural_recommendation(self, location: str) -> Dict:
        """
        Main method to get all data, run analysis, and return a comprehensive report.
        """
        
        # 1. Get Coordinates
        coords = self.get_coordinates(location)
        if not coords:
            return {"error": f"Could not find location: {location}"}
        lat, lon, location_name = coords
        
        # 2. Fetch Combined Weather Data
        raw_weather_data = self.fetch_combined_data(lat, lon)
        if not raw_weather_data:
            return {"error": "Could not fetch weather data"}
        
        # 3. Determine Climate Zone
        current = raw_weather_data.get("current", {})
        daily = raw_weather_data.get("daily", {})
        temp_max_daily = daily.get("temperature_2m_max", [0])[0] if daily else 0
        precip_sum_daily = daily.get("precipitation_sum", [0])[0] if daily else 0
        
        climate_zone = get_climate_zone(lat, temp_max_daily, precip_sum_daily)
        
        # 4. Predict Soil Characteristics
        soil_info = predict_soil_characteristics(lat, climate_zone)
        
        # 5. Extract Current Weather Summary
        temperature = current.get("temperature_2m", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        precipitation = current.get("precipitation", 0)
        wind_speed = current.get("wind_speed_10m", "N/A")
        weather_code = current.get("weather_code", 0)
        condition = interpret_weather_code(weather_code)

        # 6. Generate Final Advice
        final_advice = self.generate_advice(raw_weather_data, soil_info)
        
        # 7. Compile Final Report
        return {
            "location": location_name,
            "coordinates": {"latitude": lat, "longitude": lon},
            "weather": {
                "temperature": temperature,
                "humidity": humidity,
                "precipitation": precipitation,
                "wind_speed": wind_speed,
                "condition": condition,
                "climate_zone": climate_zone
            },
            "soil": soil_info,
            "advice": final_advice
        }

# --- For Local Testing ---
if __name__ == "__main__":
    agent = AgriAgent()
    
    print("\n" + "🌱" * 15)
    print(" Agribusiness Analysis Agent CLI ")
    print("🌱" * 15)
    
    while True:
        location = input("\nEnter location (e.g., 'Pune' or 'London', 'quit' to exit): ").strip()
        
        if location.lower() in ['quit', 'exit', 'q']:
            print("\nAnalysis complete. Goodbye! 👋")
            break
            
        if not location:
            print("Please enter a valid location!")
            continue
            
        print(f"\n🔍 Running comprehensive analysis for: {location}...")
        
        try:
            report = agent.get_agricultural_recommendation(location)
            
            if "error" in report:
                print(f"❌ Error during analysis: {report['error']}")
                continue
            
            # Formatted CLI Output
            print("\n" + "=" * 60)
            print(f"📍 LOCATION REPORT: {report['location']}")
            print(f"   ({report['coordinates']['latitude']:.2f}°N, {report['coordinates']['longitude']:.2f}°E)")
            print("-" * 60)
            print("--- CURRENT WEATHER ---")
            print(f"🌡️ Temperature: {report['weather']['temperature']}°C")
            print(f"💧 Humidity: {report['weather']['humidity']}%")
            print(f"🌧️ Condition: {report['weather']['condition']} ({report['weather']['precipitation']} mm)")
            print(f"💨 Wind: {report['weather']['wind_speed']} km/h")
            print(f"🗺️ Climate Zone: {report['weather']['climate_zone'].title()}")
            print("-" * 60)
            print("--- SOIL CHARACTERISTICS ---")
            print(f"🔬 Type: {report['soil']['type']}")
            print(f"💪 Fertility: {report['soil']['fertility']}")
            print(f"🚫 Erosion Risk: {report['soil']['erosion']}")
            print(f"🌾 Best Crops: {', '.join(report['soil']['crops'])}")
            print("-" * 60)
            print("--- FINAL AGRICULTURAL ADVICE ---")
            print(f"\n{report['advice']}")
            print("\n" + "=" * 60)
            
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
