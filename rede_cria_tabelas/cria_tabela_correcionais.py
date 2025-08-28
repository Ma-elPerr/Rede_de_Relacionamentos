# -*- coding: utf-8 -*-
"""
Script para processar os Dados Correcionais da CGU.

Este script assume que o arquivo 'dados_correcionais.zip' foi baixado
manualmente do portal de dados abertos e colocado no diretório
'dados-publicos-zip/'. A automação do download não foi possível devido
a limitações de acesso ao link (SharePoint).

O script processa os dados de sanções aplicadas a pessoas físicas,
limpa o CPF e salva os dados em uma tabela 'correcionais' no banco de dados
'dados_externos.db'.
"""

import pandas as pd
import sqlite3
import os
import zipfile
import io

def processa_dados_correcionais():
    print("Iniciando o processamento dos Dados Correcionais...")

    # Caminhos
    zip_dir = 'dados-publicos-zip'
    db_dir = 'dados-publicos'
    zip_path = os.path.join(zip_dir, 'dados_correcionais.zip')
    db_path = os.path.join(db_dir, 'dados_externos.db')

    # Garante que o diretório de saída exista
    os.makedirs(db_dir, exist_ok=True)

    # 1. Verifica se o arquivo ZIP existe
    if not os.path.exists(zip_path):
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"AVISO: O arquivo '{zip_path}' não foi encontrado.")
        print("Este script não baixa o arquivo automaticamente.")
        print("Por favor, baixe o arquivo de 'Dados Correcionais' do portal de dados")
        print("da CGU e coloque-o na pasta 'dados-publicos-zip/' antes de continuar.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return

    print(f"Processando o arquivo: {zip_path}")

    # 2. Leitura dos CSVs de dentro do ZIP
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Encontra os nomes corretos dos arquivos dentro do zip
            # Ex: 20240101_Sancoes.csv
            sancoes_filename = next((s for s in z.namelist() if 'Sancoes' in s and s.endswith('.csv')), None)

            if not sancoes_filename:
                print("ERRO: Não foi possível encontrar o arquivo de Sanções dentro do ZIP.")
                return

            print(f"Lendo {sancoes_filename} do arquivo zip...")
            with z.open(sancoes_filename) as f:
                # Especifica o encoding correto e o delimitador
                df_sancoes = pd.read_csv(io.TextIOWrapper(f, 'latin-1'), delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Erro ao ler o arquivo ZIP ou CSV: {e}")
        return

    # 3. Filtragem e Limpeza dos Dados
    print("Filtrando e limpando os dados...")

    # Filtra para manter apenas sanções aplicadas a Pessoas Físicas
    df_pf = df_sancoes[df_sancoes['TIPO_PESSOA'] == 'F'].copy()

    # Seleciona e renomeia as colunas de interesse
    colunas = {
        'CPF_CNPJ_SANCIONADO': 'cpf',
        'NOME_SANCIONADO': 'nome',
        'TIPO_SANCAO': 'sancao',
        'DATA_INICIO_SANCAO': 'data_inicio',
        'DATA_FIM_SANCAO': 'data_final',
        'ORGAO_SANCIONADOR': 'orgao'
    }
    df_pf = df_pf[colunas.keys()].rename(columns=colunas)

    # Remove qualquer formatação do CPF
    df_pf['cpf'] = df_pf['cpf'].str.replace(r'\D', '', regex=True)

    # Remove linhas onde o CPF é nulo ou inválido
    df_pf.dropna(subset=['cpf'], inplace=True)
    df_pf = df_pf[df_pf['cpf'].str.len() == 11]

    if df_pf.empty:
        print("Nenhuma sanção válida para pessoas físicas encontrada.")
        return

    print(f"Encontradas {len(df_pf)} sanções aplicáveis a pessoas físicas.")

    # 4. Salva no banco de dados SQLite
    print(f"Salvando dados na tabela 'correcionais' em {db_path}...")
    try:
        conn = sqlite3.connect(db_path)

        # 'replace' para garantir que os dados sejam sempre os mais recentes
        df_pf.to_sql('correcionais', conn, if_exists='replace', index=False)

        # Cria índice para otimizar consultas
        print("Criando índice na coluna 'cpf'...")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_correcionais_cpf ON correcionais (cpf);")

        conn.close()
        print("Processo concluído com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar os dados no banco de dados: {e}")


if __name__ == '__main__':
    processa_dados_correcionais()
