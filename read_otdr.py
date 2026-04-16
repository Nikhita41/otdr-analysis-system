import pandas as pd

def read_otdr_file(file_path):
    df = pd.read_excel(
        file_path,
        sheet_name="Raw_Trace_Data",
        skiprows=30,
        engine="openpyxl"
    )

    df.columns = df.columns.str.strip()

    df = df.iloc[:, [1, 2, 3]]
    df.columns = ["Distance", "Power", "Loss"]

    df = df[pd.to_numeric(df["Distance"], errors='coerce').notnull()]

    df["Distance"] = pd.to_numeric(df["Distance"])
    df["Power"] = pd.to_numeric(df["Power"])
    df["Loss"] = pd.to_numeric(df["Loss"])

    df = df.reset_index(drop=True)

    return df