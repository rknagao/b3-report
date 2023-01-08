import numpy as np
import pandas as pd

def dummy_last_day_of_month_in_sample(date_array: np.array) -> np.array:
    df = pd.DataFrame()
    df['year'] = pd.to_datetime(date_array).dt.year
    df['month'] = pd.to_datetime(date_array).dt.month
    df['day'] = pd.to_datetime(date_array).dt.day
    
    df_g = df.groupby(['year','month']).agg({'day':'max'}).reset_index(drop=False)
    df_g['ultimo_dia_mes'] = pd.to_datetime(df_g[['year', 'month', 'day']])

    output = [1 if (i in list(df_g['ultimo_dia_mes'])) else 0 for i in date_array]

    return output