from django.shortcuts import render
from .predict_soil_type import predict_soil_texture
from .predict_locationl_altitude import predict_altitude
from .predict_weather import get_forecast_summary
from .predict_crop_requirements import predict_crop_requirements
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import CropRequirementPrediction
from weatherDataApp .models import WeatherData


# Create function to get raw soil texture data (without Response object)
def get_soil_texture(district_name, sector_name):
    if not district_name or not sector_name:
        return {"error": "District and Sector names are required."}
    
    soil_prediction = predict_soil_texture(district_name, sector_name)
    print(f"Predicted soil texture for {district_name}, {sector_name}: {soil_prediction}")
    
    return soil_prediction



def get_location_altitude(district_name, sector_name):
    if not district_name or not sector_name:
        return {"error": "District and Sector names are required."}
    
    altitude_prediction = predict_altitude(district_name, sector_name)
    # print(f"Predicted altitude for {district_name}, {sector_name}: {altitude_prediction}")
    
    return altitude_prediction


# Create function to get raw weather data (without Response object)
def get_weather(district_name, sector_name):
    if not district_name or not sector_name:
        return {"error": "District and Sector names are required."}
    
    weather_prediction = get_forecast_summary(district_name)
    print(f"Predicted weather for {district_name}, {sector_name}: {weather_prediction}")
    
    return weather_prediction




@api_view(['POST'])
@permission_classes([AllowAny]) 
def make_crop_requirement_prediction(request):
    print("==== Rwanda Agriculture Advisory System ====")
    print("This system predicts soil type and crop requirements based on location and crop information.")
    
    # Collect user inputs
    district_name = request.data.get("district")
    sector_name = request.data.get("sector")
    crop_name = request.data.get("crop")
    season_name = request.data.get("season")
    
    # Validate required inputs
    if not district_name or not sector_name or not crop_name:
        return Response({"error": "District, sector, and crop name are required."}, status=400)
    
    # Predict soil texture - use the raw data function, not the view
    print("\nAnalyzing soil data for this location...")
    soil_prediction = get_soil_texture(district_name, sector_name)
    
    weather_data = get_weather(district_name, sector_name)
    
    if isinstance(soil_prediction, dict) and "error" in soil_prediction:
        print(f"\n❌ {soil_prediction['error']}")
        return Response({"error": soil_prediction['error']}, status=400)
    
    print(f"\n✅ Predicted soil texture for {district_name}, {sector_name}: {soil_prediction}")
    
    # Get altitude - use the raw data function, not the view
    altitude_prediction = get_location_altitude(district_name, sector_name)
    
    if isinstance(altitude_prediction, dict) and "error" in altitude_prediction:
        print(f"\n❌ {altitude_prediction['error']}")
        return Response({"error": altitude_prediction['error']}, status=400)
    
    altitude = altitude_prediction
    
    # Make crop requirement prediction
    print("\nGenerating crop requirements for these conditions...")
    prediction = predict_crop_requirements(crop_name, soil_prediction, altitude=altitude, season=season_name)
    
    # Handle errors in prediction
    if isinstance(prediction, dict) and 'error' in prediction:
        print(f"\n❌ Error in prediction: {prediction['error']}")
        return Response({"error": prediction['error']}, status=400)
    
    # Format the response data
    response_data = {
        "location": {
            "district": district_name,
            "sector": sector_name
        },
        "soil_type": prediction.get('soil_type', soil_prediction),
        "crop": prediction.get('crop', crop_name),
        "season": season_name,
        "altitude": altitude,
        "requirements": {
            "nitrogen_kg_per_ha": prediction['requirements']['nitrogen_kg_per_ha'],
            "phosphorus_kg_per_ha": prediction['requirements']['phosphorus_kg_per_ha'],
            "potassium_kg_per_ha": prediction['requirements']['potassium_kg_per_ha'],
            "water_requirement_mm": prediction['requirements']['water_requirement_mm']
        },
        "weather": weather_data,

    }
    
    # Add optional information if available
    if 'optimal_ph' in prediction['requirements']:
        response_data['requirements']['optimal_ph'] = prediction['requirements']['optimal_ph']
    
    if 'planting_info' in prediction['requirements']:
        response_data['planting_info'] = {
            "row_spacing_cm": prediction['requirements']['planting_info']['row_spacing_cm'],
            "plant_spacing_cm": prediction['requirements']['planting_info']['plant_spacing_cm']
        }
    
    if 'expected_yield_tons_per_ha' in prediction:
        response_data['expected_yield_tons_per_ha'] = prediction['expected_yield_tons_per_ha']
    
    if 'intercropping_recommendation' in prediction:
        response_data['intercropping_recommendation'] = prediction['intercropping_recommendation']
    
    if 'seasonal_recommendations' in prediction:
        response_data['seasonal_recommendations'] = prediction['seasonal_recommendations']
    
    # Keep console output for debugging (all your print statements)
    print("\n" + "="*70)
    print("CROP REQUIREMENTS")
    print("="*70)
    print(f"Nitrogen: {prediction['requirements']['nitrogen_kg_per_ha']} kg/ha")
    print(f"Phosphorus: {prediction['requirements']['phosphorus_kg_per_ha']} kg/ha")
    print(f"Potassium: {prediction['requirements']['potassium_kg_per_ha']} kg/ha")
    print(f"Water: {prediction['requirements']['water_requirement_mm']} mm")
    
    if 'planting_info' in prediction['requirements']:
        print("\n" + "="*70)
        print("PLANTING INFORMATION")
        print("="*70)
        planting = prediction['requirements']['planting_info']
        print(f"Row Spacing: {planting['row_spacing_cm']} cm")
        print(f"Plant Spacing: {planting['plant_spacing_cm']} cm")
        print(f"Planting Depth: {planting['planting_depth_cm']} cm")
    
    if 'expected_yield_tons_per_ha' in prediction:
        print("\n" + "="*70)
        print("YIELD INFORMATION")
        print("="*70)
        print(f"Expected Yield: {prediction['expected_yield_tons_per_ha']} tons/ha")
    
    if 'intercropping_recommendation' in prediction:
        print("\n" + "="*70)
        print("INTERCROPPING RECOMMENDATIONS") 
        print("="*70)
        print(f"Compatible crops: {', '.join(prediction['intercropping_recommendation'])}")
    
    if 'seasonal_recommendations' in prediction:
        print("\n" + "="*70)
        print("SEASONAL RECOMMENDATIONS")
        print("="*70)
        for i, rec in enumerate(prediction['seasonal_recommendations'], 1):
            print(f"{i}. {rec}")
    
    print("\n" + "="*70)
    print("NOTE: This is an advisory system. Please consult with local agricultural")
    print("extension officers for specific advice for your farm.")
    print("="*70)
    
    
    # Return the formatted response to the API client
    return Response(response_data)




from django.shortcuts import render
from .predict_soil_type import predict_soil_texture
from .predict_locationl_altitude import predict_altitude
from .predict_weather import get_forecast_summary
from .predict_crop_requirements import predict_crop_requirements
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response


# New helper function to map seasons to months
def get_season_months(season_name):
    """Maps season names to corresponding months in Rwanda."""
    season_mappings = {
        "short_rainy": ["September", "October", "November", "December"],
        "short_dry": ["January", "February"],
        "long_rainy": ["March", "April", "May"],
        "long_dry": ["June", "July", "August"]
    }
    
    # Alternative names sometimes used
    alternative_names = {
        "minor_rainy": "short_rainy",
        "minor_dry": "short_dry",
        "major_rainy": "long_rainy",
        "major_dry": "long_dry"
    }
    
    # Check if season is in alternative names and map to standard name
    if season_name in alternative_names:
        season_name = alternative_names[season_name]
    
    return season_mappings.get(season_name, [])


# New helper function to extract monthly weather data from forecast
def extract_monthly_data(weather_text, months):
    """Extract weather data for specific months from the forecast text."""
    monthly_data = {}
    
    # Process weather text to extract monthly information
    if not weather_text:
        return monthly_data
    
    lines = weather_text.split('\n')
    current_month = None
    
    for line in lines:
        line = line.strip()
        
        # Look for month headers
        for month in months:
            if line.startswith(month + ":"):
                current_month = month
                monthly_data[current_month] = {}
        
        # If we're in a month section, collect the data
        if current_month and line and ':' in line:
            # Skip month header line
            if not line.startswith(current_month):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Extract numeric values
                if "Temperature" in key:
                    try:
                        monthly_data[current_month]["temperature"] = float(value.split('°C')[0])
                    except:
                        pass
                elif "Rainfall" in key:
                    try:
                        monthly_data[current_month]["rainfall"] = float(value.split('mm')[0])
                    except:
                        pass
                elif "Humidity" in key:
                    try:
                        monthly_data[current_month]["humidity"] = float(value.split('%')[0])
                    except:
                        pass
    
    return monthly_data


# New helper function to extract seasonal weather data
def extract_seasonal_data(weather_text, season_name):
    """Extract seasonal forecast summary for the specified season."""
    season_data = {}
    
    # Map season name to how it appears in the forecast
    season_display_names = {
        "short_rainy": "Minor Rainy Season",
        "short_dry": "Minor Dry Season",
        "long_rainy": "Major Rainy Season",
        "long_dry": "Major Dry Season"
    }
    
    # Alternative names sometimes used
    alternative_names = {
        "minor_rainy": "Minor Rainy Season",
        "minor_dry": "Minor Dry Season",
        "major_rainy": "Major Rainy Season",
        "major_dry": "Major Dry Season"
    }
    
    # Check which display name to use
    display_name = season_display_names.get(season_name, "")
    if not display_name and season_name in alternative_names:
        display_name = alternative_names[season_name]
    
    if not display_name or not weather_text:
        return season_data
    
    lines = weather_text.split('\n')
    in_season_section = False
    
    for i, line in enumerate(lines):
        if display_name + ":" in line:
            in_season_section = True
            continue
        
        if in_season_section:
            # Check if we've reached the next season or section
            if "Season:" in line or "MONTHLY FORECAST" in line:
                break
            
            line = line.strip()
            if line and ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if "Temperature" in key:
                    try:
                        temp_parts = value.split('°C')[0].strip()
                        season_data["avg_temperature"] = float(temp_parts)
                        
                        # Try to extract temperature range
                        if "Range:" in value:
                            range_part = value.split('Range:')[1].strip()
                            min_temp, max_temp = range_part.split(' to ')
                            season_data["min_temperature"] = float(min_temp.split('°C')[0])
                            season_data["max_temperature"] = float(max_temp.split('°C')[0])
                    except:
                        pass
                elif "Rainfall" in key:
                    try:
                        # Extract total rainfall
                        if "Total:" in value:
                            total_part = value.split('Total:')[1].strip()
                            season_data["total_rainfall"] = float(total_part.split('mm')[0])
                        
                        # Extract average rainfall
                        if "Avg:" in value:
                            avg_part = value.split('Avg:')[1].strip()
                            season_data["avg_rainfall_per_day"] = float(avg_part.split('mm/day')[0])
                            
                        # Extract max rainfall
                        if "Max:" in value:
                            max_part = value.split('Max:')[1].strip()
                            season_data["max_rainfall_per_day"] = float(max_part.split('mm/day')[0])
                    except:
                        pass
                elif "Humidity" in key:
                    try:
                        season_data["humidity"] = float(value.split('%')[0])
                    except:
                        pass
    
    return season_data


# New function to adjust water requirements based on weather
def adjust_water_requirement(base_requirement, season_data, monthly_data):
    """
    Adjust the water requirement based on predicted rainfall and temperature.
    Returns the adjusted water requirement in mm.
    """
    if not season_data:
        return base_requirement
    
    # Get seasonal rainfall data
    seasonal_rainfall = season_data.get("total_rainfall", 0)
    
    # Calculate average monthly rainfall for the season
    total_monthly_rainfall = sum(month.get("rainfall", 0) for month in monthly_data.values())
    num_months = len(monthly_data) if monthly_data else 1
    avg_monthly_rainfall = total_monthly_rainfall / num_months if num_months > 0 else 0
    
    # Get temperature data
    avg_temperature = season_data.get("avg_temperature", 20)
    
    # Calculate water deficit/surplus based on crop needs vs rainfall
    water_deficit = base_requirement - seasonal_rainfall
    
    # Adjust for temperature (higher temps = higher evaporation = more water needed)
    temperature_factor = 1.0
    if avg_temperature > 25:
        temperature_factor = 1.2  # Hot conditions need more water
    elif avg_temperature < 18:
        temperature_factor = 0.9  # Cooler conditions need less water
    
    # Calculate adjusted water requirement
    if water_deficit > 0:
        # Needs irrigation to supplement rainfall
        adjusted_requirement = water_deficit * temperature_factor
    else:
        # Rainfall exceeds basic needs, but still need some irrigation for consistency
        # Set a minimum of 15% of base requirement
        adjusted_requirement = max(base_requirement * 0.15, base_requirement * 0.3 * temperature_factor)
    
    # Ensure we don't go below a minimum threshold
    min_requirement = base_requirement * 0.1
    adjusted_requirement = max(adjusted_requirement, min_requirement)
    
    return adjusted_requirement


from .models import CropRequirementPrediction
from weatherDataApp.models import WeatherData

@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def make_weather_adjusted_crop_prediction(request):
    print("==== Rwanda Agriculture Weather-Adjusted Advisory System ====")
    print("This system predicts crop requirements adjusted for seasonal weather patterns.")
    
    # Collect user inputs
    district_name = request.data.get("district")
    sector_name = request.data.get("sector")
    crop_name = request.data.get("crop")
    season_name = request.data.get("season")
    
    # Validate required inputs
    if not district_name or not sector_name or not crop_name or not season_name:
        return Response({"error": "District, sector, crop name, and season are required."}, status=400)
    
    # Get soil texture prediction
    print("\nAnalyzing soil data for this location...")
    soil_prediction = get_soil_texture(district_name, sector_name)
    
    if isinstance(soil_prediction, dict) and "error" in soil_prediction:
        print(f"\n❌ {soil_prediction['error']}")
        return Response({"error": soil_prediction['error']}, status=400)
    
    print(f"\n✅ Predicted soil texture for {district_name}, {sector_name}: {soil_prediction}")
    
    # Get altitude
    altitude_prediction = get_location_altitude(district_name, sector_name)
    
    if isinstance(altitude_prediction, dict) and "error" in altitude_prediction:
        print(f"\n❌ {altitude_prediction['error']}")
        return Response({"error": altitude_prediction['error']}, status=400)
    
    print(f"\n✅ Predicted altitude for {district_name}, {sector_name}: {altitude_prediction}")
    
    altitude = altitude_prediction
    
    # Get weather forecast
    print("\nRetrieving weather data for this location...")
    weather_data = get_weather(district_name, sector_name)
    
    if isinstance(weather_data, dict) and "error" in weather_data:
        print(f"\n❌ {weather_data['error']}")
        return Response({"error": weather_data['error']}, status=400)
    
    # Make base crop requirement prediction
    print("\nGenerating base crop requirements...")
    base_prediction = predict_crop_requirements(crop_name, soil_prediction, altitude=altitude, season=season_name)
    
    # Handle errors in prediction
    if isinstance(base_prediction, dict) and 'error' in base_prediction:
        print(f"\n❌ Error in prediction: {base_prediction['error']}")
        return Response({"error": base_prediction['error']}, status=400)
    
    # Get months for the given season
    season_months = get_season_months(season_name)
    print(f"\nAnalyzing weather for {season_name} season (months: {', '.join(season_months)})")
    
    # Extract weather data for the season months
    monthly_weather_data = extract_monthly_data(weather_data, season_months)
    seasonal_weather_data = extract_seasonal_data(weather_data, season_name)
    
    # Adjust water requirements based on weather
    base_water_req = base_prediction['requirements']['water_requirement_mm']
    adjusted_water_req = adjust_water_requirement(base_water_req, seasonal_weather_data, monthly_weather_data)
    
    print(f"\nBase water requirement: {base_water_req:.2f} mm")
    print(f"Weather-adjusted water requirement: {adjusted_water_req:.2f} mm")
    
    # Calculate adjustment for fertilizer requirements based on rainfall
    # More rainfall can leach nutrients, requiring more fertilizer
    fertilizer_adjustment = 1.0
    if seasonal_weather_data.get("total_rainfall", 0) > 500:  # Heavy rainfall
        fertilizer_adjustment = 1.15
    elif seasonal_weather_data.get("total_rainfall", 0) < 200:  # Low rainfall
        fertilizer_adjustment = 0.9
    
    # Apply adjustments to fertilizer requirements
    adjusted_nitrogen = base_prediction['requirements']['nitrogen_kg_per_ha'] * fertilizer_adjustment
    adjusted_phosphorus = base_prediction['requirements']['phosphorus_kg_per_ha'] * fertilizer_adjustment
    adjusted_potassium = base_prediction['requirements']['potassium_kg_per_ha'] * fertilizer_adjustment
    
    # Create weather-specific recommendations
    weather_specific_recommendations = []
    
    if seasonal_weather_data.get("total_rainfall", 0) > 800:
        weather_specific_recommendations.append("Implement raised beds or ridges to improve drainage during heavy rainfall")
        weather_specific_recommendations.append("Apply fertilizer in split doses to prevent leaching during heavy rains")
    elif seasonal_weather_data.get("total_rainfall", 0) < 300:
        weather_specific_recommendations.append("Implement mulching to conserve soil moisture during dry periods")
        weather_specific_recommendations.append("Consider drip irrigation to optimize water usage")
    
    if seasonal_weather_data.get("avg_temperature", 20) > 24:
        weather_specific_recommendations.append("Use shade nets during peak temperature hours if possible")
        weather_specific_recommendations.append("Increase frequency of irrigation during hot periods")
    elif seasonal_weather_data.get("avg_temperature", 20) < 18:
        weather_specific_recommendations.append("Consider using plastic mulch to increase soil temperature")
    
    # Format the response data
    response_data = {
        "location": {
            "district": district_name,
            "sector": sector_name
        },
        "soil_type": base_prediction.get('soil_type', soil_prediction),
        "crop": base_prediction.get('crop', crop_name),
        "season": season_name,
        "altitude": altitude,
        "weather_analysis": {
            "season_months": season_months,
            "seasonal_data": seasonal_weather_data,
            "monthly_data": monthly_weather_data
        },
        "requirements": {
            "nitrogen_kg_per_ha": adjusted_nitrogen,
            "phosphorus_kg_per_ha": adjusted_phosphorus,
            "potassium_kg_per_ha": adjusted_potassium,
            "water_requirement_mm": adjusted_water_req,
        },
        "base_requirements": {
            "nitrogen_kg_per_ha": base_prediction['requirements']['nitrogen_kg_per_ha'],
            "phosphorus_kg_per_ha": base_prediction['requirements']['phosphorus_kg_per_ha'],
            "potassium_kg_per_ha": base_prediction['requirements']['potassium_kg_per_ha'],
            "water_requirement_mm": base_water_req,
        },
        "weather": weather_data,
    }
    
    # Add optional information if available
    if 'optimal_ph' in base_prediction['requirements']:
        response_data['requirements']['optimal_ph'] = base_prediction['requirements']['optimal_ph']
    
    if 'planting_info' in base_prediction['requirements']:
        response_data['planting_info'] = {
            "row_spacing_cm": base_prediction['requirements']['planting_info']['row_spacing_cm'],
            "plant_spacing_cm": base_prediction['requirements']['planting_info']['plant_spacing_cm'],
            "planting_depth_cm": base_prediction['requirements']['planting_info']['planting_depth_cm']
        }
    
    if 'expected_yield_tons_per_ha' in base_prediction:
        # Adjust yield based on weather conditions
        yield_adjustment = 1.0
        if 'total_rainfall' in seasonal_weather_data:
            rainfall = seasonal_weather_data['total_rainfall']
            # Adjust yield estimation based on rainfall
            if rainfall > 1000:  # Very high rainfall
                yield_adjustment *= 0.9  # Too much rain can reduce yield
            elif rainfall < 300:  # Low rainfall
                yield_adjustment *= 0.8  # Too little rain can significantly reduce yield
            else:
                yield_adjustment *= 1.1  # Optimal rainfall can improve yield
        
        adjusted_yield = base_prediction['expected_yield_tons_per_ha'] * yield_adjustment
        response_data['expected_yield_tons_per_ha'] = adjusted_yield
        response_data['base_expected_yield_tons_per_ha'] = base_prediction['expected_yield_tons_per_ha']
    
    if 'intercropping_recommendation' in base_prediction:
        response_data['intercropping_recommendation'] = base_prediction['intercropping_recommendation']
    
    if 'seasonal_recommendations' in base_prediction:
        # Combine base recommendations with weather-specific ones
        combined_recommendations = base_prediction['seasonal_recommendations'] + weather_specific_recommendations
        response_data['seasonal_recommendations'] = combined_recommendations
    else:
        response_data['seasonal_recommendations'] = weather_specific_recommendations
        
        
        
  
    # Save base requirements to database
    try:
        
        if request.user:
            print(f"Found user making prediction: {request.user.email}")
            # Create default values dictionary with required fields
            defaults = {
                'soil_type': base_prediction.get('soil_type', soil_prediction),
                'altitude': altitude,
                'nitrogen_kg_per_ha': base_prediction['requirements']['nitrogen_kg_per_ha'],
                'phosphorus_kg_per_ha': base_prediction['requirements']['phosphorus_kg_per_ha'],
                'potassium_kg_per_ha': base_prediction['requirements']['potassium_kg_per_ha'],
                'water_requirement_mm': base_water_req,
                'created_by': request.user
            }
            
            # Add optional fields if they exist
            if 'optimal_ph' in base_prediction['requirements']:
                defaults['optimal_ph'] = base_prediction['requirements']['optimal_ph']
            
            if 'planting_info' in base_prediction['requirements']:
                planting = base_prediction['requirements']['planting_info']
                defaults['row_spacing_cm'] = planting['row_spacing_cm']
                defaults['plant_spacing_cm'] = planting['plant_spacing_cm']
                defaults['planting_depth_cm'] = planting['planting_depth_cm']
            
            if 'expected_yield_tons_per_ha' in base_prediction:
                defaults['expected_yield_tons_per_ha'] = base_prediction['expected_yield_tons_per_ha']
            
            # Handle recommendations
            base_recommendations = []
            if 'seasonal_recommendations' in base_prediction:
                base_recommendations = base_prediction['seasonal_recommendations']
            defaults['seasonal_recommendations'] = base_recommendations
            
            if 'intercropping_recommendation' in base_prediction:
                defaults['intercropping_recommendation'] = base_prediction['intercropping_recommendation']

            
            # Create or update record in the database
            crop_req, created = CropRequirementPrediction.objects.update_or_create(
                district=district_name,
                sector=sector_name,
                crop=crop_name,
                season=season_name,
                defaults=defaults
            )
            
            # Add the ID to the response
            response_data['requirement_id'] = crop_req.id
            response_data['is_new_requirement'] = created
            
            print(f"\n✅ {'Created' if created else 'Updated'} crop requirement record with ID: {crop_req.id}")
            
            # THEN create and save the weather record
            # THEN create and save the weather record
            weather_record = WeatherData(
                district=district_name,
                sector=sector_name,
                season=season_name,
                # Weather data fields...
                monthly_data=weather_data.get('monthly_data', {}),
                
                minor_dry_season_temp=weather_data.get('seasonal_data', {}).get('minor_dry', {}).get('temperature'),
                minor_dry_season_rainfall=weather_data.get('seasonal_data', {}).get('minor_dry', {}).get('rainfall'),
                minor_dry_season_humidity=weather_data.get('seasonal_data', {}).get('minor_dry', {}).get('humidity'),
                
                major_rainy_season_temp=weather_data.get('seasonal_data', {}).get('major_rainy', {}).get('temperature'),
                major_rainy_season_rainfall=weather_data.get('seasonal_data', {}).get('major_rainy', {}).get('rainfall'),
                major_rainy_season_humidity=weather_data.get('seasonal_data', {}).get('major_rainy', {}).get('humidity'),
                
                major_dry_season_temp=weather_data.get('seasonal_data', {}).get('major_dry', {}).get('temperature'),
                major_dry_season_rainfall=weather_data.get('seasonal_data', {}).get('major_dry', {}).get('rainfall'),
                major_dry_season_humidity=weather_data.get('seasonal_data', {}).get('major_dry', {}).get('humidity'),
                
                minor_rainy_season_temp=weather_data.get('seasonal_data', {}).get('minor_rainy', {}).get('temperature'),
                minor_rainy_season_rainfall=weather_data.get('seasonal_data', {}).get('minor_rainy', {}).get('rainfall'),
                minor_rainy_season_humidity=weather_data.get('seasonal_data', {}).get('minor_rainy', {}).get('humidity'),
                
                created_by=request.user,
            )
            weather_record.related_prediction = crop_req
            weather_record.save()
            print(f"\n✅ Saved weather data record for {district_name}, {sector_name}")
            
            
        else:
            print("\n⚠️ User not authenticated - crop requirement data not saved")
    except Exception as e:
        print(f"\n❌ Error saving crop requirement data: {str(e)}")
        # Don't return an error to the user, just log it and continue
    
    # Keep console output for debugging
    print("\n" + "="*70)
    print("WEATHER-ADJUSTED CROP REQUIREMENTS")
    print("="*70)
    print(f"Nitrogen: {adjusted_nitrogen:.2f} kg/ha (Base: {base_prediction['requirements']['nitrogen_kg_per_ha']:.2f} kg/ha)")
    print(f"Phosphorus: {adjusted_phosphorus:.2f} kg/ha (Base: {base_prediction['requirements']['phosphorus_kg_per_ha']:.2f} kg/ha)")
    print(f"Potassium: {adjusted_potassium:.2f} kg/ha (Base: {base_prediction['requirements']['potassium_kg_per_ha']:.2f} kg/ha)")
    print(f"Water: {adjusted_water_req:.2f} mm (Base: {base_water_req:.2f} mm)")
    
    if 'planting_info' in base_prediction['requirements']:
        print("\n" + "="*70)
        print("PLANTING INFORMATION")
        print("="*70)
        planting = base_prediction['requirements']['planting_info']
        print(f"Row Spacing: {planting['row_spacing_cm']} cm")
        print(f"Plant Spacing: {planting['plant_spacing_cm']} cm")
        print(f"Planting Depth: {planting['planting_depth_cm']} cm")
    
    if 'expected_yield_tons_per_ha' in response_data:
        print("\n" + "="*70)
        print("YIELD INFORMATION")
        print("="*70)
        print(f"Expected Yield: {response_data['expected_yield_tons_per_ha']:.2f} tons/ha (Base: {base_prediction['expected_yield_tons_per_ha']:.2f} tons/ha)")
    
    if 'intercropping_recommendation' in response_data:
        print("\n" + "="*70)
        print("INTERCROPPING RECOMMENDATIONS") 
        print("="*70)
        print(f"Compatible crops: {', '.join(response_data['intercropping_recommendation'])}")
    
    print("\n" + "="*70)
    print("WEATHER-SPECIFIC RECOMMENDATIONS")
    print("="*70)
    for i, rec in enumerate(weather_specific_recommendations, 1):
        print(f"{i}. {rec}")
    
    print("\n" + "="*70)
    print("SEASONAL RECOMMENDATIONS")
    print("="*70)
    for i, rec in enumerate(response_data['seasonal_recommendations'], 1):
        print(f"{i}. {rec}")
    
    print("\n" + "="*70)
    print("NOTE: This is an advisory system. Please consult with local agricultural")
    print("extension officers for specific advice for your farm.")
    print("="*70)
    
    # Return the formatted response to the API client
    return Response(response_data)




# views.py
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.shortcuts import get_object_or_404
from .models import CropRequirementPrediction
from .serializers import CropRequirementPredictionSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_prediction_by_id(request, pk):
    """
    Get a specific crop requirement prediction by ID
    """
    prediction = get_object_or_404(CropRequirementPrediction, pk=pk)
    serializer = CropRequirementPredictionSerializer(prediction)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_predictions(request):
    """
    Get all crop requirement predictions
    """
    predictions = CropRequirementPrediction.objects.all()
    serializer = CropRequirementPredictionSerializer(predictions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_predictions(request):
    """
    Get all predictions created by the logged-in user
    """
    predictions = CropRequirementPrediction.objects.filter(created_by=request.user)
    serializer = CropRequirementPredictionSerializer(predictions, many=True)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_prediction(request, pk):
    """
    Update a crop requirement prediction
    """
    prediction = get_object_or_404(CropRequirementPrediction, pk=pk)
    
    # Check if the user is the owner of the prediction
    if prediction.created_by != request.user:
        return Response({"detail": "You do not have permission to update this prediction."}, 
                        status=status.HTTP_403_FORBIDDEN)
    
    # Partial update if PATCH method is used
    partial = request.method == 'PATCH'
    
    serializer = CropRequirementPredictionSerializer(prediction, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_prediction(request, pk):
    """
    Delete a crop requirement prediction
    """
    prediction = get_object_or_404(CropRequirementPrediction, pk=pk)
    
    # Check if the user is the owner of the prediction
    if prediction.created_by != request.user:
        return Response({"detail": "You do not have permission to delete this prediction."},
                        status=status.HTTP_403_FORBIDDEN)
    
    prediction.delete()
    return Response({"detail": "Prediction successfully deleted."},
                    status=status.HTTP_204_NO_CONTENT)














