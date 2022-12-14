import altair as alt
import datetime
import dateutil
import json
import pandas as pd
import os
import streamlit as st
import local_lib as lib

##########################
## CONFIGURAÇÕES GERAIS ##
##########################

st.header('🐢 Tesouro Direto')

if ('import_state' not in st.session_state) or (st.session_state['import_state'] != 'ready'):
    #st.write(st.session_state)
    st.warning('Insira dados na aba de importação.')

else:    
    DF = st.session_state['tesouro']
    #LIST_TICKER = DF['ticker'].unique().tolist()
    #DF_TESOURO = df.loc[df['tp_ativo'] == 'Tipo 1: tesouro']
    #st.dataframe(DF_TESOURO)
    #st.markdown('------')

    st.markdown('''
    #### Tabela 1: Evolução mensal
    A tabela dinâmica abaixo apresenta o valor acumulado e atualizado até o último dia de cotação do Tesouro Direto.
    ''')

    df = lib.etl_historic_price_tesouro(DF)
    #st.dataframe(df)
    #df.to_csv('data.csv', index=False)
    #st.write(type(df.iloc[0,0]))
    df = lib.create_column_last_day(df, col_index='ticker', col_date='data')
    #st.dataframe(df)
    
    list_ticker = st.multiselect('Escolha o(s) investimento(s):',
                                DF['ticker'].unique().tolist(),
                                DF['ticker'].unique().tolist())

    df_plot = df.loc[(df['ticker'].isin(list_ticker)) &
                     (df['dummy_ultimo_dia'] == 1)]
    
    tab1, data_col = lib.custom_pivot_table(df_plot, 'vl_atualizado')
    st.dataframe(tab1.style.format(subset=data_col, formatter="{:.2f}"))


    st.markdown('----- PAREI AQUI ------------')

    @st.cache(suppress_st_warning=True)
    def extract_tesouro(list_ticker):
        #Objetivo: criar um dataframe dos preços históricos do Tesouro Direto.

        dt_min = DF_TESOURO['data'].min()
        
        # Extrair
        url = 'https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv'
        df_api = pd.read_csv(url, sep=';', decimal=',')

        # Transformar
        df_api['data'] = pd.to_datetime(df_api['Data Base'], dayfirst=True).dt.date
        df_api['ticker'] = df_api['Tipo Titulo'].astype(str) + ' ' + df_api['Data Vencimento'].str[6:]
        df_api = df_api.loc[(df_api['ticker'].isin(list_ticker)) & (df_api['data'] >= dt_min)]
        df_api.rename(columns={'PU Base Manha':'preco'}, inplace=True)
        df_api['preco'] = round(df_api['preco'].astype(float), 2)
        df_api = df_api[['data', 'ticker', 'preco']].sort_values(by=['ticker','data'], ascending=True)
        
        return df_api


    def transformation_tesouro(df_api):
        # Juntar com relatórios da B3
        df = pd.merge(df_api[['data', 'ticker', 'preco']],
                      DF_TESOURO[['data', 'ticker', 'qtd']],
                      on=['data','ticker'],
                      how='left').fillna(0)

        
        # Calculando a quantidade acumulada de cada ticker
        for i in DF_TESOURO['ticker'].unique():
            df.loc[df['ticker'] == i, 'qtd_acum'] = df.loc[df['ticker'] == i, 'qtd'].cumsum(skipna=True)
            
        df = df.loc[df['qtd_acum'] != 0]
        df['vl_atualizado'] = (df['qtd_acum'] * df['preco']).round(2)

        # Agregando tudo

        return df


    def plot2(df):
        '''
        Objetivo: criar gráfico interativo com evolução da carteira e benchmarks.
        Input:
            - df (dataframe): tab2.
        Output:
            - plot (altair_chart): gráfico.
        '''    
        df['data_lag'] = df['data'].shift(-1)

        # Estética.
        alt.themes.enable("streamlit")

        hover = alt.selection_single(
            fields=["data"],
            nearest=True,
            on="mouseover",
            empty="none",
        )

        lines = (
            alt.Chart(df, height=500, title="Evolução dos Investimentos Individuais")
            .mark_line()
            .encode(
                x=alt.X("data", title="Data"),
                y=alt.Y("vl_atualizado", title="Valor total (R$)"),
                color=alt.Color("ticker", title='Legenda')
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
                y="vl_atualizado",
                opacity=alt.condition(hover, alt.value(0.3), alt.value(0)),
                tooltip=[
                    alt.Tooltip("yearmonthdate(data_lag)", title="Data"),
                    alt.Tooltip("ticker", title="Legenda"),
                    alt.Tooltip("vl_atualizado", title="Valor (R$)"),
                ],
            )
            .add_selection(hover)
        )

        chart = (lines + points + tooltips).interactive()
        plot = st.altair_chart(chart.interactive(), use_container_width=True)
        return plot


    df_api = extract_tesouro(list_ticker)
    #st.dataframe(df_parte2)
    df_parte2 = transformation_tesouro(df_api)
    #st.dataframe(df_parte2)
    plot2(df_parte2)


"""
tesouro = bunbot.investimento('tesouro', 'src/config.json')
df = tesouro.load_data()
df = tesouro.preprocessing(df)



benchmark = bunbot.investimento('benchmark', 'src/config.json')
df_benchmark = benchmark.load_data()


###########
## FRONT ##
###########


# ISSO PRECISA SER ARRUMADO!
dt_min = st.sidebar.date_input(label='Selecione a data inicial:', value=datetime.datetime(2019,1,1).date())
#st.write(type(df['dt_competencia'][0]))
#st.write(type(dt_min))
#df = df.loc[df['dt_competencia'] >= dt_min]


#teste = st.radio('aeefa', ('1', '2', st.date_input('teste2', value=datetime(2020,1,1).date())))
#st.write(teste)

#st.title('Bunbot Investimentos.')
st.header('Tesouro Direto 🐢')


################################
## TABELA 1 - TABELA DINÂMICA ##
################################

st.subheader('Parte 1 - Tabela dinâmica')
st.write('Tabela dinâmica com os valores mensais em Tesouro Direto.')


list_index = st.multiselect(
    'Escolha o(s) índice(s):',
    df['indice'].unique().tolist(),
    df['indice'].unique().tolist())


def criar_tabela1(df, list_index):
    '''
    Objetivo: criar uma tabela dinâmica a partir do dataframe.
    Args:
        - df: dataframe.
        - list_index: seleção de índices a serem considerados.
    Return:
        - tab1: dataframe. 
    '''
    df = df.loc[df['indice'].isin(list_index)]

    tab1 = pd.pivot_table(df,
                        values=['valor_atualizado'],
                        columns=['dt_competencia'],
                        index=['indice', 'ticker','dt_vencimento'],
                        aggfunc='sum',
                        margins=True,
                        margins_name='Total',
                        observed=True
                        ).astype(float)\
                         .fillna(0)\
                         .round(2)
                         #.astype(int)

    list_col = [i[1] for i in tab1.columns]
    tab1.columns = list_col
    tab1 = tab1.reset_index(drop=False)
    data_cols=tab1.columns[3:].tolist()

    return tab1, data_cols


tab1, data_col = criar_tabela1(df, list_index)
st.dataframe(tab1.style.format(subset=data_col, formatter="{:.2f}"))


#################################
## TABELA 2 - GRÁFICO DE LINHA ##
#################################

# Gráfico de linhas contendo o valor atualizado total dos ativos selecionados pelo usuário.


st.subheader('Parte 2 - Gráfico de linhas')
st.write('Gráfico de linha apresentando a evolução mensal dos investimentos em tesouro direto.')

# Input de tickers a serem somados.
list_ticker = st.multiselect(
    'Escolha o(s) ticker(s):',
    df['ticker'].unique().tolist(),
    df['ticker'].unique().tolist())

# Input de benchmarks para a comparação com o gráfico.
list_benchmark = st.multiselect(
    'Escolha o(s) benchmarks(s):',
    ['cdi', 'ipca','ibov', 'sp500'],
    ['cdi', 'ipca','ibov', 'sp500'])


def criar_tabela2(df_ticker, list_ticker, df_benchmark, list_benchmark):  
    '''
    Objetivo: criar um dataframe contendo os valores totais de tickers e benchmarks selecionados.
    Input:
        - df_ticker: dataframe contendo o tesouro direto.
        - list_ticker: lista dos tickers inputados.
        - df_benchmark: dataframe contendo os benchmarks.
        - list_benchmark: lista dos benchmarks inputados.
    Output:
        - df_final: dataframe resultante a ser usada em um plot.
        - float_col: nome das colunas com decimais, a ser usada na formatação do streamlit.
    '''

    # Preparar dados de ticker e benchmark
    df_ticker = df_ticker[['dt_competencia','ticker','quantidade', 'valor_investido', 'valor_atualizado']]
    df_ticker = df_ticker.loc[(df_ticker['ticker'].isin(list_ticker)) &
                              (df_ticker['quantidade'] > 0)].sort_values(['ticker','dt_competencia'], ascending=True)
    
    df_benchmark = df_benchmark[['dt_competencia'] + list_benchmark]
    df = pd.merge(df_ticker, df_benchmark, on='dt_competencia', how='inner')
    df_concat = pd.DataFrame()

    # Calculando os valores fictícios de benchmark por ticker:
    for i in list_ticker:
        df_temp = df.loc[df['ticker'] == i].reset_index(drop=True)
        valor_inicial = df_temp.loc[0, 'valor_investido']

        for j in list_benchmark:
            list_perc_benchmark = df_temp[j].tolist()[1:]
            list_vl_benchmark = [valor_inicial]

            for k in list_perc_benchmark:
                list_vl_benchmark.append(round(list_vl_benchmark[-1] * (1 + k/100), 2))

            df_temp[f'benchmark_{j}'] = list_vl_benchmark
        
        df_concat = pd.concat([df_concat, df_temp], axis=0)

    # Criando a tabela agregada.
    dict_agg = dict([('valor_investido','sum'), ('valor_atualizado', 'sum')] + [(b, 'mean') for b in list_benchmark])
    df_agg = df_concat.groupby('dt_competencia').agg(dict_agg).round(2).reset_index(drop=False)

    # Calculando os benchmarks.
    df_agg['vl_invested'] = (df_agg['valor_investido'] - df_agg['valor_investido'].shift(1).fillna(0)).round(2)
    for i in list_benchmark:
        df_agg[f"{i}_return"] = bunbot.compare.calculate_return(array_vl_invested=df_agg['vl_invested'], array_pct_var=df_agg[i])

    # Adotand um formato para plot.
    value_vars = ['valor_atualizado'] + [f"{i}_return" for i in list_benchmark]
    df_melt = pd.melt(df_agg, id_vars=['dt_competencia'], value_vars=value_vars)
    df_melt['dt_competencia_lag'] = df_melt['dt_competencia'].shift(-1)
    df_melt['variable'].replace({'valor_atualizado': 'carteira',
                                 'cdi_return': 'CDI',
                                 'ipca_return': 'IPCA',
                                 'sp500_return': 'S&P 500',
                                 'ibov_return': 'Ibovespa'}, inplace=True)

    df_final = df_melt
    float_col='value'

    return df_final, float_col


tab2, float_col = criar_tabela2(df, list_ticker, df_benchmark, list_benchmark)
#st.dataframe(tab2.style.format(subset=float_col, formatter="{:.2f}"))


def plot2(df):
    '''
    Objetivo: criar gráfico interativo com evolução da carteira e benchmarks.
    Input:
        - df (dataframe): tab2.
    Output:
        - plot (altair_chart): gráfico.
    '''    
    # Estética.
    alt.themes.enable("streamlit")

    hover = alt.selection_single(
        fields=["dt_competencia"],
        nearest=True,
        on="mouseover",
        empty="none",
    )

    lines = (
        alt.Chart(df, height=500, title="Evolução da carteira")
        .mark_line()
        .encode(
            x=alt.X("dt_competencia", title="Data"),
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
            x="yearmonthdate(dt_competencia)",
            y="value",
            opacity=alt.condition(hover, alt.value(0.3), alt.value(0)),
            tooltip=[
                alt.Tooltip("yearmonth(dt_competencia_lag)", title="Data"),
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
"""