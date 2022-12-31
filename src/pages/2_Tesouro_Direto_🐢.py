import altair as alt
import datetime
import dateutil
import json
from lib.history import tesouro, cdi, ipca, ibovespa, sp500, all_benchmarks
from lib.date import dummy_last_day_of_month_in_sample
from lib.data_manipulation import calculate_accrued_yield
from lib.streamlit import pivot_table, lineplot
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
        df_tesouro = st.session_state['tesouro']
        df_tesouro['data'] = pd.to_datetime(df_tesouro['data'], format='%Y-%m-%d')
        

        ##########################
        # TAB1 - TABELA DINAMICA #
        ##########################

        st.markdown('''
        #### Parte 1: Evolução dos títulos
        A tabela dinâmica abaixo apresenta a evolução de cada título ao longo do tempo.
        ''')

        #st.dataframe(df_tesouro)
        df_history_tesouro = tesouro()

        # -----------------------------------------------------------------------
        def tesouro_treatment(df_history_tesouro, df_tesouro):
            df = pd.merge(df_history_tesouro, df_tesouro, on=['data','ticker'], how='left').fillna(0).sort_values(['ticker','data']).reset_index(drop=True)

            for i in df.loc[df['qt'] > 0, 'ticker'].unique():
                df.loc[df['ticker'] == i, 'qt_acum'] = df.loc[df['ticker'] == i, 'qt'].cumsum()
                
            df = df.loc[(df['qt_acum'] > 0) | (df['qt'] != 0)].reset_index(drop=True)
            df['vl_atualizado'] = (df['qt_acum'] * df['preco_hist']).round(2)
            df['ultimo_dia_mes'] = dummy_last_day_of_month_in_sample(date_array=df['data'])

            return df
        # -----------------------------------------------------------------------


        df_tesouro_treatment = tesouro_treatment(df_history_tesouro, df_tesouro)

        # Filtro de tickers.
        list_ticker = st.multiselect('Escolha o(s) investimento(s):',
                                     df_tesouro_treatment['ticker'].unique().tolist(),
                                     df_tesouro_treatment['ticker'].unique().tolist())

        df_tesouro_treatment = df_tesouro_treatment.loc[df_tesouro_treatment['ticker'].isin(list_ticker)]

        pivot_table(df=df_tesouro_treatment.loc[df_tesouro_treatment['ultimo_dia_mes'] == 1],
                    x='data', y='ticker', value='vl_atualizado')
        
        st.markdown('-----')



        ##########################################
        # TAB2 - GRÁFICO DE LINHA COM BENCHMARKS #
        ##########################################

        st.markdown('''
        #### Parte 2: Evolução da carteira
        O gráfico abaixo apresenta a evolução da carteira como um todo, em referência aos benchmarks mais comuns do mercado.
        ''')

        df_benchmarks = all_benchmarks(start_date=df_tesouro_treatment['data'].min(),
                                       end_date=df_tesouro_treatment['data'].max())

        
         # -----------------------------------------------------------------------
        def benchmark_treatment(df_tesouro_treatment, df_benchmarks):

            list_bench = df_benchmarks.columns[1:].tolist()
            df_agg = df_tesouro_treatment.groupby(['data']).agg({'vl_total':'sum', 'vl_atualizado':'sum'}).reset_index(drop=False)
            df_agg.rename(columns={'vl_atualizado':'carteira'}, inplace=True)
            df_agg['data'] = pd.to_datetime(df_agg['data'])
            df = pd.merge(df_agg, df_benchmarks, on='data', how='left')

            for i in list_bench:
                df[i] = calculate_accrued_yield(array_value=df['vl_total'], array_yield=df[i])
                
            df = pd.melt(df, id_vars='data', value_vars=['carteira'] + list_bench[1:])
            df['data_lag'] = df['data'].shift(-1)

            return df
         # -----------------------------------------------------------------------

        df_benchmark_treatment = benchmark_treatment(df_tesouro_treatment, df_benchmarks)
        df_benchmark_treatment.to_csv('aa.csv', index=False)
        lineplot(df=df_benchmark_treatment, x='data', y='value', label='variable', title='Simulação de carteira vs benchmarks')

        
        ##############
        # TAB3 - KPI #
        ##############

        st.markdown('''
        #### Parte 3: KPI
        Principais números da carteira.
        ''')

        date_interval = st.slider('Selecione o intervalo',
                                  value=(df_tesouro_treatment['data'].min().to_pydatetime()  - datetime.timedelta(days=1),
                                         df_tesouro_treatment['data'].max().to_pydatetime()),
                                  min_value=df_tesouro_treatment['data'].min().to_pydatetime() - datetime.timedelta(days=1),
                                  max_value=df_tesouro_treatment['data'].max().to_pydatetime(),
                                  step=datetime.timedelta(days=90),
                                  format='YYYY-MM-DD')
        
        # Criar o dataframe df_kpi co
        df_date = pd.DataFrame({'data': pd.date_range(df_tesouro_treatment['data'].min().to_pydatetime() - datetime.timedelta(days=1),
                                                      df_tesouro_treatment['data'].max().to_pydatetime())})
        df_kpi = pd.merge(df_date, df_tesouro_treatment, on='data', how='left')
        df_kpi = df_kpi.groupby('data').agg({'qt':'sum', 'qt_acum':'sum',  'vl_atualizado':'sum'}).reset_index()
        df_kpi['vl_atualizado'] = np.where(df_kpi['qt_acum'] != 0, df_kpi['vl_atualizado'], np.nan)
        df_kpi['vl_atualizado'] = df_kpi['vl_atualizado'].fillna(method='ffill').fillna(0)

        # Cálculo dos aportes históricos.
        vl_aporte = df_tesouro_treatment.loc[(df_tesouro_treatment['qt'] != 0) &
                                             (df_tesouro_treatment['vl_total'] > 0) &
                                             (df_tesouro_treatment['data'] <= date_interval[1]), 'vl_total'].sum()

        vl_aporte_delta = df_tesouro_treatment.loc[(df_tesouro_treatment['qt'] != 0) &
                                                   (df_tesouro_treatment['vl_total'] > 0) &
                                                   (df_tesouro_treatment['data'].between(date_interval[0], date_interval[1])), 'vl_total'].sum()

        # Cálculo dos valores resgatados.
        vl_resgate = df_tesouro_treatment.loc[(df_tesouro_treatment['qt'] != 0) &
                                              (df_tesouro_treatment['vl_total'] < 0) &
                                              (df_tesouro_treatment['data'] <= date_interval[1]), 'vl_total'].sum()

        vl_resgate_delta = df_tesouro_treatment.loc[(df_tesouro_treatment['qt'] != 0) &
                                                    (df_tesouro_treatment['vl_total'] < 0) &
                                                    (df_tesouro_treatment['data'].between(date_interval[0], date_interval[1])), 'vl_total'].sum()

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
        