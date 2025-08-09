import joblib
import sys
import os

import os
# print(f"Current working directory: {os.getcwd()}")
# print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")
# print(f"Models directory should be: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')}")

current_dir = os.path.dirname(os.path.__file__)
models_dir = os.path.join(current_dir, 'models')


def load_model_components():
    """Load all required model components."""
    try:
        # Get the current directory (where this script is)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Define paths
        model_path = os.path.join(current_dir, 'models', 'rwanda_altitude_model.joblib')
        district_encoder_path = os.path.join(current_dir, 'models', 'district_encoder.joblib')
        sector_encoder_path = os.path.join(current_dir, 'models', 'sector_encoder.joblib')
        altitude_mapping_path = os.path.join(current_dir, 'models', 'altitude_mapping.joblib')
        
        # Actually load the files
        model = joblib.load(model_path)
        district_encoder = joblib.load(district_encoder_path)
        sector_encoder = joblib.load(sector_encoder_path)
        altitude_mapping = joblib.load(altitude_mapping_path)
        
        return model, district_encoder, sector_encoder, altitude_mapping
    except FileNotFoundError as e:
        print(f"Error: Required model files not found. {e}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Looking for models in: {os.path.join(os.getcwd(), 'models')}")
        return None, None, None, None
    
    
    
def predict_altitude(district_name, sector_name):
    """Predict altitude level for a given district and sector."""
    # Load the model and encoders
    model, district_encoder, sector_encoder, altitude_mapping = load_model_components()
    
    if model is None:
        return "Failed to load model components"
    
    # Check if district exists in our encoded data
    try:
        if district_name not in district_encoder.classes_:
            return f"District '{district_name}' not found in the dataset"
        
        # Encode the input
        district_enc = district_encoder.transform([district_name])[0]
        
        # Check if sector exists and encode it
        try:
            sector_enc = sector_encoder.transform([sector_name])[0]
        except ValueError:
            return f"Sector '{sector_name}' not found in the dataset"
        
        # Make prediction
        prediction = model.predict([[district_enc, sector_enc]])[0]
        
        # Map back to original altitude level
        altitude_level = altitude_mapping[prediction]
        
        return altitude_level
    
    except Exception as e:
        return f"Error during prediction: {str(e)}"

def list_available_districts():
    """List all available districts in the model."""
    _, district_encoder, _, _ = load_model_components()
    
    if district_encoder is None:
        return []
    
    return sorted(district_encoder.classes_)

def list_sectors_in_district(district_name):
    """List all sectors in a given district."""
    model, district_encoder, sector_encoder, _ = load_model_components()
    
    if district_encoder is None:
        return []
    
    # Load the original dataset to get sectors for a district
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dataset_path = os.path.join(current_dir, 'models', 'cleaned_data.joblib')
        dataset = joblib.load(dataset_path)
        
        if district_name in dataset['District'].values:
            return sorted(dataset[dataset['District'] == district_name]['Sector'].unique())
        else:
            print(f"District '{district_name}' not found")
            return []
    except Exception as e:
        print(f"Could not load sector information: {e}")
        return []


     
