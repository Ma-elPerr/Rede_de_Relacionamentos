# -*- coding: utf-8 -*-
"""
@author: rictom
https://github.com/rictom/cnpj-sqlite

A rotina:
    - descompacta os arquivos já baixados do site da receita;
    - cria uma base cnpj.db no formato sqlite;
    - cria indices nas colunas CNPJ, Razão Social, cpf/cnpj de sócios e nome de Sócios.
"""

import pandas as pd
import sqlite3
import sqlalchemy
import glob
import time
import dask.dataframe as dd
import os
import sys
import zipfile

pasta_compactados = r"dados-publicos-zip"  # local dos arquivos zipados da Receita
pasta_saida = r"dados-publicos"  # esta pasta deve estar vazia.
bApagaDescompactadosAposUso = True

def criar_cnpj_db(force_delete=False):
    """
    Cria o banco de dados cnpj.db a partir dos arquivos .zip baixados.
    """
    print(f'\n{time.asctime()}: Iniciando criação da base cnpj.db')

    cam_db = os.path.join(pasta_saida, 'cnpj.db')
    if os.path.exists(cam_db):
        if force_delete:
            print(f'Arquivo {cam_db} existente. Removendo por causa da opção --force-delete.')
            os.remove(cam_db)
        else:
            print(f'O arquivo {cam_db} já existe. Use --force-delete para recriá-lo.')
            return # Não retorna erro, apenas avisa e para.

    arquivos_zip = list(glob.glob(os.path.join(pasta_compactados, r'*.zip')))

    if len(arquivos_zip) != 37:
        print(f'AVISO: A pasta {pasta_compactados} deveria conter 37 arquivos zip, mas tem {len(arquivos_zip)}. A base ficará incompleta.')

    if not arquivos_zip:
        print(f'ERRO: Nenhum arquivo .zip encontrado em {pasta_compactados}.')
        sys.exit(1)

    print(f'{time.asctime()}: Descompactando {len(arquivos_zip)} arquivos...')
    for arq in arquivos_zip:
        print(f'{time.asctime()}: descompactando {arq}')
        try:
            with zipfile.ZipFile(arq, 'r') as zip_ref:
                zip_ref.extractall(pasta_saida)
        except zipfile.BadZipFile:
            print(f"ERRO: O arquivo {arq} está corrompido ou não é um arquivo zip válido. Pulando.")
            continue
    
    print(f'{time.asctime()}: Fim da descompactação.')

    engine = sqlite3.connect(cam_db)
    engine_url = f'sqlite:///{cam_db}'

    # carrega tabelas pequenas e indexa
    def carregaTabelaCodigo(extensaoArquivo, nomeTabela):
        arquivos = list(glob.glob(os.path.join(pasta_saida, '*' + extensaoArquivo)))
        if not arquivos:
            print(f"AVISO: Nenhum arquivo encontrado para {extensaoArquivo}. A tabela {nomeTabela} ficará vazia.")
            return
        arquivo = arquivos[0]
        print(f'Carregando arquivo {arquivo} na tabela {nomeTabela}')
        dtab = pd.read_csv(arquivo, dtype=str, sep=';', encoding='latin1', header=None, names=['codigo', 'descricao'])
        dtab.to_sql(nomeTabela, engine, if_exists='replace', index=None)
        engine.execute(f'CREATE INDEX IF NOT EXISTS idx_{nomeTabela} ON {nomeTabela}(codigo);')
        if bApagaDescompactadosAposUso:
            print(f'Apagando arquivo {arquivo}')
            os.remove(arquivo)

    carregaTabelaCodigo('.CNAECSV', 'cnae')
    carregaTabelaCodigo('.MOTICSV', 'motivo')
    carregaTabelaCodigo('.MUNICCSV', 'municipio')
    carregaTabelaCodigo('.NATJUCSV', 'natureza_juridica')
    carregaTabelaCodigo('.PAISCSV', 'pais')
    carregaTabelaCodigo('.QUALSCSV', 'qualificacao_socio')

    # carrega as tabelas grandes
    colunas_empresas = ['cnpj_basico', 'razao_social', 'natureza_juridica', 'qualificacao_responsavel', 'capital_social_str', 'porte_empresa', 'ente_federativo_responsavel']
    colunas_estabelecimento = ['cnpj_basico', 'cnpj_ordem', 'cnpj_dv', 'matriz_filial', 'nome_fantasia', 'situacao_cadastral', 'data_situacao_cadastral', 'motivo_situacao_cadastral', 'nome_cidade_exterior', 'pais', 'data_inicio_atividades', 'cnae_fiscal', 'cnae_fiscal_secundaria', 'tipo_logradouro', 'logradouro', 'numero', 'complemento', 'bairro', 'cep', 'uf', 'municipio', 'ddd1', 'telefone1', 'ddd2', 'telefone2', 'ddd_fax', 'fax', 'correio_eletronico', 'situacao_especial', 'data_situacao_especial']
    colunas_socios = ['cnpj_basico', 'identificador_de_socio', 'nome_socio', 'cnpj_cpf_socio', 'qualificacao_socio', 'data_entrada_sociedade', 'pais', 'representante_legal', 'nome_representante', 'qualificacao_representante_legal', 'faixa_etaria']
    colunas_simples = ['cnpj_basico', 'opcao_simples', 'data_opcao_simples', 'data_exclusao_simples', 'opcao_mei', 'data_opcao_mei', 'data_exclusao_mei']

    def sqlCriaTabela(nomeTabela, colunas):
        return f"CREATE TABLE IF NOT EXISTS {nomeTabela} ({', '.join([f'{c} TEXT' for c in colunas])})"

    engine.execute(sqlCriaTabela('empresas', colunas_empresas))
    engine.execute(sqlCriaTabela('estabelecimento', colunas_estabelecimento))
    engine.execute(sqlCriaTabela('socios_original', colunas_socios))
    engine.execute(sqlCriaTabela('simples', colunas_simples))

    def carregaTipo(nome_tabela, tipo, colunas):
        arquivos = list(glob.glob(os.path.join(pasta_saida, '*' + tipo)))
        if not arquivos:
            print(f"AVISO: Nenhum arquivo encontrado para o padrão *{tipo}. A tabela {nome_tabela} não será populada.")
            return
        print(f'Carregando {len(arquivos)} arquivo(s) para a tabela {nome_tabela}...')
        ddf = dd.read_csv(arquivos, sep=';', header=None, names=colunas, encoding='latin1', dtype=str, na_filter=None, blocksize=None)
        ddf.to_sql(nome_tabela, engine_url, index=None, if_exists='append', dtype=sqlalchemy.sql.sqltypes.TEXT)
        if bApagaDescompactadosAposUso:
            for arq in arquivos:
                print(f'Apagando o arquivo {arq}')
                os.remove(arq)
        print(f'Fim da carga para {nome_tabela}...', time.asctime())

    carregaTipo('empresas', '.EMPRECSV', colunas_empresas)
    carregaTipo('estabelecimento', '.ESTABELE', colunas_estabelecimento)
    carregaTipo('socios_original', '.SOCIOCSV', colunas_socios)
    carregaTipo('simples', '.SIMPLES.CSV.*', colunas_simples)

    sqls = '''
        ALTER TABLE empresas ADD COLUMN capital_social REAL;
        UPDATE empresas SET capital_social = CAST(REPLACE(capital_social_str, ',', '.') AS REAL);
        ALTER TABLE empresas DROP COLUMN capital_social_str;
        ALTER TABLE estabelecimento ADD COLUMN cnpj TEXT;
        UPDATE estabelecimento SET cnpj = cnpj_basico || cnpj_ordem || cnpj_dv;
        CREATE INDEX IF NOT EXISTS idx_empresas_cnpj_basico ON empresas (cnpj_basico);
        CREATE INDEX IF NOT EXISTS idx_empresas_razao_social ON empresas (razao_social);
        CREATE INDEX IF NOT EXISTS idx_estabelecimento_cnpj_basico ON estabelecimento (cnpj_basico);
        CREATE INDEX IF NOT EXISTS idx_estabelecimento_cnpj ON estabelecimento (cnpj);
        CREATE INDEX IF NOT EXISTS idx_estabelecimento_nomefantasia ON estabelecimento (nome_fantasia);
        CREATE INDEX IF NOT EXISTS idx_socios_original_cnpj_basico ON socios_original(cnpj_basico);
        CREATE TABLE socios AS SELECT te.cnpj as cnpj, ts.* FROM socios_original ts LEFT JOIN estabelecimento te ON te.cnpj_basico = ts.cnpj_basico WHERE te.matriz_filial='1';
        DROP TABLE IF EXISTS socios_original;
        CREATE INDEX IF NOT EXISTS idx_socios_cnpj ON socios(cnpj);
        CREATE INDEX IF NOT EXISTS idx_socios_cnpj_cpf_socio ON socios(cnpj_cpf_socio);
        CREATE INDEX IF NOT EXISTS idx_socios_nome_socio ON socios(nome_socio);
        CREATE INDEX IF NOT EXISTS idx_socios_representante ON socios(representante_legal);
        CREATE INDEX IF NOT EXISTS idx_socios_representante_nome ON socios(nome_representante);
        CREATE INDEX IF NOT EXISTS idx_simples_cnpj_basico ON simples(cnpj_basico);
        CREATE TABLE IF NOT EXISTS "_referencia" ("referencia" TEXT, "valor" TEXT);
    '''

    print('Início das transformações SQL:', time.asctime())
    ktotal = len(sqls.split(';'))
    for k, sql in enumerate(sqls.split(';')):
        if sql.strip():
            print('-' * 20 + f'\nExecutando parte {k + 1}/{ktotal}:\n', sql)
            engine.execute(sql)
    print('Fim das transformações SQL...', time.asctime())

    try:
        data_ref_files = list(glob.glob(os.path.join(pasta_saida, '*.EMPRECSV')))
        if data_ref_files:
            dataReferenciaAux = data_ref_files[0].split('.')[-2]
            if len(dataReferenciaAux) == len('D30610') and dataReferenciaAux.startswith('D'):
                dataReferencia = f"{dataReferenciaAux[4:6]}/{dataReferenciaAux[2:4]}/202{dataReferenciaAux[1]}"
                qtde_cnpjs = engine.execute('select count(*) as contagem from estabelecimento;').fetchone()[0]
                engine.execute(f"INSERT INTO _referencia (referencia, valor) VALUES ('CNPJ', '{dataReferencia}')")
                engine.execute(f"INSERT INTO _referencia (referencia, valor) VALUES ('cnpj_qtde', '{qtde_cnpjs}')")
    except Exception as e:
        print(f"AVISO: Não foi possível extrair a data de referência dos arquivos. {e}")


    print('-' * 20)
    print(f'Arquivo {cam_db} criado/atualizado com sucesso.')
    print('Qtde de empresas (matrizes):', engine.execute('SELECT COUNT(*) FROM empresas').fetchone()[0])
    print('Qtde de estabelecimentos (matrizes e filiais):', engine.execute('SELECT COUNT(*) FROM estabelecimento').fetchone()[0])
    print('Qtde de sócios:', engine.execute('SELECT COUNT(*) FROM socios').fetchone()[0])

    engine.commit()
    engine.close()
    print(f'FIM!!! {time.asctime()}')

if __name__ == '__main__':
    criar_cnpj_db(force_delete=True)
    input('Pressione Enter para sair.')
