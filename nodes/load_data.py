import pandas as pd


def load_data(state: dict) -> dict:
    df = pd.read_excel("data/pet_food_rgm_data_v2.xlsx", sheet_name="Weekly Raw Data")
    print("\n=== Column Names ===")
    for col in df.columns:
        print(f"  {repr(col)}")
    print(f"=== Total columns: {len(df.columns)}, Rows: {len(df)} ===\n")
    return {"raw_df": df}
