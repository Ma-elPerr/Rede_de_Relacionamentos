import requests
import pandas as pd
import sqlite3
import zipfile
import io
import os
from datetime import datetime

# --- Configuração ---
CNEP_URL = "https://portaldatransparencia.gov.br/download-de-dados/cnep"
# Assumindo que o arquivo é um zip, como é comum em portais de dados abertos.
# O nome do arquivo dentro do zip pode variar, o script tentará encontrar o CSV.
DOWNLOAD_URL = "https://portaldatransparencia.gov.br/download-de-dados/cnep.zip"
DB_EXTERNOS = "dados-publicos/dados_externos.db"
CNEP_TABLE_NAME = "cnep"
METADATA_FILE = "dados-publicos/cnep_metadata.json"

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

    print("A base de dados do CNEP já está atualizada.")
    return False

def download_and_process_cnep():
    """Baixa e processa os dados do CNEP, inserindo em um banco de dados SQLite."""
    print("Iniciando o processo de download e atualização da base CNEP...")

    last_modified_online = get_last_modified_header()
    if not last_modified_online:
        print("Não foi possível obter a data de modificação do arquivo online. Abortando.")
        return

    if not needs_update(last_modified_online):
        return

    print(f"Nova versão do arquivo CNEP encontrada (data: {last_modified_online}). Baixando...")

    try:
        r = requests.get(DOWNLOAD_URL)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o arquivo: {e}")
        return

    print("Download concluído. Processando o arquivo...")

    try:
        # Usa um buffer de memória para não precisar salvar o ZIP em disco
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            # Encontra o primeiro arquivo CSV dentro do ZIP
            csv_filename = next((name for name in z.namelist() if name.lower().endswith('.csv')), None)
            if not csv_filename:
                print("Nenhum arquivo CSV encontrado dentro do ZIP.")
                return

            print(f"Lendo o arquivo CSV: {csv_filename}")
            with z.open(csv_filename) as f:
                # A codificação 'latin-1' é comum em arquivos do governo brasileiro
                df = pd.read_csv(f, sep=';', encoding='latin-1', dtype=str)

    except Exception as e:
        print(f"Erro ao processar o arquivo ZIP/CSV: {e}")
        return

    print("Arquivo CSV lido com sucesso. Formatando os dados...")

    # Renomeia colunas para facilitar o acesso, removendo acentos e espaços
    df.columns = [
        'CADASTRO', 'CODIGO_SANCAO', 'TIPO_PESSOA', 'CPF_OU_CNPJ_DO_SANCIONADO',
        'NOME_DO_SANCIONADO', 'NOME_INFORMADO_PELO_ORGAO_SANCIONADOR',
        'RAZAO_SOCIAL_CADASTRO_RECEITA', 'NOME_FANTASIA_CADASTRO_RECEITA',
        'NUMERO_DO_PROCESSO', 'CATEGORIA_DA_SANCAO', 'VALOR_DA_MULTA',
        'DATA_INICIO_SANCAO', 'DATA_FINAL_SANCAO', 'DATA_PUBLICACAO',
        'PUBLICACAO', 'DETALHAMENTO_DO_MEIO_DE_PUBLICACAO',
        'DATA_DO_TRANSITO_EM_JULGADO', 'ABRANGENCIA_DA_SANCAO',
        'ORGAO_SANCIONADOR', 'UF_ORGAO_SANCIONADOR', 'ESFERA_ORGAO_SANCIONADOR',
        'FUNDAMENTACAO_LEGAL', 'DATA_ORIGEM_INFORMACAO', 'ORIGEM_INFORMACOES',
        'OBSERVACOES'
    ]

    # Filtra apenas por pessoas jurídicas e seleciona as colunas de interesse
    df_pj = df[df['TIPO_PESSOA'] == 'PESSOA JURÍDICA'].copy()

    colunas_interesse = {
        'CPF_OU_CNPJ_DO_SANCIONADO': 'cnpj',
        'NOME_DO_SANCIONADO': 'nome',
        'CATEGORIA_DA_SANCAO': 'sancao',
        'ORGAO_SANCIONADOR': 'orgao',
        'DATA_INICIO_SANCAO': 'data_inicio',
        'DATA_FINAL_SANCAO': 'data_final'
    }

    df_cnep = df_pj[list(colunas_interesse.keys())].copy()
    df_cnep.rename(columns=colunas_interesse, inplace=True)

    # Remove qualquer formatação do CNPJ, deixando apenas os dígitos
    df_cnep['cnpj'] = df_cnep['cnpj'].str.replace(r'\D', '', regex=True)

    # Remove CNPJs nulos ou inválidos e garante que tenham 14 dígitos
    df_cnep.dropna(subset=['cnpj'], inplace=True)
    df_cnep = df_cnep[df_cnep['cnpj'].str.len() == 14]

    if df_cnep.empty:
        print("Nenhum CNPJ válido encontrado nos dados do CNEP.")
        return

    print(f"Encontrados {len(df_cnep)} registros de CNPJs punidos.")

    # Salva no banco de dados
    try:
        print(f"Salvando dados na tabela '{CNEP_TABLE_NAME}' do banco '{DB_EXTERNOS}'...")
        conn = sqlite3.connect(DB_EXTERNOS)
        df_cnep.to_sql(CNEP_TABLE_NAME, conn, if_exists='replace', index=False)

        # Cria um índice para otimizar as consultas
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{CNEP_TABLE_NAME}_cnpj ON {CNEP_TABLE_NAME}(cnpj);")
        conn.close()
        print("Dados salvos e indexados com sucesso.")

        # Salva os metadados
        with open(METADATA_FILE, 'w') as f:
            import json
            metadata = {
                'last_modified': last_modified_online,
                'update_timestamp_utc': datetime.utcnow().isoformat()
            }
            json.dump(metadata, f)
        print(f"Metadados salvos em {METADATA_FILE}.")

    except Exception as e:
        print(f"Erro ao salvar os dados no banco de dados: {e}")

if __name__ == "__main__":
    download_and_process_cnep()
    print("\nProcesso concluído.")
    input("Pressione Enter para sair.")
