import pandas as pd
from joblib import load
import os


# print(f"Current working directory: {os.getcwd()}")
# print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")
# print(f"Models directory should be: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')}")

current_dir = os.path.dirname(os.path.__file__)
models_dir = os.path.join(current_dir, 'models')


def predict_soil_texture(district, sector):

    try:
        # Load the model and preprocessor
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Load the model and preprocessor
        model_path = os.path.join(current_dir, 'models', 'best_soil_texture_model.joblib')

        preprocessor_path = os.path.join(current_dir, 'models', 'soil_preprocessor.joblib')
        
        if not os.path.exists(model_path) or not os.path.exists(preprocessor_path):
            return "Error: Model or preprocessor file not found."
        
        model = load(model_path)
        preprocessor = load(preprocessor_path)
        
        # Load the original dataset to get coordinates
        try:
            dataset = pd.read_csv(os.path.join(current_dir, 'data', 'rwanda_soilTypes.csv'))
            
            # Find average coordinates for the specific sector
            sector_data = dataset[(dataset['District'] == district) & (dataset['Sector'] == sector)]
            
            if len(sector_data) > 0:
                # Use average coordinates for the sector
                latitude = sector_data['Latitude'].mean()
                longitude = sector_data['Longitude'].mean()
            else:
                return f"Error: The combination of District '{district}' and Sector '{sector}' was not found in the dataset."
                
        except FileNotFoundError:
            return "Error: Dataset file not found."
        
        # Create a dataframe with the input data
        input_data = pd.DataFrame({
            'District': [district],
            'Latitude': [latitude],
            'Longitude': [longitude]
        })

        # Get a sample of the training data to fit the preprocessor
        training_data = dataset[['District', 'Latitude', 'Longitude']]
        
        # Fit the preprocessor on the training data
        preprocessor.fit(training_data)
        
        # Now transform the input data
        X_processed = preprocessor.transform(input_data)
        
        # Make the prediction
        prediction = model.predict(X_processed)[0]
        
        print("Predicted Soil type type is:", prediction)
        
        return prediction.lower()
    
    except Exception as e:
        return f"Error during prediction: {str(e)}"
