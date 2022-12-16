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
    #### Tabela 1: Evolução mensal
    A tabela dinâmica abaixo apresenta o valor acumulado e atualizado até o último dia de cotação do Tesouro Direto.
    ''')

    df_hist_tesouro = lib.etl_tesouro_historic_price()
    df_tesouro_historico = lib.merge_historic_tesouro(df_hist_tesouro, df_tesouro)
    df_tesouro_historico = lib.create_column_last_day(df_tesouro_historico)
    
    # Filtro de tickers.
    list_ticker = st.multiselect('Escolha o(s) investimento(s):',
                                 df_tesouro_historico['ticker'].unique().tolist(),
                                 df_tesouro_historico['ticker'].unique().tolist())

    df_tesouro_historico = df_tesouro_historico.loc[(df_tesouro_historico['ticker'].isin(list_ticker)) &
                                                    (df_tesouro_historico['dummy_ultimo_dia'] == 1)]
    
    tab1, data_col = lib.custom_pivot_table(df_tesouro_historico, col_value='vl_atualizado')
    st.dataframe(tab1.style.format(subset=data_col, formatter="{:.2f}"))


    ##########################################
    # TAB2 - GRÁFICO DE LINHA COM BENCHMARKS #
    ##########################################

    df_hist_bench = lib.etl_benchmark_historic_price()
    df_tesouro_historico_agg = lib.merge_historic_benchmark(df_tesouro_historico, df_hist_bench)

    # TEM ALGO ERRADO NESTA PASSAGEM
    # Dica: user o arquivo teste.py. Estou rodando tudo lá primeiro e depois passando aqui só o que dá certo.
    tab2 = lib.custom_data_lineplot(df_tesouro_historico_agg, ['ibov', 'sp500', 'cdi', 'ipca'])
    tab2.to_csv('src/teste.csv', index=False)

    def plot2(df):
        # Estética.
        alt.themes.enable("streamlit")

        hover = alt.selection_single(
            fields=["data"],
            nearest=True,
            on="mouseover",
            empty="none",
        )

        lines = (
            alt.Chart(df, height=500, title="Evolução da Carteira")
            .mark_line()
            .encode(
                x=alt.X("data", title="Data"),
                y=alt.Y("value", title="Valor total (R$)"),
                color=alt.Color("variable", title='Legenda')
            )
        )

        # Draw points on the line, and highlight based on selection
        points = lines.transform_filter(hover).mark_circle(size=90)

        # Draw a rule at the location of the selection
        tooltips = (
            alt.Chart(df)
            .mark_rule()
            .encode(
                x="yearmonthdate(data)",
                y="value",
                opacity=alt.condition(hover, alt.value(0.3), alt.value(0)),
                tooltip=[
                    alt.Tooltip("yearmonthdate(data_lag)", title="Data"),
                    alt.Tooltip("variable", title="Legenda"),
                    alt.Tooltip("value", title="Valor (R$)"),
                ],
            )
            .add_selection(hover)
        )

        chart = (lines + points + tooltips).interactive()
        plot = st.altair_chart(chart.interactive(), use_container_width=True)
        return plot

    plot2(tab2)
    st.dataframe(tab2)
