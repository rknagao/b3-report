# %%
import json
import pandas as pd
import yfinance as yf

# %%
# Variábeis globais
with open('src/config.json', 'r') as f:
    config = json.load(f)

PATH_DATA_CLEAN = '../data/3.clean/'

dict_codigo = {
    'cdi': 4391,
    'ipca': 433,
    'ibov': '^BVSP',
    'sp500': '^GSPC'
}

# %%
def consulta_bc(bench):
    url = f'http://api.bcb.gov.br/dados/serie/bcdata.sgs.{dict_codigo[bench]}/dados?formato=json'
    df = pd.read_json(url)
    df['data'] = pd.to_datetime(df['data'], dayfirst=True)
    df.columns = ['dt_competencia', bench]
    #df.rename(columns={'data':'dt_competencia'}, inplace=True)
    #df.set_index('data', inplace=True)
    return df

# %%
cdi = consulta_bc('cdi')
cdi.head()

# %%
ipca = consulta_bc('ipca')
ipca.head()

# %%
def load_data_yfinance(codigo):
    '''
    Objetivo: extrair e aplicar tratamento de índices obtidos do Yahoo Finance.
    Args: 
        - ticker: nome do ativo
    Return:
        - df_final: dataframe
    '''
    ticker = dict_codigo[codigo]

    # Extraindo os dados do yfinance.
    df = yf.download(ticker, interval='1d', start = '2018-12-01')['Adj Close'].reset_index(drop=False)
    df.columns = ['dt_competencia', ticker]

    # Obtendo apenas o primeiro registro de cada mês.
    df['ano'] = df['dt_competencia'].dt.year
    df['mes'] = df['dt_competencia'].dt.month
    df['dia'] = df['dt_competencia'].dt.day
    df_data = df.groupby(['ano','mes']).agg({'dia':'min'}).reset_index(drop=False)
    df_final = pd.merge(df, df_data, on=['ano','mes','dia'], how='inner')
    df_final['dt_competencia'] = pd.to_datetime(dict(year=df_final['ano'], month=df_final['mes'], day=1))

    # Calculando a variação mensal do índice.
    df_final[codigo] = ((df_final[ticker] / df_final[ticker].shift(1) - 1) * 100).fillna(0).round(2)
    df_final = df_final[['dt_competencia', codigo]].loc[df_final['dt_competencia'] >= '2019-01-1']

    return df_final

# %%
ibov = load_data_yfinance('ibov')
ibov.head()

# %%
sp500 = load_data_yfinance('sp500')
sp500.head()

# %%
# Juntando tudo.
df_final = pd.DataFrame()
df_final = pd.merge(ibov, sp500, on='dt_competencia', how='inner')
df_final = pd.merge(df_final, cdi, on='dt_competencia', how='inner')
df_final = pd.merge(df_final, ipca, on='dt_competencia', how='inner')


# %%
# Exportando o dataset limpo.
df_final.to_csv(config['data']['path']['clean']['benchmark'], index=False, encoding='utf8')


