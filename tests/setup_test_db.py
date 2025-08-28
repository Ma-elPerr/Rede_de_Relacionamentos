import sqlite3
import os

def setup_test_database():
    # Base path for test databases
    base_path = os.path.dirname(__file__)

    # Main test database (simulating cnpj.db)
    db_path = os.path.join(base_path, 'test_cnpj.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # External data test database (simulating dados_externos.db)
    db_externos_path = os.path.join(base_path, 'dados_externos.db')
    if os.path.exists(db_externos_path):
        os.remove(db_externos_path)
    conn_ext = sqlite3.connect(db_externos_path)
    cur_ext = conn_ext.cursor()

    # --- Create Schema ---
    # Tables for test_cnpj.db
    cur.execute('''CREATE TABLE estabelecimento (cnpj TEXT, cnpj_basico TEXT, matriz_filial TEXT, nome_fantasia TEXT, situacao_cadastral TEXT, data_situacao_cadastral TEXT, motivo_situacao_cadastral TEXT, nome_cidade_exterior TEXT, pais TEXT, data_inicio_atividades TEXT, cnae_fiscal TEXT, cnae_fiscal_secundaria TEXT, tipo_logradouro TEXT, logradouro TEXT, numero TEXT, complemento TEXT, bairro TEXT, cep TEXT, uf TEXT, municipio TEXT)''')
    cur.execute('''CREATE TABLE empresas (cnpj_basico TEXT, razao_social TEXT, natureza_juridica TEXT, capital_social REAL, porte_empresa TEXT)''')
    cur.execute('''CREATE TABLE municipio (codigo TEXT, descricao TEXT)''')
    cur.execute('''CREATE TABLE pais (codigo TEXT, descricao TEXT)''')
    cur.execute('''CREATE TABLE simples (cnpj_basico TEXT, opcao_mei TEXT)''')
    cur.execute('''CREATE TABLE cnae (codigo TEXT, descricao TEXT)''')
    cur.execute('''CREATE TABLE qualificacao_socio (codigo TEXT, descricao TEXT)''')
    cur.execute('''CREATE TABLE motivo (codigo TEXT, descricao TEXT)''')
    cur.execute('''CREATE TABLE natureza_juridica (codigo TEXT, descricao TEXT)''')
    cur.execute('''CREATE TABLE _referencia (referencia TEXT, valor TEXT)''')

    # Tables for test_dados_externos.db
    cur_ext.execute('''CREATE TABLE cnep (cnpj TEXT, sancao TEXT, orgao TEXT, data_inicio TEXT, data_final TEXT)''')
    cur_ext.execute('''CREATE TABLE ceis (cnpj TEXT, sancao TEXT, orgao TEXT, data_inicio TEXT, data_final TEXT)''')
    cur_ext.execute('''CREATE TABLE correcionais (cpf TEXT, nome TEXT, sancao TEXT, orgao TEXT, data_inicio TEXT, data_final TEXT)''')
    cur.execute('''CREATE TABLE socios (cnpj TEXT, cnpj_cpf_socio TEXT, nome_socio TEXT, qualificacao_socio TEXT, data_entrada_sociedade TEXT, pais TEXT, representante_legal TEXT, nome_representante TEXT, qualificacao_representante_legal TEXT, faixa_etaria TEXT)''')


    # --- Insert Sample Data ---
    # CNPJ 1: No sanctions, but has a sanctioned partner
    cur.execute("INSERT INTO empresas VALUES ('00000000', 'NORMAL INC', '2062', 1000, '05')")
    cur.execute("INSERT INTO estabelecimento VALUES ('00000000000001', '00000000', '1', 'FANTASIA NORMAL', '02', '20000101', '0', '', '105', '20000101', '1234567', '', 'RUA', 'A', '1', '', 'B', '111', 'SP', '3550308')")

    # CNPJ 2: CNEP sanction
    cur.execute("INSERT INTO empresas VALUES ('11111111', 'CNEP CORP', '2062', 2000, '05')")
    cur.execute("INSERT INTO estabelecimento VALUES ('11111111000111', '11111111', '1', 'FANTASIA CNEP', '02', '20010101', '0', '', '105', '20010101', '1234567', '', 'RUA', 'B', '2', '', 'C', '222', 'RJ', '3304557')")
    cur_ext.execute("INSERT INTO cnep VALUES ('11111111000111', 'Suspensão', 'Orgao CNEP', '20230101', '20240101')")

    # CNPJ 3: CEIS sanction
    cur.execute("INSERT INTO empresas VALUES ('22222222', 'CEIS SA', '2062', 3000, '05')")
    cur.execute("INSERT INTO estabelecimento VALUES ('22222222000122', '22222222', '1', 'FANTASIA CEIS', '02', '20020101', '0', '', '105', '20020101', '1234567', '', 'RUA', 'C', '3', '', 'D', '333', 'MG', '3106200')")
    cur_ext.execute("INSERT INTO ceis VALUES ('22222222000122', 'Multa', 'Orgao CEIS', '20230201', '20240201')")

    # Socio and Correcional Data
    cur.execute("INSERT INTO socios VALUES ('00000000000001', '11122233344', 'SOCIO SANCIONADO', '49', '20000101', '', '', '', '', '5')")
    cur_ext.execute("INSERT INTO correcionais VALUES ('11122233344', 'SOCIO SANCIONADO', 'DEMISSAO', 'Orgao Correcional', '20230301', '')")


    # Common data
    cur.execute("INSERT INTO municipio VALUES ('3550308', 'SAO PAULO')")
    cur.execute("INSERT INTO municipio VALUES ('3304557', 'RIO DE JANEIRO')")
    cur.execute("INSERT INTO municipio VALUES ('3106200', 'BELO HORIZONTE')")
    cur.execute("INSERT INTO pais VALUES ('105', 'BRASIL')")
    cur.execute("INSERT INTO cnae VALUES ('1234567', 'CNAE TESTE')")
    cur.execute("INSERT INTO natureza_juridica VALUES ('2062', 'SOCIEDADE EMPRESARIA LIMITADA')")
    cur.execute("INSERT INTO _referencia VALUES ('cnpj_qtde', '100')")
    cur.execute("INSERT INTO _referencia VALUES ('CNPJ', '2024-01-01')")


    # Commit and close
    conn.commit()
    conn.close()
    conn_ext.commit()
    conn_ext.close()

if __name__ == '__main__':
    setup_test_database()
    print("Test databases 'test_cnpj.db' and 'dados_externos.db' created successfully.")
