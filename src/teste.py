import altair as alt
import datetime
import dateutil
import json
import pandas as pd
import os
import streamlit as st
import local_lib as lib
import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

#df_tesouro = st.session_state['tesouro']
df_tesouro = pd.read_csv('../tesouro_pos_importacao.csv')
df_tesouro['data'] = pd.to_datetime(df_tesouro['data'], format='%Y-%m-%d')


# Tab1 - Tabela dinâmica.
df_hist_tesouro = lib.etl_tesouro_historic_price()
df_tesouro_historico = lib.merge_historic_tesouro(df_hist_tesouro, df_tesouro)
df_tesouro_historico = lib.create_column_last_day(df_tesouro_historico)

tab1 = lib.custom_pivot_table(df_tesouro_historico, col_value='vl_atualizado')


# Tab2 - Tabela para o gráfico de linha.
df_hist_bench = lib.etl_benchmark_historic_price()
df_tesouro_historico_agg = lib.merge_historic_benchmark(df_tesouro_historico, df_hist_bench)
df_tesouro_historico_agg.to_csv('teste.csv', index=False)
#tab2 = lib.custom_data_lineplot(df_tesouro_historico_agg, ['ibov', 'sp500', 'cdi', 'ipca'])
#tab2.to_csv('teste.csv', index=False)
print(tab2)
