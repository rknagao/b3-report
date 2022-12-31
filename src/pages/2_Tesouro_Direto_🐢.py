import altair as alt
import datetime
import dateutil
import json
#import local_lib as lib
from lib.data import tesouro
from millify import millify
import numpy as np
import os
import pandas as pd
import streamlit as st
import yfinance as yf

##########################
## CONFIGURAÇÕES GERAIS ##
##########################

st.header('Tesouro Direto 🐢')

if ('import_state' not in st.session_state) or (st.session_state['import_state'] != 'ready'):
    st.warning('Volte ao menu Home à esquerda para carregar os dados.')

else:    
    if st.session_state['tesouro'].shape[0] == 0:
        st.warning('Os relatórios inseridos estão vazios.')
    
    else:
        df = st.session_state['tesouro']
        df['data'] = pd.to_datetime(df['data'], format='%Y-%m-%d')
        

        ##########################
        # TAB1 - TABELA DINAMICA #
        ##########################

        st.markdown('''
        #### Parte 1: Evolução mensal
        A tabela dinâmica abaixo apresenta o valor acumulado e atualizado até o último dia de cotação do Tesouro Direto.
        ''')

        st.dataframe(df)

        """
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


        ##############
        # TAB3 - KPI #
        ##############

        st.markdown('''
        #### Parte 3: KPI
        Principais números da carteira.
        ''')

        date_interval = st.slider('Selecione o intervalo',
                                  value=(df_tesouro_historico['data'].min().to_pydatetime()  - datetime.timedelta(days=1),
                                         df_tesouro_historico['data'].max().to_pydatetime()),
                                  min_value=df_tesouro_historico['data'].min().to_pydatetime() - datetime.timedelta(days=1),
                                  max_value=df_tesouro_historico['data'].max().to_pydatetime(),
                                  step=datetime.timedelta(days=90),
                                  format='YYYY-MM-DD')
        
        # Criar o dataframe df_kpi co
        df_date = pd.DataFrame({'data': pd.date_range(df_tesouro_historico['data'].min().to_pydatetime() - datetime.timedelta(days=1),
                                                      df_tesouro_historico['data'].max().to_pydatetime())})
        df_kpi = pd.merge(df_date, df_tesouro_historico, on='data', how='left')
        df_kpi = df_kpi.groupby('data').agg({'qt':'sum', 'qt_acum':'sum',  'vl_atualizado':'sum'}).reset_index()
        df_kpi['vl_atualizado'] = np.where(df_kpi['qt_acum'] != 0, df_kpi['vl_atualizado'], np.nan)
        df_kpi['vl_atualizado'] = df_kpi['vl_atualizado'].fillna(method='ffill').fillna(0)

        # Cálculo dos aportes históricos.
        vl_aporte = df_tesouro_historico.loc[(df_tesouro_historico['qt'] != 0) &
                                             (df_tesouro_historico['vl_total'] > 0) &
                                             (df_tesouro_historico['data'] <= date_interval[1]), 'vl_total'].sum()

        vl_aporte_delta = df_tesouro_historico.loc[(df_tesouro_historico['qt'] != 0) &
                                                   (df_tesouro_historico['vl_total'] > 0) &
                                                   (df_tesouro_historico['data'].between(date_interval[0], date_interval[1])), 'vl_total'].sum()

        # Cálculo dos valores resgatados.
        vl_resgate = df_tesouro_historico.loc[(df_tesouro_historico['qt'] != 0) &
                                              (df_tesouro_historico['vl_total'] < 0) &
                                              (df_tesouro_historico['data'] <= date_interval[1]), 'vl_total'].sum()

        vl_resgate_delta = df_tesouro_historico.loc[(df_tesouro_historico['qt'] != 0) &
                                                    (df_tesouro_historico['vl_total'] < 0) &
                                                    (df_tesouro_historico['data'].between(date_interval[0], date_interval[1])), 'vl_total'].sum()

        # Cálculo do valor patrimonial.
        vl_patrimonio = df_kpi.loc[df_kpi['data'] == date_interval[1], 'vl_atualizado'].sum()
        vl_patrimonio_delta = vl_patrimonio - df_kpi.loc[df_kpi['data'] == date_interval[0], 'vl_atualizado'].sum()

        # Cálculo do rendimento.
        rendimento_nominal = round((vl_patrimonio - vl_resgate - vl_aporte) / vl_aporte * 100 , 1)
        if  vl_aporte_delta != 0:
            rendimento_nominal_delta = round((vl_patrimonio_delta - vl_resgate_delta - vl_aporte_delta) / vl_aporte_delta * 100 , 1)
        else:
            rendimento_nominal_delta = 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Aporte", value=f"R$ {millify(vl_aporte)}", delta=f"R$ {millify(vl_aporte_delta)}")

        with col2:
            st.metric(label="Resgate", value=f"R$ {millify(vl_resgate)}", delta=f"R$ {millify(vl_resgate_delta)}", delta_color='inverse')

        with col3:
            st.metric(label="Patrimônio", value=f"R$ {millify(vl_patrimonio)}", delta=f"R$ {millify(vl_patrimonio_delta)}")

        with col4:
            st.metric(label="Rendimento", value=f"{rendimento_nominal} %", delta=f"{rendimento_nominal_delta} %")
        """