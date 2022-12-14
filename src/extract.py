# %%
import datetime
import json
import os
import pandas as pd
import warnings

# %%
# Variábeis globais
with open('src/config.json', 'r') as f:
    config = json.load(f)


# %%
def get_sheets(file):
    # Objetivo: identificar todas as abas de um Excel.
    xl = pd.ExcelFile(config['data']['path']['raw'] + file, engine='openpyxl')
    return xl.sheet_names


def excel_to_df(file, sheet):
    # Objetivo: ler uma aba específica do Excel e convertê-lo em um dataframe.
    xl = pd.ExcelFile(config['data']['path']['raw'] + file, engine='openpyxl')
    df = xl.parse(sheet)
    
    return df


def organize_df(file, sheet, df, df_acao, df_bdr, df_etf, df_rf, df_td):
    # Objetivo: organizar os dataframes criados por (1) aba e (2) mês de competência.

    # Identificar a data de competência.
    year = int(file[8:12])
    month = int(file[13:15])    
    date = datetime.date(year, month, 1)
    df.loc[:, 'dt_competencia'] = date

    # Organizar os dados por temas.
    if sheet == 'Acoes':
        df_acao = pd.concat([df_acao, df], ignore_index=True)

    elif sheet == 'BDR' : 
        df_bdr = pd.concat([df_bdr, df], ignore_index=True)

    elif sheet == 'ETF' : 
        df_etf = pd.concat([df_etf, df], ignore_index=True)

    elif sheet == 'Renda Fixa' : 
        df_rf = pd.concat([df_rf, df], ignore_index=True)

    else: 
        df_td = pd.concat([df_td, df], ignore_index=True)

    return df_acao, df_bdr, df_etf, df_rf, df_td


def save_df(df_acao, df_bdr, df_etf, df_rf, df_td):
    # Objetivo: salvar os dataframes.
    df_acao.to_csv(config['data']['path']['interim']['acao'], encoding='utf8', index=False)
    df_bdr.to_csv(config['data']['path']['interim']['bdr'], encoding='utf8', index=False)
    df_etf.to_csv(config['data']['path']['interim']['etf'], encoding='utf8', index=False)
    df_rf.to_csv(config['data']['path']['interim']['rf'], encoding='utf8', index=False)
    df_td.to_csv(config['data']['path']['interim']['tesouro'], encoding='utf8', index=False)


def load_data():
    # Objetivo: executar integralmente a extração dos dados.

    # Criar dataframe para cada aba.
    df_acao = pd.DataFrame()    # Ações
    df_bdr = pd.DataFrame()     # BDR
    df_etf = pd.DataFrame()     # ETF
    df_rf = pd.DataFrame()      # Renda Fixa
    df_td = pd.DataFrame()      # Tesouro Direto

    warnings.simplefilter("ignore")
    # Ler todos os arquivos na pasta de dados brutos.
    list_file = os.listdir(config['data']['path']['raw'])
    for i in list_file:     
        list_sheet = get_sheets(i)

        for j in list_sheet:
            df = excel_to_df(i, j)
            df_acao, df_bdr, df_etf, df_rf, df_td = organize_df(i, j, df, df_acao, df_bdr, df_etf, df_rf, df_td)
            
    warnings.simplefilter("default")

    save_df(df_acao, df_bdr, df_etf, df_rf, df_td)

# %%
load_data()



# %%
