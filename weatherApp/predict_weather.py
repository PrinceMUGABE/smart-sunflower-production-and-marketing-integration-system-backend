import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
import joblib
import os
from tensorflow.keras.losses import MeanSquaredError



# Set up output directories
os.makedirs('plots', exist_ok=True)
os.makedirs('reports', exist_ok=True)



# Set random seed for reproducibility
np.random.seed(42)

# Define all districts in Rwanda with their specific climate characteristics
RWANDA_DISTRICTS = {
    # KIGALI PROVINCE
    'Nyarugenge': {
        'province': 'Kigali',
        'elevation': 1567,  # meters
        'temp_offset': 0.2,  # slightly warmer than Kigali average
        'rainfall_factor': 1.0,
        'humidity_offset': 0,
        'coordinates': (-1.94, 30.06)  # lat, long
    },
    'Gasabo': {
        'province': 'Kigali',
        'elevation': 1551,
        'temp_offset': 0,  # baseline for Kigali
        'rainfall_factor': 1.0,
        'humidity_offset': 0,
        'coordinates': (-1.89, 30.12)
    },
    'Kicukiro': {
        'province': 'Kigali',
        'elevation': 1490,
        'temp_offset': 0.3,  # warmer
        'rainfall_factor': 0.95,  # slightly less rainfall
        'humidity_offset': -1,
        'coordinates': (-1.97, 30.11)
    },
    
    # NORTHERN PROVINCE
    'Musanze': {
        'province': 'Northern',
        'elevation': 1850,
        'temp_offset': -2.5,  # cooler due to elevation and proximity to volcanoes
        'rainfall_factor': 1.3,  # higher rainfall
        'humidity_offset': 2,
        'coordinates': (-1.50, 29.63)
    },
    'Burera': {
        'province': 'Northern',
        'elevation': 2100,
        'temp_offset': -3.0,  # very cool climate
        'rainfall_factor': 1.35,  # high rainfall
        'humidity_offset': 3,
        'coordinates': (-1.35, 29.83)
    },
    'Gakenke': {
        'province': 'Northern',
        'elevation': 1700,
        'temp_offset': -1.5,
        'rainfall_factor': 1.25,
        'humidity_offset': 1,
        'coordinates': (-1.70, 29.78)
    },
    'Gicumbi': {
        'province': 'Northern',
        'elevation': 2200,
        'temp_offset': -3.2,  # one of the coolest districts
        'rainfall_factor': 1.3,
        'humidity_offset': 2,
        'coordinates': (-1.70, 30.10)
    },
    'Rulindo': {
        'province': 'Northern',
        'elevation': 1850,
        'temp_offset': -2.0,
        'rainfall_factor': 1.2,
        'humidity_offset': 1,
        'coordinates': (-1.72, 29.98)
    },
    
    # EASTERN PROVINCE
    'Nyagatare': {
        'province': 'Eastern',
        'elevation': 1400,
        'temp_offset': 2.0,  # warmer
        'rainfall_factor': 0.7,  # drier
        'humidity_offset': -5,  # less humid
        'coordinates': (-1.30, 30.33)
    },
    'Gatsibo': {
        'province': 'Eastern',
        'elevation': 1450,
        'temp_offset': 1.8,
        'rainfall_factor': 0.75,
        'humidity_offset': -4,
        'coordinates': (-1.58, 30.45)
    },
    'Kayonza': {
        'province': 'Eastern',
        'elevation': 1470,
        'temp_offset': 1.5,
        'rainfall_factor': 0.8,
        'humidity_offset': -3,
        'coordinates': (-1.85, 30.65)
    },
    'Rwamagana': {
        'province': 'Eastern',
        'elevation': 1550,
        'temp_offset': 1.0,
        'rainfall_factor': 0.9,
        'humidity_offset': -2,
        'coordinates': (-1.95, 30.43)
    },
    'Kirehe': {
        'province': 'Eastern',
        'elevation': 1350,
        'temp_offset': 2.2,  # hot and dry
        'rainfall_factor': 0.65,
        'humidity_offset': -6,
        'coordinates': (-2.27, 30.73)
    },
    'Ngoma': {
        'province': 'Eastern',
        'elevation': 1600,
        'temp_offset': 1.0,
        'rainfall_factor': 0.85,
        'humidity_offset': -3,
        'coordinates': (-2.15, 30.53)
    },
    'Bugesera': {
        'province': 'Eastern',
        'elevation': 1400,
        'temp_offset': 1.7,
        'rainfall_factor': 0.7,
        'humidity_offset': -4,
        'coordinates': (-2.15, 30.25)
    },
    'Nyabihu': {
        'province': 'Western',
        'elevation': 1900,
        'temp_offset': -2.7,
        'rainfall_factor': 1.4,  # very high rainfall
        'humidity_offset': 4,
        'coordinates': (-1.65, 29.50)
    },
    
    # WESTERN PROVINCE
    'Rubavu': {
        'province': 'Western',
        'elevation': 1460,
        'temp_offset': 1.0,  # warmer due to Lake Kivu
        'rainfall_factor': 1.1,
        'humidity_offset': 8,  # higher humidity due to lake
        'coordinates': (-1.68, 29.32)
    },
    'Karongi': {
        'province': 'Western',
        'elevation': 1500,
        'temp_offset': 0.5,
        'rainfall_factor': 1.1,
        'humidity_offset': 5,  # lake effect
        'coordinates': (-2.10, 29.40)
    },
    'Rutsiro': {
        'province': 'Western',
        'elevation': 1700,
        'temp_offset': -0.5,
        'rainfall_factor': 1.2,
        'humidity_offset': 3,
        'coordinates': (-1.95, 29.33)
    },
    'Ngororero': {
        'province': 'Western',
        'elevation': 1850,
        'temp_offset': -1.0,
        'rainfall_factor': 1.25,
        'humidity_offset': 2,
        'coordinates': (-1.78, 29.56)
    },
    'Rusizi': {
        'province': 'Western',
        'elevation': 1500,
        'temp_offset': 0.8,
        'rainfall_factor': 1.15,
        'humidity_offset': 6,  # lake effect from Lake Kivu
        'coordinates': (-2.60, 29.00)
    },
    'Nyamasheke': {
        'province': 'Western',
        'elevation': 1550,
        'temp_offset': 0.5,
        'rainfall_factor': 1.2,
        'humidity_offset': 5,  # lake effect
        'coordinates': (-2.33, 29.15)
    },
    
    # SOUTHERN PROVINCE
    'Huye': {
        'province': 'Southern',
        'elevation': 1768,
        'temp_offset': -1.0,  # slightly cooler
        'rainfall_factor': 1.2,  # more rainfall
        'humidity_offset': 5,
        'coordinates': (-2.60, 29.74)
    },
    'Nyanza': {
        'province': 'Southern',
        'elevation': 1700,
        'temp_offset': -0.8,
        'rainfall_factor': 1.15,
        'humidity_offset': 4,
        'coordinates': (-2.38, 29.75)
    },
    'Gisagara': {
        'province': 'Southern',
        'elevation': 1650,
        'temp_offset': -0.5,
        'rainfall_factor': 1.1,
        'humidity_offset': 3,
        'coordinates': (-2.60, 29.85)
    },
    'Nyaruguru': {
        'province': 'Southern',
        'elevation': 1900,
        'temp_offset': -1.7,
        'rainfall_factor': 1.25,
        'humidity_offset': 4,
        'coordinates': (-2.73, 29.52)
    },
    'Nyamagabe': {
        'province': 'Southern',
        'elevation': 1950,
        'temp_offset': -1.8,  # cool highlands
        'rainfall_factor': 1.3,
        'humidity_offset': 5,
        'coordinates': (-2.47, 29.56)
    },
    'Ruhango': {
        'province': 'Southern',
        'elevation': 1650,
        'temp_offset': -0.6,
        'rainfall_factor': 1.1,
        'humidity_offset': 3,
        'coordinates': (-2.22, 29.78)
    },
    'Muhanga': {
        'province': 'Southern',
        'elevation': 1750,
        'temp_offset': -1.2,
        'rainfall_factor': 1.15,
        'humidity_offset': 3,
        'coordinates': (-2.08, 29.75)
    },
    'Kamonyi': {
        'province': 'Southern',
        'elevation': 1600,
        'temp_offset': -0.3,
        'rainfall_factor': 1.05,
        'humidity_offset': 1,
        'coordinates': (-2.00, 29.88)
    }
}

def generate_location_weather_data(start_date='2022-01-01', n_days=1095):  # ~3 years of data
    """
    Generate synthetic weather data for multiple locations in Rwanda
    """
    dates = [datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=i) for i in range(n_days)]
    
    all_locations_data = []
    
    for location, attributes in RWANDA_DISTRICTS.items():
        # Base values adjusted for location
        temp_min_base = 15 + attributes['temp_offset']  # Celsius
        temp_max_base = 30 + attributes['temp_offset']  # Celsius
        humidity_base = 70 + attributes['humidity_offset']  # Percentage
        rainfall_factor = attributes['rainfall_factor']
        elevation = attributes['elevation']
        
        # Lists to store location data
        temp_min = []
        temp_max = []
        temp_avg = []
        humidity = []
        rainfall = []
        wind_speed = []
        sunshine_hours = []
        
        # For correlation between days (weather patterns)
        prev_temp = temp_min_base + (temp_max_base - temp_min_base) / 2
        prev_humidity = humidity_base
        prev_rainfall = 0
        
        for date in dates:
            month = date.month
            day_of_year = date.timetuple().tm_yday
            
            # Seasonal temperature variations (cooler in June-August, warmer in Feb-March)
            seasonal_temp_effect = -3 * np.sin(2 * np.pi * (day_of_year - 15) / 365)
            
            # Temperature persistence (correlation with previous day)
            persistence_factor = 0.7
            random_factor = 1 - persistence_factor
            
            # Random daily variations with persistence from previous day
            daily_temp_variation = persistence_factor * (prev_temp - temp_min_base - temp_max_base) / 2 + \
                                random_factor * np.random.normal(0, 1.5)
            
            # Calculate actual temperatures
            day_temp_min = temp_min_base + seasonal_temp_effect + daily_temp_variation - random.uniform(0, 3)
            day_temp_max = temp_max_base + seasonal_temp_effect + daily_temp_variation + random.uniform(0, 3)
            day_temp_avg = (day_temp_min + day_temp_max) / 2
            
            # Update previous temperature for next iteration
            prev_temp = day_temp_avg
            
            # Humidity - higher in rainy seasons and with elevation effects
            # March-May and September-December have higher humidity
            humidity_seasonal = 5 * (1 if (month >= 3 and month <= 5) or (month >= 9 and month <= 12) else -1)
            
            # Humidity has some persistence from previous day
            humidity_persistence = 0.6
            day_humidity = humidity_base + humidity_seasonal + \
                          humidity_persistence * (prev_humidity - humidity_base) + \
                          (1 - humidity_persistence) * np.random.normal(0, 5)
            
            day_humidity = max(40, min(100, day_humidity))  # Constrain between 40-100%
            prev_humidity = day_humidity
            
            # Rainfall patterns - two rainy seasons in Rwanda
            # Major rainy season: March-May
            # Minor rainy season: September-December
            is_rainy_season = (month >= 3 and month <= 5) or (month >= 9 and month <= 12)
            
            # Rainfall probability based on season and previous day's rainfall
            base_rain_probability = 0.6 if is_rainy_season else 0.2
            # Higher chance of rain if it rained yesterday (weather patterns)
            rain_persistence = 0.2 if prev_rainfall > 0 else 0
            rain_probability = min(0.9, base_rain_probability + rain_persistence)
            
            if random.random() < rain_probability:
                if month >= 3 and month <= 5:  # Major rainy season
                    day_rainfall = max(0, np.random.gamma(5, 5) * rainfall_factor + np.random.normal(0, 2))
                elif month >= 9 and month <= 12:  # Minor rainy season
                    day_rainfall = max(0, np.random.gamma(3, 4) * rainfall_factor + np.random.normal(0, 2))
                else:  # Dry season, occasional rain
                    day_rainfall = max(0, np.random.gamma(1, 2) * rainfall_factor + np.random.normal(0, 1))
            else:
                day_rainfall = 0
                
            # Update previous rainfall
            prev_rainfall = day_rainfall
            
            # Wind speed (affected by elevation and terrain)
            # Higher elevations tend to have higher wind speeds
            elevation_factor = (elevation - 1400) / 1000  # Normalized to range of elevations
            day_wind_speed = max(0, np.random.gamma(2, 1.5) + elevation_factor + np.random.normal(0, 0.5))
            
            # Sunshine hours (negatively correlated with rainfall)
            potential_sunshine = 12  # Maximum possible
            if day_rainfall > 10:
                day_sunshine = max(0, potential_sunshine * (0.3 + np.random.normal(0, 0.1)))
            elif day_rainfall > 0:
                day_sunshine = max(0, potential_sunshine * (0.6 + np.random.normal(0, 0.15)))
            else:
                day_sunshine = max(0, potential_sunshine * (0.9 + np.random.normal(0, 0.1)))
            
            # Append values to lists
            temp_min.append(round(day_temp_min, 1))
            temp_max.append(round(day_temp_max, 1))
            temp_avg.append(round(day_temp_avg, 1))
            humidity.append(round(day_humidity, 1))
            rainfall.append(round(day_rainfall, 1))
            wind_speed.append(round(day_wind_speed, 1))
            sunshine_hours.append(round(day_sunshine, 1))
        
        # Create location-specific DataFrame
        location_df = pd.DataFrame({
            'date': dates,
            'location': location,
            'latitude': attributes['coordinates'][0],
            'longitude': attributes['coordinates'][1],
            'elevation_m': elevation,
            'temp_min_c': temp_min,
            'temp_max_c': temp_max,
            'temp_avg_c': temp_avg,
            'humidity_pct': humidity,
            'rainfall_mm': rainfall,
            'wind_speed_kmh': wind_speed,
            'sunshine_hours': sunshine_hours
        })
        
        all_locations_data.append(location_df)
    
    # Combine all location data
    combined_df = pd.concat(all_locations_data, ignore_index=True)
    
    # Add some missing values to make dataset more realistic
    for col in combined_df.columns:
        if col not in ['date', 'location', 'latitude', 'longitude', 'elevation_m']:
            # Add 1% missing data
            mask = np.random.random(size=len(combined_df)) < 0.01
            combined_df.loc[mask, col] = np.nan
    
    # Add derived features
    combined_df['month'] = combined_df['date'].dt.month
    combined_df['day'] = combined_df['date'].dt.day
    combined_df['day_of_year'] = combined_df['date'].dt.dayofyear
    combined_df['year'] = combined_df['date'].dt.year
    combined_df['is_rainy_season'] = combined_df['month'].apply(lambda x: 1 if (x >= 3 and x <= 5) or (x >= 9 and x <= 12) else 0)
    
    return combined_df

def clean_weather_data(data):
    """
    Clean and preprocess the weather data
    """
    # Make a copy to avoid modifying the original
    df = data.copy()
    
    # Handle missing values by location and date
    for location in df['location'].unique():
        location_data = df[df['location'] == location]
        
        for col in df.columns:
            if col not in ['date', 'location', 'latitude', 'longitude', 'elevation_m', 'month', 'day', 'day_of_year', 'year', 'is_rainy_season']:
                # Use interpolation for time series data
                df.loc[df['location'] == location, col] = location_data[col].interpolate(method='linear')
    
    # Fill any remaining missing values
    df = df.ffill().bfill()  # Using ffill and bfill instead of deprecated method param
    
    # Check for and remove duplicates
    df = df.drop_duplicates(subset=['date', 'location'], keep='first')
    
    # Sort by location and date
    df = df.sort_values(['location', 'date'])
    
    # Add lag features for key weather variables by location
    for location in df['location'].unique():
        location_mask = df['location'] == location
        
        for lag in [1, 3, 7]:
            df.loc[location_mask, f'temp_avg_lag{lag}'] = df.loc[location_mask, 'temp_avg_c'].shift(lag)
            df.loc[location_mask, f'rainfall_lag{lag}'] = df.loc[location_mask, 'rainfall_mm'].shift(lag)
            df.loc[location_mask, f'humidity_lag{lag}'] = df.loc[location_mask, 'humidity_pct'].shift(lag)
        
        # Create rolling mean features
        df.loc[location_mask, 'temp_avg_rolling7'] = df.loc[location_mask, 'temp_avg_c'].rolling(window=7).mean()
        df.loc[location_mask, 'rainfall_rolling7'] = df.loc[location_mask, 'rainfall_mm'].rolling(window=7).mean()
        df.loc[location_mask, 'humidity_rolling7'] = df.loc[location_mask, 'humidity_pct'].rolling(window=7).mean()
    
    # Convert location to one-hot encoding for model input
    location_dummies = pd.get_dummies(df['location'], prefix='loc')
    df = pd.concat([df, location_dummies], axis=1)
    
    # Drop the first 7 rows for each location which will have NaN values due to lag/rolling features
    rows_to_drop = []
    for location in df['location'].unique():
        location_indices = df[df['location'] == location].index
        rows_to_drop.extend(location_indices[:7])
    
    df = df.drop(rows_to_drop).reset_index(drop=True)
    
    return df

def plot_regional_weather_patterns(data):
    """
    Plot weather patterns across different regions
    """
    # Create directory for plots if it doesn't exist
    if not os.path.exists('plots'):
        os.makedirs('plots')
    
    # Plot temperature comparison across regions
    plt.figure(figsize=(15, 8))
    for location in data['location'].unique():
        location_data = data[data['location'] == location]
        plt.plot(location_data['date'], location_data['temp_avg_c'], label=location)
    
    plt.title('Average Temperature Comparison Across Regions')
    plt.xlabel('Date')
    plt.ylabel('Temperature (°C)')
    plt.legend()
    plt.savefig('plots/regional_temperature_comparison.png')
    
    # Plot rainfall comparison
    plt.figure(figsize=(15, 8))
    
    # Compute monthly rainfall by region
    monthly_rain = data.groupby(['location', 'year', 'month'])['rainfall_mm'].sum().reset_index()
    monthly_rain['yearmonth'] = monthly_rain['year'].astype(str) + '-' + monthly_rain['month'].astype(str).str.zfill(2)
    
    # Get unique yearmonth values for x-axis
    yearmonths = sorted(monthly_rain['yearmonth'].unique())
    
    # Plot for each location
    for location in monthly_rain['location'].unique():
        location_data = monthly_rain[monthly_rain['location'] == location]
        plt.plot(location_data['yearmonth'], location_data['rainfall_mm'], label=location, marker='o')
    
    plt.title('Monthly Rainfall Comparison Across Regions')
    plt.xlabel('Year-Month')
    plt.ylabel('Total Rainfall (mm)')
    plt.xticks(rotation=90)
    plt.legend()
    plt.tight_layout()
    plt.savefig('plots/regional_rainfall_comparison.png')
    
    # Plot humidity comparison - boxplot by region
    plt.figure(figsize=(12, 8))
    sns.boxplot(x='location', y='humidity_pct', data=data)
    plt.title('Humidity Distribution by Region')
    plt.xlabel('Region')
    plt.ylabel('Humidity (%)')
    plt.savefig('plots/regional_humidity_boxplot.png')
    
    # Plot temperature by elevation
    plt.figure(figsize=(10, 6))
    avg_temp_by_location = data.groupby('location')[['temp_avg_c', 'elevation_m']].mean().reset_index()
    plt.scatter(avg_temp_by_location['elevation_m'], avg_temp_by_location['temp_avg_c'], s=100)
    
    # Label each point with the location name
    for i, row in avg_temp_by_location.iterrows():
        plt.annotate(row['location'], (row['elevation_m'], row['temp_avg_c']), 
                     xytext=(5, 5), textcoords='offset points')
    
    plt.title('Average Temperature vs. Elevation')
    plt.xlabel('Elevation (meters)')
    plt.ylabel('Average Temperature (°C)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.savefig('plots/temperature_vs_elevation.png')

def prepare_location_time_series_data(data, target_col, lookback=7):
    """
    Prepare sequences for LSTM model with location features
    
    Args:
        data: DataFrame containing time series data with location information
        target_col: Target column to predict
        lookback: Number of previous time steps to use as input variables
    
    Returns:
        X: Input sequences
        y: Target values
        scaler: Fitted scaler for features
        feature_cols: List of feature column names
        location_encoder: Dictionary mapping locations to their one-hot encoded columns
    """
    
    # Get location-related columns (one-hot encoded)
    location_columns = [col for col in data.columns if col.startswith('loc_')]
    
    # Create a mapping of locations to their one-hot columns for later use
    location_encoder = {}
    for loc in data['location'].unique():
        loc_col = f'loc_{loc}'
        if loc_col in data.columns:
            location_encoder[loc] = loc_col
    
    # Select features for the model
    feature_cols = [
        'temp_avg_c', 'humidity_pct', 'rainfall_mm', 
        'wind_speed_kmh', 'sunshine_hours', 
        'month', 'day_of_year', 'elevation_m',
        'temp_avg_lag1', 'rainfall_lag1', 'humidity_lag1'
    ]
    
    # Add location columns to features
    feature_cols.extend(location_columns)
    
    # Scale the data (excluding one-hot encoded location columns)
    numerical_cols = [col for col in feature_cols if col not in location_columns]
    scaler = MinMaxScaler()
    
    # Create a DataFrame to hold scaled data
    scaled_df = data.copy()
    scaled_df[numerical_cols] = scaler.fit_transform(data[numerical_cols])
    
    # Initialize lists for X and y
    X_list = []
    y_list = []
    
    # Group by location and create sequences
    for location in data['location'].unique():
        location_data = scaled_df[scaled_df['location'] == location]
        location_features = location_data[feature_cols].values
        location_target = data[data['location'] == location][target_col].values
        
        # Create sequences for this location
        for i in range(lookback, len(location_features)):
            X_list.append(location_features[i-lookback:i])
            y_list.append(location_target[i])
    
    # Convert lists to numpy arrays
    X = np.array(X_list)
    y = np.array(y_list)
    
    # Handle any NaN values
    X = np.nan_to_num(X)
    y = np.nan_to_num(y)
    
    print("X shape:", X.shape)
    print("y shape:", y.shape)
    print("X dtype:", X.dtype)
    print("y dtype:", y.dtype)
    
    return X, y, scaler, feature_cols, location_encoder


def train_location_lstm_models(cleaned_data, lookback=14, units=64, epochs=20, batch_size=32):
    """
    Prepare data and train LSTM models for multiple weather targets (temp, rainfall, humidity)
    
    Args:
        cleaned_data: DataFrame with cleaned weather data
        lookback: Number of previous time steps to use
        units: Number of LSTM units
        epochs: Number of training epochs
        batch_size: Batch size for training
    
    Returns:
        models: Dictionary containing trained models
        scalers: Dictionary containing fitted scalers
        features: Dictionary containing feature lists
        location_encoders: Dictionary containing location encoders
    """
    models = {}
    scalers = {}
    features = {}
    location_encoders = {}
    
    # Train models for each target
    for target_col, target_short in zip(['temp_avg_c', 'rainfall_mm', 'humidity_pct'], 
                                       ['temp', 'rainfall', 'humidity']):
        print(f"\nPreparing data for {target_short} prediction...")
        
        # Prepare data for this target
        X, y, scaler, feature_cols, location_encoder = prepare_location_time_series_data(
            cleaned_data, target_col=target_col, lookback=lookback)
        
        print(f"\nTraining LSTM model for {target_short} prediction...")
        
        # Split into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        # Convert to float32 for TensorFlow
        X_train = X_train.astype(np.float32)
        y_train = y_train.astype(np.float32)
        X_test = X_test.astype(np.float32)
        y_test = y_test.astype(np.float32)
        
        # Build the LSTM model
        model = Sequential()
        model.add(LSTM(units=units, return_sequences=True, input_shape=(X.shape[1], X.shape[2])))
        model.add(Dropout(0.2))
        model.add(LSTM(units=units))
        model.add(Dropout(0.2))
        model.add(Dense(1))
        
        model.compile(optimizer='adam', loss='mse')
        
        # Check for NaN values
        print("X contains NaN:", np.isnan(X_train).any())
        print("y contains NaN:", np.isnan(y_train).any())
        
        # Train the model
        history = model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            verbose=1
        )
        
        # Evaluate the model
        loss = model.evaluate(X_test, y_test, verbose=0)
        print(f'Test MSE for {target_short}: {loss}')
        
        # Save model and artifacts
        model.save(f'models/location_lstm_{target_short}_model.h5')
        joblib.dump(scaler, f'models/location_scaler_{target_short}.pkl')
        with open(f'models/location_features_{target_short}.txt', 'w') as f:
            f.write(','.join(feature_cols))
        joblib.dump(location_encoder, f'models/location_encoder_{target_short}.pkl')
        
        # Store in dictionaries
        models[target_short] = model
        scalers[target_short] = scaler
        features[target_short] = feature_cols
        location_encoders[target_short] = location_encoder
        
        # Plot training history
        plt.figure(figsize=(10, 6))
        plt.plot(history.history['loss'], label='Train Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title(f'Training History for {target_short.capitalize()}')
        plt.xlabel('Epoch')
        plt.ylabel('Loss (MSE)')
        plt.legend()
        plt.grid(True)
        plt.savefig(f'plots/{target_short}_training_history.png')
    
    return models, scalers, features, location_encoders

def predict_weather_by_location(location, recent_data, target, model, scaler, features, 
                             location_encoder, lookback=14, days_ahead=7):
    """
    Make weather predictions for a specific location
    """
    import pandas as pd
    import numpy as np
    from datetime import timedelta
    
    # Filter data for the specified location
    location_data = recent_data[recent_data['location'] == location].copy()
    
    if len(location_data) < lookback:
        raise ValueError(f"Not enough historical data for location {location}. Need at least {lookback} days.")
    
    # Get the most recent data
    recent_location_data = location_data.iloc[-lookback:].copy()
    
    # Prepare predictions list
    predictions = []
    current_data = recent_location_data.copy()
    
    # Split features into numerical and one-hot
    numerical_cols = [col for col in features if not col.startswith('loc_')]
    
    for day in range(days_ahead):
        # Scale the numerical features
        current_data[numerical_cols] = scaler.transform(current_data[numerical_cols])
        
        # Get the input sequence and ensure it's float32
        X_pred = current_data[features].values
        X_pred = np.asarray(X_pred, dtype=np.float32)  # Convert to float32
        X_pred = X_pred.reshape(1, lookback, len(features))
        
        # Make prediction
        next_day_pred = model.predict(X_pred, verbose=0)[0][0]
        predictions.append(next_day_pred)
        
        # Create next day's data for iterative prediction
        last_day = current_data.iloc[-1].copy()
        next_day = last_day.copy()
        
        # Increment date
        next_day['date'] = last_day['date'] + timedelta(days=1)
        
        # Update time-based features
        next_day['month'] = next_day['date'].month
        next_day['day'] = next_day['date'].day
        next_day['day_of_year'] = next_day['date'].timetuple().tm_yday
        next_day['year'] = next_day['date'].year
        
        # Update target with prediction
        next_day[target] = next_day_pred
        
        # Update lag features
        next_day['temp_avg_lag1'] = last_day['temp_avg_c']
        next_day['rainfall_lag1'] = last_day['rainfall_mm']
        next_day['humidity_lag1'] = last_day['humidity_pct']
        
        # Add the new row to current data and remove oldest
        current_data = pd.concat([current_data.iloc[1:], pd.DataFrame([next_day])])
    
    return predictions



def load_models_and_predict(location, recent_data_file, models_dir='models', days_to_predict=7):
    """
    Load saved models and make predictions for a specific location
    
    Args:
        location: Name of the location to predict for
        recent_data_file: CSV file with recent weather data
        models_dir: Directory containing saved models
        days_to_predict: Number of days to forecast
    
    Returns:
        DataFrame with predictions
    """
    # Read recent data
    recent_data = pd.read_csv(recent_data_file, parse_dates=['date'])
    
    predictions = {}
    
    for target_short, target_full in zip(['temp', 'rainfall', 'humidity'], 
                                        ['temp_avg_c', 'rainfall_mm', 'humidity_pct']):
        # Load model
        model = load_model(
            f'{models_dir}/location_lstm_{target_short}_model.h5',
            custom_objects={'mse': MeanSquaredError()}
        )
        
        # Load scaler
        scaler = joblib.load(f'{models_dir}/location_scaler_{target_short}.pkl')
        
        # Load features
        with open(f'{models_dir}/location_features_{target_short}.txt', 'r') as f:
            features = f.read().split(',')
        
        # Load location encoder
        location_encoder = joblib.load(f'{models_dir}/location_encoder_{target_short}.pkl')
        
        # Make predictions
        target_preds = predict_weather_by_location(
            location, recent_data, target_full,
            model, scaler, features, location_encoder,
            lookback=14, days_ahead=days_to_predict
        )
        
        predictions[f'{target_short}_pred'] = target_preds
    
    # Create prediction DataFrame
    pred_df = pd.DataFrame({
        'date': [recent_data['date'].max() + timedelta(days=i+1) for i in range(days_to_predict)],
        'location': location,
        'temp_avg_c_pred': predictions['temp_pred'],
        'rainfall_mm_pred': predictions['rainfall_pred'],
        'humidity_pct_pred': predictions['humidity_pred']
    })
    
    return pred_df

def get_forecast_summary(location):
    """
    Generate a forecast summary for a location (fix for the missing function)
    
    Args:
        location (str): Name of the district in Rwanda
        
    Returns:
        str: Forecast summary
    """
    try:
        # Generate yearly forecast for the location
        forecast_df = forecast_weather_yearly(location)
        
        # Use the existing seasonal summary function
        summary = get_seasonal_forecast_summary(forecast_df)
        
        return summary
    except Exception as e:
        return f"Error generating forecast summary: {str(e)}"

def forecast_weather_yearly(location, recent_data_file='data/rwanda_locations_weather_cleaned.csv', 
                           models_dir='models', days_to_predict=365):
    """
    Simulate forecast data for a specific location in Rwanda for testing
    This is a simplified version for demonstration since we don't have the actual models
    """
    # Create date range for the next year
    start_date = datetime.now()
    dates = [start_date + timedelta(days=i) for i in range(days_to_predict)]
    
    # Get district attributes if available, otherwise use defaults
    district_attrs = RWANDA_DISTRICTS.get(location, {
        'temp_offset': 0,
        'rainfall_factor': 1.0,
        'humidity_offset': 0,
        'elevation': 1500
    })
    
    # Base values adjusted for location
    temp_offset = district_attrs.get('temp_offset', 0)
    rainfall_factor = district_attrs.get('rainfall_factor', 1.0)
    humidity_offset = district_attrs.get('humidity_offset', 0)
    
    # Create simulated forecast data
    data = []
    for date in dates:
        month = date.month
        day_of_year = date.timetuple().tm_yday
        
        # Seasonal temperature variations
        seasonal_temp_effect = -3 * np.sin(2 * np.pi * (day_of_year - 15) / 365)
        
        # Calculate temperature
        base_temp = 22 + temp_offset
        day_temp = base_temp + seasonal_temp_effect + np.random.normal(0, 1)
        
        # Rainfall patterns - two rainy seasons in Rwanda
        # Major rainy season: March-May
        # Minor rainy season: September-December
        is_rainy_season = (month >= 3 and month <= 5) or (month >= 9 and month <= 12)
        
        if is_rainy_season:
            if month >= 3 and month <= 5:  # Major rainy season
                day_rainfall = max(0, np.random.gamma(5, 3) * rainfall_factor)
            else:  # Minor rainy season (Sep-Dec)
                day_rainfall = max(0, np.random.gamma(3, 2) * rainfall_factor)
        else:  # Dry season
            day_rainfall = max(0, np.random.gamma(1, 1) * rainfall_factor)
        
        # Calculate humidity
        base_humidity = 70 + humidity_offset
        humidity_seasonal = 5 if is_rainy_season else -5
        day_humidity = min(100, max(40, base_humidity + humidity_seasonal + np.random.normal(0, 3)))
        
        data.append({
            'date': date,
            'location': location,
            'temperature_c': round(day_temp, 1),
            'rainfall_mm': round(day_rainfall, 1),
            'humidity_pct': round(day_humidity, 1),
            'month': month,
            'month_name': date.strftime('%B'),
            'day': date.day,
            'year': date.year,
            'day_of_year': day_of_year,
            'season': get_season(month)
        })
    
    return pd.DataFrame(data)

def get_season(month):
    """Define Rwanda's seasons"""
    if month in [3, 4, 5]:
        return 'Major Rainy Season'
    elif month in [6, 7, 8]:
        return 'Major Dry Season'
    elif month in [9, 10, 11, 12]:
        return 'Minor Rainy Season'
    else:  # 1, 2
        return 'Minor Dry Season'

def get_seasonal_forecast_summary(forecast_df):
    """
    Generate a seasonal summary from forecast data
    
    Args:
        forecast_df: DataFrame with yearly forecast data
        
    Returns:
        str: Seasonal forecast summary
    """
    location = forecast_df['location'].iloc[0]
    
    # Group by season and calculate averages
    seasonal_summary = forecast_df.groupby('season').agg({
        'temperature_c': ['mean', 'min', 'max'],
        'rainfall_mm': ['mean', 'sum', 'max'],
        'humidity_pct': ['mean', 'min', 'max']
    }).round(1)
    
    # Group by month for monthly averages
    monthly_summary = forecast_df.groupby(['month', 'month_name']).agg({
        'temperature_c': 'mean',
        'rainfall_mm': 'sum',
        'humidity_pct': 'mean'
    }).round(1)
    
    # Create summary text
    summary = f"Annual Weather Forecast for {location}, Rwanda\n"
    summary += "=" * 50 + "\n\n"
    
    # Seasonal summary
    summary += "SEASONAL FORECAST SUMMARY\n"
    summary += "-" * 30 + "\n\n"
    
    for season in ['Minor Dry Season', 'Major Rainy Season', 'Major Dry Season', 'Minor Rainy Season']:
        if season in seasonal_summary.index:
            summary += f"{season}:\n"
            
            # Temperature
            temp_mean = seasonal_summary.loc[season, ('temperature_c', 'mean')]
            temp_min = seasonal_summary.loc[season, ('temperature_c', 'min')]
            temp_max = seasonal_summary.loc[season, ('temperature_c', 'max')]
            summary += f"  Temperature: {temp_mean}°C (Range: {temp_min}°C to {temp_max}°C)\n"
            
            # Rainfall
            rain_total = seasonal_summary.loc[season, ('rainfall_mm', 'sum')]
            rain_mean = seasonal_summary.loc[season, ('rainfall_mm', 'mean')]
            rain_max = seasonal_summary.loc[season, ('rainfall_mm', 'max')]
            
            # Characterize the rainfall
            if rain_total < 50:
                rain_desc = "Very dry"
            elif rain_total < 200:
                rain_desc = "Relatively dry"
            elif rain_total < 400:
                rain_desc = "Moderate rainfall"
            elif rain_total < 600:
                rain_desc = "Wet"
            else:
                rain_desc = "Very wet"
                
            summary += f"  Rainfall: {rain_desc} - Total: {rain_total}mm, Avg: {rain_mean}mm/day, Max: {rain_max}mm/day\n"
            
            # Humidity
            humidity_mean = seasonal_summary.loc[season, ('humidity_pct', 'mean')]
            summary += f"  Humidity: {humidity_mean}%\n\n"
    
    # Monthly breakdown
    summary += "MONTHLY FORECAST BREAKDOWN\n"
    summary += "-" * 30 + "\n\n"
    
    # Sort by month number for chronological display
    for month_num, month_group in sorted(monthly_summary.groupby(level=0)):
        month_name = month_group.index[0][1]
        temp = month_group['temperature_c'].values[0]
        rainfall = month_group['rainfall_mm'].values[0]
        humidity = month_group['humidity_pct'].values[0]
        
        summary += f"{month_name}:\n"
        summary += f"  Avg. Temperature: {temp}°C\n"
        summary += f"  Total Rainfall: {rainfall}mm\n"
        summary += f"  Avg. Humidity: {humidity}%\n\n"
    
    return summary

def generate_district_comparison_report():
    """
    Generate a comparison report of all districts across different time periods
    """
    # Dictionary to store forecasts for all districts
    all_districts_forecasts = {}
    
    # Generate forecasts for all districts
    for district in RWANDA_DISTRICTS.keys():
        print(f"Generating forecast for {district}...")
        all_districts_forecasts[district] = forecast_weather_yearly(district)
    
    # Combine all forecasts into a single DataFrame
    combined_forecast = pd.concat(all_districts_forecasts.values())
    
    # Monthly averages across all districts
    monthly_district_avg = combined_forecast.groupby(['location', 'month', 'month_name']).agg({
        'temperature_c': 'mean',
        'rainfall_mm': 'sum',
        'humidity_pct': 'mean'
    }).round(1).reset_index()
    
    # Seasonal averages across all districts
    seasonal_district_avg = combined_forecast.groupby(['location', 'season']).agg({
        'temperature_c': 'mean',
        'rainfall_mm': 'sum',
        'humidity_pct': 'mean'
    }).round(1).reset_index()
    
    # Yearly averages across all districts
    yearly_district_avg = combined_forecast.groupby(['location']).agg({
        'temperature_c': 'mean',
        'rainfall_mm': 'sum',
        'humidity_pct': 'mean'
    }).round(1).reset_index()
    
    # Generate CSV files
    monthly_district_avg.to_csv('reports/monthly_district_weather_avg.csv', index=False)
    seasonal_district_avg.to_csv('reports/seasonal_district_weather_avg.csv', index=False)
    yearly_district_avg.to_csv('reports/yearly_district_weather_avg.csv', index=False)
    
    return {
        'monthly': monthly_district_avg,
        'seasonal': seasonal_district_avg,
        'yearly': yearly_district_avg
    }

def create_comparison_visualizations(district_data):
    """
    Create visualizations comparing weather patterns across districts
    """
    yearly_data = district_data['yearly']
    seasonal_data = district_data['seasonal']
    monthly_data = district_data['monthly']
    
    # 1. Temperature comparison across districts (yearly average)
    plt.figure(figsize=(14, 10))
    yearly_sorted = yearly_data.sort_values(by='temperature_c', ascending=False)
    sns.barplot(x='location', y='temperature_c', data=yearly_sorted)
    plt.title('Average Annual Temperature by District')
    plt.xlabel('District')
    plt.ylabel('Temperature (°C)')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig('plots/district_temperature_comparison.png')
    
    # 2. Total annual rainfall comparison
    plt.figure(figsize=(14, 10))
    yearly_sorted = yearly_data.sort_values(by='rainfall_mm', ascending=False)
    sns.barplot(x='location', y='rainfall_mm', data=yearly_sorted)
    plt.title('Total Annual Rainfall by District')
    plt.xlabel('District')
    plt.ylabel('Rainfall (mm)')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig('plots/district_rainfall_comparison.png')
    
    # 3. Seasonal temperature patterns across provinces
    # First, add province information
    province_map = {district: data['province'] for district, data in RWANDA_DISTRICTS.items()}
    seasonal_data['province'] = seasonal_data['location'].map(province_map)
    
    plt.figure(figsize=(14, 10))
    season_order = ['Minor Dry Season', 'Major Rainy Season', 'Major Dry Season', 'Minor Rainy Season']
    sns.boxplot(x='season', y='temperature_c', hue='province', data=seasonal_data, order=season_order)
    plt.title('Seasonal Temperature Patterns by Province')
    plt.xlabel('Season')
    plt.ylabel('Average Temperature (°C)')
    plt.legend(title='Province')
    plt.tight_layout()
    plt.savefig('plots/seasonal_temperature_by_province.png')
    
    # 4. Monthly rainfall patterns across provinces
    monthly_data['province'] = monthly_data['location'].map(province_map)
    
    plt.figure(figsize=(16, 10))
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
    sns.lineplot(x='month_name', y='rainfall_mm', hue='province', data=monthly_data, 
           style='province', markers=True, errorbar=None)
    plt.title('Monthly Rainfall Patterns by Province')
    plt.xlabel('Month')
    plt.ylabel('Total Rainfall (mm)')
    plt.xticks(rotation=45)
    plt.legend(title='Province')
    plt.tight_layout()
    plt.savefig('plots/monthly_rainfall_by_province.png')
    
    return {
        'temperature': 'plots/district_temperature_comparison.png',
        'rainfall': 'plots/district_rainfall_comparison.png',
        'seasonal': 'plots/seasonal_temperature_by_province.png',
        'monthly': 'plots/monthly_rainfall_by_province.png'
    }


def print_comparative_report(district_data):
    """
    Print a comprehensive comparative report of all districts
    """
    yearly_data = district_data['yearly']
    
    # Header
    print("\n" + "="*80)
    print("RWANDA DISTRICTS WEATHER COMPARISON")
    print("="*80 + "\n")
    
    # 1. Top 5 warmest districts
    print("TOP 5 WARMEST DISTRICTS (Annual Average)")
    print("-"*50)
    warmest = yearly_data.sort_values(by='temperature_c', ascending=False).head(5)
    for i, (_, row) in enumerate(warmest.iterrows()):
        print(f"{i+1}. {row['location']}: {row['temperature_c']}°C")
    
    # 2. Top 5 coolest districts
    print("\nTOP 5 COOLEST DISTRICTS (Annual Average)")
    print("-"*50)
    coolest = yearly_data.sort_values(by='temperature_c').head(5)
    for i, (_, row) in enumerate(coolest.iterrows()):
        print(f"{i+1}. {row['location']}: {row['temperature_c']}°C")
    
    # 3. Top 5 wettest districts (highest rainfall)
    print("\nTOP 5 WETTEST DISTRICTS (Annual Rainfall)")
    print("-"*50)
    wettest = yearly_data.sort_values(by='rainfall_mm', ascending=False).head(5)
    for i, (_, row) in enumerate(wettest.iterrows()):
        print(f"{i+1}. {row['location']}: {row['rainfall_mm']}mm")
    
    # 4. Top 5 driest districts (lowest rainfall)
    print("\nTOP 5 DRIEST DISTRICTS (Annual Rainfall)")
    print("-"*50)
    driest = yearly_data.sort_values(by='rainfall_mm').head(5)
    for i, (_, row) in enumerate(driest.iterrows()):
        print(f"{i+1}. {row['location']}: {row['rainfall_mm']}mm")
    
    # 5. Average by province
    print("\nPROVINCE WEATHER AVERAGES")
    print("-"*50)
    
    # Add province to yearly data
    province_map = {district: data['province'] for district, data in RWANDA_DISTRICTS.items()}
    yearly_data['province'] = yearly_data['location'].map(province_map)
    
    province_avg = yearly_data.groupby('province').agg({
        'temperature_c': 'mean',
        'rainfall_mm': 'mean',
        'humidity_pct': 'mean'
    }).round(1)
    
    for province, row in province_avg.iterrows():
        print(f"\n{province} Province:")
        print(f"  Average Temperature: {row['temperature_c']}°C")
        print(f"  Average Annual Rainfall: {row['rainfall_mm']}mm")
        print(f"  Average Humidity: {row['humidity_pct']}%")
    
    print("\n" + "="*80)
    print("Generated report files:")
    # print("  - reports/monthly_district_weather_avg.csv")
    # print("  - reports/seasonal_district_weather_avg.csv") 
    # print("  - reports/yearly_district_weather_avg.csv")
    print("="*80 + "\n")
    
    
def visualize_yearly_forecast(forecast_df, output_dir='plots'):
    """
    Create visualizations for yearly weather forecast
    
    Args:
        forecast_df: DataFrame with yearly forecast
        output_dir: Directory to save plots
    """
    location = forecast_df['location'].iloc[0]
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 1. Temperature throughout the year
    plt.figure(figsize=(15, 6))
    plt.plot(forecast_df['date'], forecast_df['temperature_c'], 'r-')
    plt.title(f'Annual Temperature Forecast for {location}')
    plt.xlabel('Date')
    plt.ylabel('Temperature (°C)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Add season background colors
    seasons = forecast_df['season'].unique()
    season_colors = {
        'Major Rainy Season': 'lightblue',
        'Major Dry Season': 'bisque',
        'Minor Rainy Season': 'lightcyan',
        'Minor Dry Season': 'wheat'
    }
    
    for season in seasons:
        season_data = forecast_df[forecast_df['season'] == season]
        if not season_data.empty:
            plt.axvspan(season_data['date'].min(), season_data['date'].max(), 
                      alpha=0.2, color=season_colors.get(season, 'lightgray'))
    
    # Add legend for seasons
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color, alpha=0.2, label=season)
                      for season, color in season_colors.items()]
    plt.legend(handles=legend_elements, loc='upper right')
        
    plt.savefig(f'{output_dir}/{location}_annual_temperature.png')
    
    # 2. Monthly rainfall
    monthly_rain = forecast_df.groupby(['month_name', 'month'])['rainfall_mm'].sum().reset_index()
    monthly_rain = monthly_rain.sort_values('month')  # Sort by month number for chronological order
    
    plt.figure(figsize=(12, 6))
    rainfall_bars = plt.bar(monthly_rain['month_name'], monthly_rain['rainfall_mm'], color='skyblue')
    
    # Add season coloring to the bars
    for i, month_num in enumerate(monthly_rain['month']):
        if month_num in [3, 4, 5]:  # Major Rainy Season
            rainfall_bars[i].set_color('royalblue')
        elif month_num in [6, 7, 8]:  # Major Dry Season
            rainfall_bars[i].set_color('orange')
        elif month_num in [9, 10, 11, 12]:  # Minor Rainy Season
            rainfall_bars[i].set_color('deepskyblue')
        else:  # Minor Dry Season
            rainfall_bars[i].set_color('wheat')
    
    plt.title(f'Monthly Rainfall Forecast for {location}')
    plt.xlabel('Month')
    plt.ylabel('Total Rainfall (mm)')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add legend for rainfall by season
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='wheat', label='Minor Dry Season'),
        Patch(facecolor='royalblue', label='Major Rainy Season'),
        Patch(facecolor='orange', label='Major Dry Season'),
        Patch(facecolor='deepskyblue', label='Minor Rainy Season')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{location}_monthly_rainfall.png')
    
    # 3. Seasonal comparison - multiple metrics
    seasonal_data = forecast_df.groupby('season').agg({
        'temperature_c': 'mean',
        'rainfall_mm': 'sum',
        'humidity_pct': 'mean'
    }).reset_index()
    
    # Order seasons chronologically
    season_order = ['Minor Dry Season', 'Major Rainy Season', 'Major Dry Season', 'Minor Rainy Season']
    seasonal_data['season_order'] = seasonal_data['season'].map({s: i for i, s in enumerate(season_order)})
    seasonal_data = seasonal_data.sort_values('season_order').drop('season_order', axis=1)
    
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    # Temperature line
    ax1.set_xlabel('Season')
    ax1.set_ylabel('Average Temperature (°C)', color='tab:red')
    ax1.plot(seasonal_data['season'], seasonal_data['temperature_c'], color='tab:red', marker='o', linewidth=2)
    ax1.tick_params(axis='y', labelcolor='tab:red')
    
    # Rainfall bars on secondary y-axis
    ax2 = ax1.twinx()
    ax2.set_ylabel('Total Rainfall (mm)', color='tab:blue')
    ax2.bar(seasonal_data['season'], seasonal_data['rainfall_mm'], color='tab:blue', alpha=0.6)
    ax2.tick_params(axis='y', labelcolor='tab:blue')
    
    plt.title(f'Seasonal Weather Comparison for {location}')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{location}_seasonal_comparison.png')
    
    # 4. Daily rainfall heatmap by month
    # Create a pivot with day of month vs month
    forecast_df['day_of_month'] = forecast_df['date'].dt.day
    rainfall_pivot = forecast_df.pivot_table(
        values='rainfall_mm', 
        index='day_of_month',
        columns='month_name', 
        aggfunc='mean'
    )
    
    # Sort columns by month number
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
    rainfall_pivot = rainfall_pivot[
        [m for m in month_order if m in rainfall_pivot.columns]
    ]
    
    plt.figure(figsize=(14, 10))
    sns.heatmap(rainfall_pivot, cmap='Blues', vmin=0, vmax=max(20, rainfall_pivot.max().max()))
    plt.title(f'Daily Rainfall Pattern Forecast for {location}')
    plt.ylabel('Day of Month')
    plt.savefig(f'{output_dir}/{location}_rainfall_heatmap.png')
    
    # Return file paths for all generated images
    return {
        'temperature': f'{output_dir}/{location}_annual_temperature.png',
        'rainfall': f'{output_dir}/{location}_monthly_rainfall.png',
        'seasonal': f'{output_dir}/{location}_seasonal_comparison.png',
        'heatmap': f'{output_dir}/{location}_rainfall_heatmap.png'
    }

def get_district_climate_insights(location):
    """
    Get specific climate insights for a district based on known characteristics
    
    Args:
        location: Name of the district
    
    Returns:
        dict: Climate insights
    """
    # Basic district climate characteristics from the original code
  
    if location not in RWANDA_DISTRICTS:
        return {
            "error": f"Climate data for {location} not found"
        }
    
    data = RWANDA_DISTRICTS[location]
    
    # Generate climate insights
    climate_type = "unknown"
    features = []
    agricultural_notes = []
    
    # Determine climate type and special features
    if data['temp_offset'] < -2.0:
        climate_type = "Cool Highland"
        features.append("Cool temperatures year-round")
        agricultural_notes.append("Suitable for tea cultivation and temperate crops")
    elif data['temp_offset'] > 1.5:
        climate_type = "Warm Lowland"
        features.append("Higher temperatures throughout the year")
        agricultural_notes.append("Suitable for drought-resistant crops and livestock")
    else:
        climate_type = "Moderate Mid-altitude"
        features.append("Moderate temperatures")
        agricultural_notes.append("Versatile agricultural potential")
    
    # Rainfall patterns
    if data['rainfall_factor'] > 1.2:
        features.append("High rainfall throughout rainy seasons")
        agricultural_notes.append("Good for water-intensive crops like rice")
    elif data['rainfall_factor'] < 0.8:
        features.append("Lower rainfall, more drought-prone")
        agricultural_notes.append("Requires drought-resistant crops and water management")
    
    # Humidity insights
    if data['humidity_offset'] > 4:
        features.append("Higher humidity levels")
        if "lake" in location.lower() or any(l in location for l in ["Rubavu", "Karongi", "Rusizi", "Nyamasheke"]):
            features.append("Lake effect increases humidity and moderates temperatures")
    elif data['humidity_offset'] < -3:
        features.append("Lower humidity, more arid conditions")
    
    # Elevation effects
    if data['elevation'] > 1800:
        features.append(f"High elevation ({data['elevation']}m) creates cooler microclimate")
    
    return {
        "location": location,
        "province": data['province'],
        "elevation": data['elevation'],
        "coordinates": data['coordinates'],
        "climate_type": climate_type,
        "features": features,
        "agricultural_potential": agricultural_notes
    }

def generate_annual_forecast_report(location, include_plots=True):
    """
    Generate a comprehensive annual forecast report for a district
    
    Args:
        location: Name of the district
        include_plots: Whether to include plot generation
        
    Returns:
        dict: Comprehensive forecast report
    """
    try:
        # Get climate insights for the district
        climate_insights = get_district_climate_insights(location)
        
        # Generate annual forecast
        annual_forecast = forecast_weather_yearly(location)
        
        # Generate seasonal summary
        seasonal_summary = get_seasonal_forecast_summary(annual_forecast)
        
        # Generate plots if requested
        plot_paths = {}
        if include_plots:
            plot_paths = visualize_yearly_forecast(annual_forecast)
        
        # Compile everything into a comprehensive report
        report = {
            "location": location,
            "climate_profile": climate_insights,
            "annual_forecast_data": annual_forecast,
            "seasonal_summary": seasonal_summary,
            "plot_paths": plot_paths
        }
        
        return report
        
    except Exception as e:
        return {
            "error": f"Error generating annual forecast: {str(e)}"
        }


def inspect_data_types(data):
    """Inspect data types and check for potential issues"""
    print("Data types in DataFrame:")
    print(data.dtypes)
    
    # Check for object/string columns in features
    for col in data.columns:
        if data[col].dtype == 'object':
            print(f"Column {col} has object dtype, values: {data[col].unique()[:5]}")
    
    # Check for non-numeric values
    for col in data.select_dtypes(include=['float64', 'int64']).columns:
        non_numeric = pd.to_numeric(data[col], errors='coerce').isna().sum()
        if non_numeric > 0:
            print(f"Column {col} has {non_numeric} non-numeric values")
   
   

def print_forecast_report(report):
    """
    Print a nicely formatted version of the forecast report
    
    Args:
        report: Dictionary containing the forecast report data
    """
    if "error" in report:
        print(f"ERROR: {report['error']}")
        return
    
    location = report["location"]
    climate_profile = report["climate_profile"]
    seasonal_summary = report["seasonal_summary"]
    
    # Print header
    print("\n" + "="*80)
    print(f"RWANDA WEATHER FORECAST REPORT: {location.upper()}")
    print("="*80 + "\n")
    
    # Print climate profile
    print("CLIMATE PROFILE")
    print("-"*50)
    print(f"Location: {location}")
    print(f"Province: {climate_profile['province']}")
    print(f"Elevation: {climate_profile['elevation']} meters")
    print(f"Coordinates: {climate_profile['coordinates'][0]:.2f}°, {climate_profile['coordinates'][1]:.2f}°")
    print(f"Climate Type: {climate_profile['climate_type']}")
    
    print("\nKey Climate Features:")
    for feature in climate_profile['features']:
        print(f"- {feature}")
    
    print("\nAgricultural Potential:")
    for note in climate_profile['agricultural_potential']:
        print(f"- {note}")
    
    # Print seasonal summary
    print("\n" + seasonal_summary)
    
    # Print plot file paths if available
    if report["plot_paths"] and len(report["plot_paths"]) > 0:
        print("\nFORECAST VISUALIZATIONS")
        print("-"*50)
        for plot_type, path in report["plot_paths"].items():
            print(f"{plot_type.capitalize()} Plot: {path}")
    
    # Print forecast data sample
    print("\nFORECAST DATA SAMPLE (First 7 days)")
    print("-"*80)
    forecast_sample = report["annual_forecast_data"].head(7)
    print(forecast_sample[['date', 'temperature_c', 'rainfall_mm', 'humidity_pct']].to_string(index=False))
    print(f"\n... plus {len(report['annual_forecast_data']) - 7} more days")
    
    print("\n" + "="*80)
    print(f"End of forecast report for {location}")
    print("="*80 + "\n")         
            

# Main execution of model to predict weather for a specific district
# and generate reports
# This is a placeholder for the main execution block

if __name__ == "__main__":
    # Fix the error by running the corrected get_forecast_summary function
    location = input("Enter the district name (e.g., Kirehe): ").strip()
    print(f"\nForecast summary for {location}:")
    print(get_forecast_summary(location))
    
    # Generate comparison data for all districts
    print("\nGenerating weather comparison data for all districts...")
    district_comparison = generate_district_comparison_report()
    
    # Create visualizations
    # print("\nCreating comparison visualizations...")
    # plot_paths = create_comparison_visualizations(district_comparison)
    
    # Print comparative report
    print_comparative_report(district_comparison)
    
    # print("\nVisualization files:")
    # for chart_type, path in plot_paths.items():
    #     print(f"  - {chart_type}: {path}")