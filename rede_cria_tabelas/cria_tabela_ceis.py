import requests
import pandas as pd
import sqlite3
import zipfile
import io
import os
from datetime import datetime

# --- Configuração ---
DOWNLOAD_URL = "https://portaldatransparencia.gov.br/download-de-dados/ceis.zip"
DB_EXTERNOS = "dados-publicos/dados_externos.db"
CEIS_TABLE_NAME = "ceis"
METADATA_FILE = "dados-publicos/ceis_metadata.json"

def get_last_modified_header():
    """Busca o cabeçalho 'Last-Modified' da URL para verificar a data do arquivo."""
    try:
        with requests.get(DOWNLOAD_URL, stream=True) as r:
            r.raise_for_status()
            return r.headers.get('Last-Modified')
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a URL: {e}")
        return None

def needs_update(last_modified_online):
    """Verifica se o arquivo local está desatualizado."""
    if not os.path.exists(DB_EXTERNOS) or not os.path.exists(METADATA_FILE):
        return True

    with open(METADATA_FILE, 'r') as f:
        import json
        metadata = json.load(f)
        last_modified_local = metadata.get('last_modified')

    if last_modified_local != last_modified_online:
        return True

    print("A base de dados do CEIS já está atualizada.")
    return False

def download_and_process_ceis():
    """Baixa e processa os dados do CEIS, inserindo em um banco de dados SQLite."""
    print("Iniciando o processo de download e atualização da base CEIS...")

    last_modified_online = get_last_modified_header()
    if not last_modified_online:
        print("Não foi possível obter a data de modificação do arquivo online. Abortando.")
        return

    if not needs_update(last_modified_online):
        return

    print(f"Nova versão do arquivo CEIS encontrada (data: {last_modified_online}). Baixando...")

    try:
        r = requests.get(DOWNLOAD_URL)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o arquivo: {e}")
        return

    print("Download concluído. Processando o arquivo...")

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            csv_filename = next((name for name in z.namelist() if name.lower().endswith('.csv')), None)
            if not csv_filename:
                print("Nenhum arquivo CSV encontrado dentro do ZIP.")
                return

            print(f"Lendo o arquivo CSV: {csv_filename}")
            with z.open(csv_filename) as f:
                df = pd.read_csv(f, sep=';', encoding='latin-1', dtype=str)

    except Exception as e:
        print(f"Erro ao processar o arquivo ZIP/CSV: {e}")
        return

    print("Arquivo CSV lido com sucesso. Formatando os dados...")

    # Renomeia colunas para facilitar o acesso
    df.columns = [
        'TIPO_DE_PESSOA', 'CPF_OU_CNPJ_DO_SANCIONADO', 'NOME_DO_SANCIONADO',
        'NOME_INFORMADO_PELO_ORGAO_SANCIONADOR', 'RAZAO_SOCIAL_CADASTRO_RECEITA',
        'NOME_FANTASIA_CADASTRO_RECEITA', 'TIPO_DE_SANCAO', 'DATA_INICIO_SANCAO',
        'DATA_FINAL_SANCAO', 'ORGAO_SANCIONADOR', 'UF_ORGAO_SANCIONADOR'
    ]

    # Filtra apenas por pessoas jurídicas e seleciona as colunas de interesse
    df_pj = df[df['TIPO_DE_PESSOA'] == 'PESSOA JURÍDICA'].copy()

    colunas_interesse = {
        'CPF_OU_CNPJ_DO_SANCIONADO': 'cnpj',
        'NOME_DO_SANCIONADO': 'nome',
        'TIPO_DE_SANCAO': 'sancao',
        'ORGAO_SANCIONADOR': 'orgao',
        'DATA_INICIO_SANCAO': 'data_inicio',
        'DATA_FINAL_SANCAO': 'data_final'
    }

    df_ceis = df_pj[list(colunas_interesse.keys())].copy()
    df_ceis.rename(columns=colunas_interesse, inplace=True)

    # Limpa e padroniza a coluna de CNPJ
    df_ceis['cnpj'] = df_ceis['cnpj'].str.replace(r'\D', '', regex=True)
    df_ceis.dropna(subset=['cnpj'], inplace=True)
    df_ceis = df_ceis[df_ceis['cnpj'].str.len() == 14]

    if df_ceis.empty:
        print("Nenhum CNPJ válido encontrado nos dados do CEIS.")
        return

    print(f"Encontrados {len(df_ceis)} registros de CNPJs punidos no CEIS.")

    # Salva no banco de dados
    try:
        print(f"Salvando dados na tabela '{CEIS_TABLE_NAME}' do banco '{DB_EXTERNOS}'...")
        conn = sqlite3.connect(DB_EXTERNOS)
        # Usa 'append' para não sobrescrever a tabela cnep, se ela já existir
        df_ceis.to_sql(CEIS_TABLE_NAME, conn, if_exists='replace', index=False)

        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{CEIS_TABLE_NAME}_cnpj ON {CEIS_TABLE_NAME}(cnpj);")
        conn.close()
        print("Dados do CEIS salvos e indexados com sucesso.")

        # Salva os metadados
        with open(METADATA_FILE, 'w') as f:
            import json
            metadata = {
                'last_modified': last_modified_online,
                'update_timestamp_utc': datetime.utcnow().isoformat()
            }
            json.dump(metadata, f)
        print(f"Metadados do CEIS salvos em {METADATA_FILE}.")

    except Exception as e:
        print(f"Erro ao salvar os dados do CEIS no banco de dados: {e}")

if __name__ == "__main__":
    download_and_process_ceis()
    print("\nProcesso concluído.")
    input("Pressione Enter para sair.")
