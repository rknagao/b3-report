import altair as alt
import datetime
import dateutil
import json
import pandas as pd
import os
import streamlit as st
import local_lib as lib
import yfinance as yf

##########################
## CONFIGURAÇÕES GERAIS ##
##########################

st.header('🐢 Tesouro Direto')

if ('import_state' not in st.session_state) or (st.session_state['import_state'] != 'ready'):
    st.warning('Insira dados na aba de importação.')

else:    
    df_tesouro = st.session_state['tesouro']
    df_tesouro['data'] = pd.to_datetime(df_tesouro['data'], format='%Y-%m-%d')
    

    ##########################
    # TAB1 - TABELA DINAMICA #
    ##########################

    st.markdown('''
    #### Parte 1: Evolução mensal
    A tabela dinâmica abaixo apresenta o valor acumulado e atualizado até o último dia de cotação do Tesouro Direto.
    ''')

    df_hist_tesouro = lib.etl_tesouro_historic_price()
    df_tesouro_historico = lib.merge_historic_tesouro(df_hist_tesouro, df_tesouro)
    df_tesouro_historico = lib.create_column_last_day(df_tesouro_historico)
    
    # Filtro de tickers.
    list_ticker = st.multiselect('Escolha o(s) investimento(s):',
                                 df_tesouro_historico['ticker'].unique().tolist(),
                                 df_tesouro_historico['ticker'].unique().tolist())
    df_tesouro_historico = df_tesouro_historico.loc[df_tesouro_historico['ticker'].isin(list_ticker)]
    
    df_plot = df_tesouro_historico.loc[df_tesouro_historico['dummy_ultimo_dia'] == 1]
    tab1, data_col = lib.custom_pivot_table(df_plot, col_value='vl_atualizado')
    st.dataframe(tab1.style.format(subset=data_col, formatter="{:.2f}"))


    ##########################################
    # TAB2 - GRÁFICO DE LINHA COM BENCHMARKS #
    ##########################################

    st.markdown('''
    #### Parte 2: Evolução mensal
    Evolução da carteira e os valores simulados de benchmarks.
    ''')

    df_hist_bench = lib.etl_benchmark_historic_price()
    df_tesouro_historico_agg = lib.merge_historic_benchmark(df_tesouro_historico, df_hist_bench)
    tab2 = lib.custom_data_lineplot(df_tesouro_historico_agg, ['ibov', 'sp500', 'cdi', 'ipca'])
    lib.lineplot_altair(data=tab2, title='Simulação de carteira vs benchmarks', col_date='data', col_value='value', col_label='variable')
