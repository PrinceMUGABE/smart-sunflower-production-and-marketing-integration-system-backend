import pandas as pd
import pandas as pd
from joblib import load
import os
from rest_framework.response import Response
from .predict_soil_type import predict_soil_texture


# print(f"Current working directory: {os.getcwd()}")
# print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")
# print(f"Models directory should be: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')}")

current_dir = os.path.dirname(os.path.__file__)
models_dir = os.path.join(current_dir, 'models')


# def predict_crop_requirements(crop_name, soil_type, altitude='mid', season='short_dry'):

#     try:
        
#         # Get the directory where this script is located
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         # Define model directory within the project
#         model_dir = os.path.join(current_dir, 'models')
        
#         print(f"Looking for models in: {model_dir}")
        
#         # Check if model directory exists
#         if not os.path.exists(model_dir):
#             return Response({"error": f"Model directory '{model_dir}' does not exist."})
            
#         # Check if soil type subdirectory exists
#         soil_dir = os.path.join(model_dir, soil_type)
#         if not os.path.exists(soil_dir):
#             # Try to find an alternative soil type
#             available_soils = [d for d in os.listdir(model_dir) 
#                               if os.path.isdir(os.path.join(model_dir, d))]
#             if not available_soils:
#                 return Response({"error": "No soil type directories found in the model directory."})
            
#             # Use the first available soil type as fallback
#             soil_type = available_soils[0]
#             soil_dir = os.path.join(model_dir, soil_type)
#             print(f"Warning: Soil type '{soil_type}' not found. Using '{soil_type}' instead.")
        
#         # Load the comprehensive dataset
#         try:
#             # df = pd.read_csv('data/comprehensive_crop_requirements.csv')
#             df = pd.read_csv(os.path.join(current_dir, 'data', 'comprehensive_crop_requirements.csv'))
#         except FileNotFoundError:
#             return Response({"error": "Dataset file not found."})
        
#         # Get the row for this crop
#         crop_data = df[df['crop'].str.lower() == crop_name.lower()]
        
#         if len(crop_data) == 0:
#             # Try to find a close match using fuzzy matching
#             from difflib import get_close_matches
#             all_crops = df['crop'].unique()
#             close_matches = get_close_matches(crop_name, all_crops)
            
#             if close_matches:
#                 crop_name = close_matches[0]
#                 crop_data = df[df['crop'] == crop_name]
#                 print(f"Warning: Crop '{crop_name}' not found. Using closest match '{crop_name}' instead.")
#             else:
#                 return Response({"error": f"Crop '{crop_name}' not found in the dataset."})
        
#         # Create input features with a copy of crop data
#         input_features = crop_data.copy()
        
#         # Map Rwanda's seasons to the format in the dataset
#         season_mapping = {
#             'short_dry': 'short_dry',      # Dec-Feb
#             'long_rainy': 'long_rainy',    # Mar-May
#             'long_dry': 'long_dry',        # Jun-Sep
#             'short_rainy': 'short_rainy'   # Sep-Dec
#         }
        
#         detailed_season = season_mapping.get(season, 'short_dry')  # Default to short_dry if unknown
        
#         # Add missing altitude and season columns that models might expect
#         altitude_types = ['low', 'mid', 'high']
#         season_types = ['dry', 'wet', 'short_dry', 'long_rainy', 'long_dry', 'short_rainy']
        
#         # Generate all possible altitude-season combinations and ensure they exist in input_features
#         for alt in altitude_types:
#             for seas in season_types:
#                 col_name = f"{alt}_altitude_{seas}_adjusted"
#                 if col_name not in input_features.columns:
#                     input_features[col_name] = 0.0  # Add with default value
                
#         # Also ensure base altitude columns exist
#         for alt in altitude_types:
#             col_name = f"{alt}_altitude_adjusted"
#             if col_name not in input_features.columns:
#                 input_features[col_name] = 0.0
        
#         # Load the models for this soil type
#         soil_models = {}
        
#         # Define target variables - both general and season-specific
#         base_targets = ['adjusted_nitrogen', 'adjusted_phosphorus', 'adjusted_potassium']
        
#         # Check available model files directly
#         available_models = []
#         for filename in os.listdir(soil_dir):
#             if filename.endswith('_model.joblib'):
#                 model_name = filename.replace('_model.joblib', '')
#                 available_models.append(model_name)
        
#         # Find the best matching water requirement column/model
#         water_req_key = None
        
#         # First try: exact match for altitude and season
#         exact_match = f"{altitude}_altitude_{detailed_season}_adjusted"
#         if exact_match in available_models:
#             water_req_key = exact_match
        
#         # Second try: match with any season at this altitude
#         if not water_req_key:
#             altitude_models = [m for m in available_models if f"{altitude}_altitude" in m and "_adjusted" in m]
#             if altitude_models:
#                 water_req_key = altitude_models[0]
#                 print(f"Warning: No exact match for {altitude} altitude {detailed_season}. Using {water_req_key} instead.")
        
#         # Third try: match with any altitude for this season
#         if not water_req_key:
#             season_models = [m for m in available_models if f"{detailed_season}_adjusted" in m]
#             if season_models:
#                 water_req_key = season_models[0]
#                 print(f"Warning: No model for {altitude} altitude. Using {water_req_key} instead.")
        
#         # Fourth try: use any available water requirement model
#         if not water_req_key:
#             water_models = [m for m in available_models if "_altitude" in m and "_adjusted" in m]
#             if water_models:
#                 water_req_key = water_models[0]
#                 print(f"Warning: No specific model found for {altitude} altitude {detailed_season}. Using {water_req_key} as fallback.")
#             else:
#                 # If no water requirement models are found, we'll proceed without water predictions
#                 print(f"Warning: No water requirement models found. Proceeding with nutrient predictions only.")
#                 water_req_key = None
        
#         # Try to load all required models
#         target_variables = base_targets.copy()
#         if water_req_key:
#             target_variables.append(water_req_key)
            
#         missing_models = []
        
#         for target in target_variables:
#             model_path = os.path.join(soil_dir, f"{target}_model.joblib")
#             if os.path.exists(model_path):
#                 try:
#                     soil_models[target] = load(model_path)
#                 except Exception as e:
#                     print(f"Error loading model {target}: {str(e)}")
#                     missing_models.append(f"{target} (Error: {str(e)})")
#             else:
#                 missing_models.append(target)
        
#         # If we're missing nutrient models, try to use base models directly from dataset
#         if any(target in missing_models for target in base_targets):
#             print("Warning: Some nutrient models are missing. Using dataset values directly.")
#             for nutrient in base_targets:
#                 if nutrient in missing_models and nutrient.replace('adjusted_', '') in crop_data.columns:
#                     base_nutrient = nutrient.replace('adjusted_', '')
#                     soil_models[nutrient] = {
#                         'direct_value': float(crop_data[base_nutrient].values[0])
#                     }
#                     missing_models.remove(nutrient)
        
#         # If we're still missing crucial models after fallbacks, return error
#         if missing_models and all(target in missing_models for target in base_targets):
#             return Response({"error": f"Missing models for all nutrient targets: {', '.join(missing_models)}"})
        
#         # Make predictions for each target variable or use direct values
#         predictions = {}
#         for target, model in soil_models.items():
#             if isinstance(model, dict) and 'direct_value' in model:
#                 # Use direct value from the dataset
#                 predictions[target] = model['direct_value']
#             else:
#                 # Use the model to predict
#                 try:
#                     # Check if input_features has all columns the model expects
#                     if hasattr(model, 'feature_names_in_'):
#                         missing_cols = set(model.feature_names_in_) - set(input_features.columns)
#                         for col in missing_cols:
#                             input_features[col] = 0.0  # Add missing columns with default values
                    
#                     predictions[target] = model.predict(input_features)[0]
#                 except Exception as e:
#                     print(f"Error predicting with {target} model: {str(e)}")
#                     # Use a default value based on dataset if prediction fails
#                     if target.replace('adjusted_', '') in crop_data.columns:
#                         base_value = crop_data[target.replace('adjusted_', '')].values[0]
#                         predictions[target] = float(base_value)
#                         print(f"Using default value for {target}: {predictions[target]}")
#                     else:
#                         # Use reasonable defaults if all else fails
#                         defaults = {
#                             'adjusted_nitrogen': 50.0,
#                             'adjusted_phosphorus': 25.0,
#                             'adjusted_potassium': 30.0
#                         }
#                         if target in defaults:
#                             predictions[target] = defaults[target]
#                             print(f"Using standard default for {target}: {predictions[target]}")
#                         else:
#                             # For water requirements, use a reasonable default based on season
#                             water_defaults = {
#                                 'short_dry': 450,
#                                 'long_rainy': 200,
#                                 'long_dry': 550,
#                                 'short_rainy': 350
#                             }
#                             predictions[target] = water_defaults.get(season, 400)
#                             print(f"Using seasonal default water value: {predictions[target]}")
        
#         # Apply seasonal adjustments for nutrient requirements
#         seasonal_factors = {
#             'short_dry': {
#                 'nitrogen_factor': 1.0,
#                 'phosphorus_factor': 1.0,
#                 'potassium_factor': 1.0,
#                 'yield_factor': 1.0
#             },
#             'long_rainy': {
#                 'nitrogen_factor': 1.25,
#                 'phosphorus_factor': 0.9,
#                 'potassium_factor': 1.15,
#                 'yield_factor': 1.1
#             },
#             'long_dry': {
#                 'nitrogen_factor': 0.9,
#                 'phosphorus_factor': 1.1,
#                 'potassium_factor': 0.95,
#                 'yield_factor': 0.9
#             },
#             'short_rainy': {
#                 'nitrogen_factor': 1.15,
#                 'phosphorus_factor': 0.95,
#                 'potassium_factor': 1.05,
#                 'yield_factor': 1.05
#             }
#         }
        
#         # Apply seasonal adjustment factors
#         nitrogen = predictions.get('adjusted_nitrogen', 50.0) * seasonal_factors[season]['nitrogen_factor']
#         phosphorus = predictions.get('adjusted_phosphorus', 25.0) * seasonal_factors[season]['phosphorus_factor']
#         potassium = predictions.get('adjusted_potassium', 30.0) * seasonal_factors[season]['potassium_factor']
        
#         # Select the water requirement based on altitude and season
#         water_requirement = predictions.get(water_req_key, None)
        
#         # If water_requirement is still None, provide a default based on season and altitude
#         if water_requirement is None:
#             # Base defaults by season (in mm)
#             water_defaults = {
#                 'short_dry': 450,
#                 'long_rainy': 200,
#                 'long_dry': 550,
#                 'short_rainy': 350
#             }
            
#             # Altitude adjustment factors
#             altitude_factors = {
#                 'low': 1.2,  # Higher water requirement in low altitude
#                 'mid': 1.0,  # Base reference
#                 'high': 0.8   # Lower water requirement in high altitude (cooler, less evaporation)
#             }
            
#             # Use the default for the season, adjusted by altitude
#             base_water = water_defaults.get(season, 400)
#             altitude_factor = altitude_factors.get(altitude, 1.0)
#             water_requirement = base_water * altitude_factor
#             print(f"Using calculated default water requirement: {water_requirement} mm")
        
#         # Format the results
#         requirements = {
#             "crop": crop_name,
#             "soil_type": soil_type,
#             "season": season,
#             "altitude": altitude,
#             "requirements": {
#                 "nitrogen_kg_per_ha": round(nitrogen, 2),
#                 "phosphorus_kg_per_ha": round(phosphorus, 2),
#                 "potassium_kg_per_ha": round(potassium, 2),
#                 "water_requirement_mm": round(water_requirement, 2) if water_requirement else None,
#             }
#         }
        
#         # Add optional fields if they exist in the dataset
#         if 'optimal_ph' in crop_data:
#             requirements["requirements"]["optimal_ph"] = float(crop_data['optimal_ph'].values[0])
        
#         if 'min_sunlight_hours' in crop_data:
#             requirements["requirements"]["min_sunlight_hours"] = int(crop_data['min_sunlight_hours'].values[0])
        
#         # Add planting information if available
#         planting_fields = ['row_spacing_cm', 'plant_spacing_cm', 'planting_depth_cm']
#         if all(field in crop_data.columns for field in planting_fields):
#             planting_info = {
#                 "row_spacing_cm": int(crop_data['row_spacing_cm'].values[0]),
#                 "plant_spacing_cm": int(crop_data['plant_spacing_cm'].values[0]),
#                 "planting_depth_cm": int(crop_data['planting_depth_cm'].values[0]),
#             }
#             requirements["requirements"]["planting_info"] = planting_info
        
#         # Add expected yield if available
#         if 'optimal_yield' in crop_data.columns:
#             base_yield = float(crop_data['optimal_yield'].values[0])
#             # Apply yield factor based on season
#             adjusted_yield = base_yield * seasonal_factors[season]['yield_factor']
#             requirements["expected_yield_tons_per_ha"] = round(adjusted_yield, 2)
        
#         # Add intercropping recommendation if available
#         if 'intercropping_compatibility' in crop_data.columns:
#             intercrop_value = crop_data['intercropping_compatibility'].values[0]
#             if isinstance(intercrop_value, str) and intercrop_value != 'None':
#                 requirements["intercropping_recommendation"] = intercrop_value.split(',')
        
#         # Add season-specific recommendations for Rwanda's four seasons
#         if season == 'short_dry':
#             requirements["seasonal_recommendations"] = [
#                 "Implement water conservation techniques",
#                 "Consider drought-resistant varieties",
#                 "Apply mulch to reduce evaporation",
#                 "Use drip irrigation if available"
#             ]
#         elif season == 'long_rainy':
#             requirements["seasonal_recommendations"] = [
#                 "Ensure proper drainage systems to prevent waterlogging",
#                 "Monitor closely for fungal diseases",
#                 "Consider raised beds in low-lying areas",
#                 "Implement erosion control measures on slopes"
#             ]
#         elif season == 'long_dry':
#             requirements["seasonal_recommendations"] = [
#                 "Increase irrigation frequency and volume",
#                 "Use deep mulching to preserve soil moisture",
#                 "Consider shade structures for sensitive crops",
#                 "Implement windbreaks to reduce evapotranspiration"
#             ]
#         elif season == 'short_rainy':
#             requirements["seasonal_recommendations"] = [
#                 "Monitor drainage but prepare for dry spells",
#                 "Implement integrated pest management for seasonal pests",
#                 "Consider cover crops to prevent soil erosion",
#                 "Time planting to maximize use of rainfall patterns"
#             ]
            
#         # Add note about model limitations if fallbacks were used
#         if missing_models:
#             requirements["model_notes"] = f"Some models were unavailable ({', '.join(missing_models)}). Results may be less accurate."
        
#         return requirements
        
#     except Exception as e:
#         import traceback
#         error_details = traceback.format_exc()
#         print(f"Detailed error: {error_details}")
#         return Response({"error": f"An error occurred during prediction: {str(e)}"})


def predict_crop_requirements(crop_name, soil_type, altitude='mid', season='short_dry'):
    try:
        # Get the directory where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Define model directory within the project
        model_dir = os.path.join(current_dir, 'models')
        
        print(f"Looking for models in: {model_dir}")
        
        # Check if model directory exists
        if not os.path.exists(model_dir):
            return Response({"error": f"Model directory '{model_dir}' does not exist."})
            
        # Check if soil type subdirectory exists
        soil_dir = os.path.join(model_dir, soil_type)
        if not os.path.exists(soil_dir):
            # Try to find an alternative soil type
            available_soils = [d for d in os.listdir(model_dir) 
                              if os.path.isdir(os.path.join(model_dir, d))]
            if not available_soils:
                return Response({"error": "No soil type directories found in the model directory."})
            
            # Use the first available soil type as fallback
            soil_type = available_soils[0]
            soil_dir = os.path.join(model_dir, soil_type)
            print(f"Warning: Soil type '{soil_type}' not found. Using '{soil_type}' instead.")
        
        # Load the comprehensive dataset
        try:
            df = pd.read_csv(os.path.join(current_dir, 'data', 'comprehensive_crop_requirements.csv'))
        except FileNotFoundError:
            return Response({"error": "Dataset file not found."})
        
        # Get the row for this crop
        crop_data = df[df['crop'].str.lower() == crop_name.lower()]
        
        if len(crop_data) == 0:
            # Try to find a close match using fuzzy matching
            from difflib import get_close_matches
            all_crops = df['crop'].unique()
            close_matches = get_close_matches(crop_name, all_crops)
            
            if close_matches:
                crop_name = close_matches[0]
                crop_data = df[df['crop'] == crop_name]
                print(f"Warning: Crop '{crop_name}' not found. Using closest match '{crop_name}' instead.")
            else:
                return Response({"error": f"Crop '{crop_name}' not found in the dataset."})
        
        # Create input features with a copy of crop data
        input_features = crop_data.copy()
        
        # Map Rwanda's seasons to the format in the dataset
        season_mapping = {
            'short_dry': 'short_dry',      # Dec-Feb
            'long_rainy': 'long_rainy',    # Mar-May
            'long_dry': 'long_dry',        # Jun-Sep
            'short_rainy': 'short_rainy'   # Sep-Dec
        }
        
        detailed_season = season_mapping.get(season, 'short_dry')  # Default to short_dry if unknown
        
        # Add missing altitude and season columns that models might expect
        altitude_types = ['low', 'mid', 'high']
        season_types = ['dry', 'wet', 'short_dry', 'long_rainy', 'long_dry', 'short_rainy']
        
        # Generate all possible altitude-season combinations and ensure they exist in input_features
        for alt in altitude_types:
            for seas in season_types:
                col_name = f"{alt}_altitude_{seas}_adjusted"
                if col_name not in input_features.columns:
                    input_features[col_name] = 0.0  # Add with default value
                
        # Also ensure base altitude columns exist
        for alt in altitude_types:
            col_name = f"{alt}_altitude_adjusted"
            if col_name not in input_features.columns:
                input_features[col_name] = 0.0
        
        # Load the models for this soil type
        soil_models = {}
        
        # Define target variables - both general and season-specific
        base_targets = ['adjusted_nitrogen', 'adjusted_phosphorus', 'adjusted_potassium']
        
        # IMPROVED MODEL SELECTION LOGIC FOR WATER REQUIREMENTS
        water_req_key = None
        
        # First try: exact match for altitude and season
        exact_match = f"{altitude}_altitude_{detailed_season}_adjusted"
        exact_model_path = os.path.join(soil_dir, f"{exact_match}_model.joblib")
        if os.path.exists(exact_model_path):
            water_req_key = exact_match
            print(f"Found exact match model: {exact_match}")
        else:
            print(f"Could not find exact model: {exact_model_path}")
        
        # Second try: match with any season at this altitude
        if not water_req_key:
            altitude_pattern = f"{altitude}_altitude_"
            altitude_models = [m.replace("_model.joblib", "") for m in os.listdir(soil_dir) 
                            if m.startswith(altitude_pattern) and m.endswith("_model.joblib")]
            if altitude_models:
                water_req_key = altitude_models[0]
                print(f"Found altitude-specific model: {water_req_key}")
        
        # Third try: match with any altitude for this season
        if not water_req_key:
            season_pattern = f"_altitude_{detailed_season}_adjusted"
            season_models = [m.replace("_model.joblib", "") for m in os.listdir(soil_dir)
                        if m.endswith(f"{season_pattern}_model.joblib")]
            if season_models:
                water_req_key = season_models[0]
                print(f"Found season-specific model: {water_req_key}")
        
        # Fourth try: use any available water requirement model
        if not water_req_key:
            water_models = [m.replace("_model.joblib", "") for m in os.listdir(soil_dir)
                        if "_altitude_" in m and m.endswith("_adjusted_model.joblib")]
            if water_models:
                water_req_key = water_models[0]
                print(f"No specific model found. Using fallback model: {water_req_key}")
            else:
                print(f"Warning: No water requirement models found. Proceeding with nutrient predictions only.")
                water_req_key = None
        
        # Try to load all required models
        target_variables = base_targets.copy()
        if water_req_key:
            target_variables.append(water_req_key)
            
        missing_models = []
        
        for target in target_variables:
            model_path = os.path.join(soil_dir, f"{target}_model.joblib")
            if os.path.exists(model_path):
                try:
                    soil_models[target] = load(model_path)
                    print(f"Successfully loaded model: {target}")
                except Exception as e:
                    print(f"Error loading model {target}: {str(e)}")
                    missing_models.append(f"{target} (Error: {str(e)})")
            else:
                missing_models.append(target)
                print(f"Model file not found: {model_path}")
        
        # If we're missing nutrient models, try to use base models directly from dataset
        if any(target in missing_models for target in base_targets):
            print("Warning: Some nutrient models are missing. Using dataset values directly.")
            for nutrient in base_targets:
                if nutrient in missing_models and nutrient.replace('adjusted_', '') in crop_data.columns:
                    base_nutrient = nutrient.replace('adjusted_', '')
                    soil_models[nutrient] = {
                        'direct_value': float(crop_data[base_nutrient].values[0])
                    }
                    print(f"Using direct value for {nutrient}: {soil_models[nutrient]['direct_value']}")
                    missing_models.remove(nutrient)
        
        # If we're still missing crucial models after fallbacks, return error
        if missing_models and all(target in missing_models for target in base_targets):
            return Response({"error": f"Missing models for all nutrient targets: {', '.join(missing_models)}"})
        
        # Make predictions for each target variable or use direct values
        predictions = {}
        for target, model in soil_models.items():
            if isinstance(model, dict) and 'direct_value' in model:
                # Use direct value from the dataset
                predictions[target] = model['direct_value']
            else:
                # Use the model to predict
                try:
                    # Check if input_features has all columns the model expects
                    if hasattr(model, 'feature_names_in_'):
                        missing_cols = set(model.feature_names_in_) - set(input_features.columns)
                        for col in missing_cols:
                            input_features[col] = 0.0  # Add missing columns with default values
                    
                    predictions[target] = model.predict(input_features)[0]
                except Exception as e:
                    print(f"Error predicting with {target} model: {str(e)}")
                    # Use a default value based on dataset if prediction fails
                    if target.replace('adjusted_', '') in crop_data.columns:
                        base_value = crop_data[target.replace('adjusted_', '')].values[0]
                        predictions[target] = float(base_value)
                        print(f"Using default value for {target}: {predictions[target]}")
                    else:
                        # Use reasonable defaults if all else fails
                        defaults = {
                            'adjusted_nitrogen': 50.0,
                            'adjusted_phosphorus': 25.0,
                            'adjusted_potassium': 30.0
                        }
                        if target in defaults:
                            predictions[target] = defaults[target]
                            print(f"Using standard default for {target}: {predictions[target]}")
                        else:
                            # For water requirements, use a reasonable default based on season
                            water_defaults = {
                                'short_dry': 450,
                                'long_rainy': 200,
                                'long_dry': 550,
                                'short_rainy': 350
                            }
                            predictions[target] = water_defaults.get(season, 400)
                            print(f"Using seasonal default water value: {predictions[target]}")
        
        # Apply seasonal adjustments for nutrient requirements
        seasonal_factors = {
            'short_dry': {
                'nitrogen_factor': 1.0,
                'phosphorus_factor': 1.0,
                'potassium_factor': 1.0,
                'yield_factor': 1.0
            },
            'long_rainy': {
                'nitrogen_factor': 1.25,
                'phosphorus_factor': 0.9,
                'potassium_factor': 1.15,
                'yield_factor': 1.1
            },
            'long_dry': {
                'nitrogen_factor': 0.9,
                'phosphorus_factor': 1.1,
                'potassium_factor': 0.95,
                'yield_factor': 0.9
            },
            'short_rainy': {
                'nitrogen_factor': 1.15,
                'phosphorus_factor': 0.95,
                'potassium_factor': 1.05,
                'yield_factor': 1.05
            }
        }
        
        # Apply seasonal adjustment factors
        nitrogen = predictions.get('adjusted_nitrogen', 50.0) * seasonal_factors[season]['nitrogen_factor']
        phosphorus = predictions.get('adjusted_phosphorus', 25.0) * seasonal_factors[season]['phosphorus_factor']
        potassium = predictions.get('adjusted_potassium', 30.0) * seasonal_factors[season]['potassium_factor']
        
        # Select the water requirement based on altitude and season
        water_requirement = predictions.get(water_req_key, None)
        
        # If water_requirement is still None, provide a default based on season and altitude
        if water_requirement is None:
            # Base defaults by season (in mm)
            water_defaults = {
                'short_dry': 450,
                'long_rainy': 200,
                'long_dry': 550,
                'short_rainy': 350
            }
            
            # Altitude adjustment factors
            altitude_factors = {
                'low': 1.2,  # Higher water requirement in low altitude
                'mid': 1.0,  # Base reference
                'high': 0.8   # Lower water requirement in high altitude (cooler, less evaporation)
            }
            
            # Use the default for the season, adjusted by altitude
            base_water = water_defaults.get(season, 400)
            altitude_factor = altitude_factors.get(altitude, 1.0)
            water_requirement = base_water * altitude_factor
            print(f"Using calculated default water requirement: {water_requirement} mm")
        
        # Format the results
        requirements = {
            "crop": crop_name,
            "soil_type": soil_type,
            "season": season,
            "altitude": altitude,
            "requirements": {
                "nitrogen_kg_per_ha": round(nitrogen, 2),
                "phosphorus_kg_per_ha": round(phosphorus, 2),
                "potassium_kg_per_ha": round(potassium, 2),
                "water_requirement_mm": round(water_requirement, 2) if water_requirement else None,
            }
        }
        
        # Add optional fields if they exist in the dataset
        if 'optimal_ph' in crop_data:
            requirements["requirements"]["optimal_ph"] = float(crop_data['optimal_ph'].values[0])
        
        if 'min_sunlight_hours' in crop_data:
            requirements["requirements"]["min_sunlight_hours"] = int(crop_data['min_sunlight_hours'].values[0])
        
        # Add planting information if available
        planting_fields = ['row_spacing_cm', 'plant_spacing_cm', 'planting_depth_cm']
        if all(field in crop_data.columns for field in planting_fields):
            planting_info = {
                "row_spacing_cm": int(crop_data['row_spacing_cm'].values[0]),
                "plant_spacing_cm": int(crop_data['plant_spacing_cm'].values[0]),
                "planting_depth_cm": int(crop_data['planting_depth_cm'].values[0]),
            }
            requirements["requirements"]["planting_info"] = planting_info
        
        # Add expected yield if available
        if 'optimal_yield' in crop_data.columns:
            base_yield = float(crop_data['optimal_yield'].values[0])
            # Apply yield factor based on season
            adjusted_yield = base_yield * seasonal_factors[season]['yield_factor']
            requirements["expected_yield_tons_per_ha"] = round(adjusted_yield, 2)
        
        # Add intercropping recommendation if available
        if 'intercropping_compatibility' in crop_data.columns:
            intercrop_value = crop_data['intercropping_compatibility'].values[0]
            if isinstance(intercrop_value, str) and intercrop_value != 'None':
                requirements["intercropping_recommendation"] = intercrop_value.split(',')
        
        # Add season-specific recommendations for Rwanda's four seasons
        if season == 'short_dry':
            requirements["seasonal_recommendations"] = [
                "Implement water conservation techniques",
                "Consider drought-resistant varieties",
                "Apply mulch to reduce evaporation",
                "Use drip irrigation if available"
            ]
        elif season == 'long_rainy':
            requirements["seasonal_recommendations"] = [
                "Ensure proper drainage systems to prevent waterlogging",
                "Monitor closely for fungal diseases",
                "Consider raised beds in low-lying areas",
                "Implement erosion control measures on slopes"
            ]
        elif season == 'long_dry':
            requirements["seasonal_recommendations"] = [
                "Increase irrigation frequency and volume",
                "Use deep mulching to preserve soil moisture",
                "Consider shade structures for sensitive crops",
                "Implement windbreaks to reduce evapotranspiration"
            ]
        elif season == 'short_rainy':
            requirements["seasonal_recommendations"] = [
                "Monitor drainage but prepare for dry spells",
                "Implement integrated pest management for seasonal pests",
                "Consider cover crops to prevent soil erosion",
                "Time planting to maximize use of rainfall patterns"
            ]
            
        # Add note about model limitations if fallbacks were used
        if missing_models:
            requirements["model_notes"] = f"Some models were unavailable ({', '.join(missing_models)}). Results may be less accurate."
        
        return requirements
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Detailed error: {error_details}")
        return Response({"error": f"An error occurred during prediction: {str(e)}"})
    
    
    
    
def make_crop_requirement_prediction():
    print("==== Rwanda Agriculture Advisory System ====")
    print("This system predicts soil type and crop requirements based on location and crop information.")
    
    # Collect user inputs once
    district_name = input("\nEnter district name: ")
    sector_name = input("Enter sector name: ")
    
    # Predict soil texture
    print("\nAnalyzing soil data for this location...")
    soil_prediction = predict_soil_texture(district_name, sector_name)
    
    if isinstance(soil_prediction, str) and soil_prediction.startswith("Error"):
        print(f"\n❌ {soil_prediction}")
        return
    
    print(f"\n✅ Predicted soil texture for {district_name}, {sector_name}: {soil_prediction}")
    
    # Collect crop information
    crop_name = input("\nEnter crop name (e.g., Rice, Maize): ")
    
    # print("\nAltitude levels:")
    # print("1. Low altitude")
    # print("2. Mid altitude")
    # print("3. High altitude")
    altitude_choice = input("Choose altitude (1-3): ")
    
    altitude_mapping = {
        '1': 'low',
        '2': 'mid',
        '3': 'high'
    }
    
    altitude = altitude_mapping.get(altitude_choice, 'mid')
    
    # Rwanda's four seasons
    # print("\nRwanda's seasons:")
    # print("1. Short dry season (mid-December to mid-March)")
    # print("2. Long rainy season (mid-March to mid-May)")
    # print("3. Long dry season (mid-May to mid-September)")
    # print("4. Short rainy season (mid-September to mid-December)")
    
    season_choice = input("Choose season (1-4): ")
    
    # Map season choice to appropriate format
    season_mapping = {
        '1': 'short_dry',
        '2': 'long_rainy',
        '3': 'long_dry',
        '4': 'short_rainy'
    }
    
    # Full season names for display
    season_names = {
        '1': 'Short dry season',
        '2': 'Long rainy season',
        '3': 'Long dry season',
        '4': 'Short rainy season'
    }
    
    season = season_mapping.get(season_choice, 'short_dry')
    season_name = season_names.get(season_choice, 'Short dry season')
    
    # Make crop requirement prediction
    print("\nGenerating crop requirements for these conditions...")
    prediction = predict_crop_requirements(crop_name, soil_prediction, altitude=altitude, season=season)
    
    # Display results
    if 'error' in prediction:
        print(f"\n❌ Error in prediction: {prediction['error']}")
    else:
        # print("\n" + "="*70)
        # print(f"RWANDA AGRICULTURAL ADVISORY SYSTEM - PREDICTION RESULTS")
        # print("="*70)
        # print(f"Location: {district_name} District, {sector_name} Sector")
        # print(f"Soil Type: {prediction['soil_type']}")
        # print(f"Crop: {prediction['crop']}")
        # print(f"Season: {season_name}")
        # print(f"Altitude: {altitude.capitalize()}")
        
        print("\n" + "="*70)
        print("CROP REQUIREMENTS")
        print("="*70)
        print(f"Nitrogen: {prediction['requirements']['nitrogen_kg_per_ha']} kg/ha")
        print(f"Phosphorus: {prediction['requirements']['phosphorus_kg_per_ha']} kg/ha")
        print(f"Potassium: {prediction['requirements']['potassium_kg_per_ha']} kg/ha")
        print(f"Water: {prediction['requirements']['water_requirement_mm']} mm")
        
        # if 'optimal_ph' in prediction['requirements']:
        #     print(f"Optimal pH: {prediction['requirements']['optimal_ph']}")
        
        if 'planting_info' in prediction['requirements']:
            print("\n" + "="*70)
            print("PLANTING INFORMATION")
            print("="*70)
            planting = prediction['requirements']['planting_info']
            print(f"Row Spacing: {planting['row_spacing_cm']} cm")
            print(f"Plant Spacing: {planting['plant_spacing_cm']} cm")
            # print(f"Planting Depth: {planting['planting_depth_cm']} cm")
        
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

