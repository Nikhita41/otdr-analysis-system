import pandas as pd
import numpy as np

def process_otdr_data(df):

    # -------- DISTANCE UNIT FIX --------
    # If distance is in meters convert to km
    if df["Distance"].max() > 100:
        df["Distance"] = df["Distance"] / 1000

    # -------- POWER DROP --------
    # Negative = loss, Positive = reflection spike
    df["Power_Drop"] = df["Power"].diff()

    # -------- SLOPE --------
    # Rate of power change per km
    df["Slope"] = df["Power"].diff() / df["Distance"].diff()

    # -------- ATTENUATION --------
    # Loss column is round-trip → divide by 2
    # Also avoid division by zero
    df["Attenuation"] = (df["Loss"] / df["Distance"].replace(0, np.nan)) / 2

    # -------- REFLECTANCE --------
    # Fresnel reflection spike detection
    df["Reflectance"] = df["Power"] - df["Power"].rolling(5).mean()

    # -------- EVENT FLAG --------
    df["Event_Flag"] = np.where(abs(df["Power_Drop"]) > 0.5, 1, 0)

    # Replace NaN
    df = df.fillna(0)

    print("\nProcessed OTDR Data:")
    print(df.head())

    return df