# -*- coding: utf-8 -*-
"""
Script mestre para criar todas as bases de dados da RedeCNPJ.

Este script orquestra a execução de todos os passos necessários para baixar os dados
da Receita Federal e construir os bancos de dados SQLite utilizados pela aplicação.
"""

import argparse
import time
import os
import sys
import subprocess
# Garante que o diretório de trabalho seja o do script, para que os imports e caminhos relativos funcionem.
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

def verificar_e_instalar_dependencias():
    """Garante que as dependências do requirements.txt estejam instaladas."""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if not os.path.exists(requirements_path):
        print(f"AVISO: 'requirements.txt' não encontrado. Pulando instalação de dependências.")
        return

    print(f"Garantindo que as dependências de '{requirements_path}' estejam instaladas...")
    try:
        # A forma mais robusta é simplesmente executar o pip install.
        # Ele é idempotente e apenas confirmará se as dependências já estiverem satisfeitas.
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
        print("Dependências verificadas/instaladas com sucesso.")
    except subprocess.CalledProcessError:
        print("\nERRO: Falha ao instalar dependências. Verifique sua instalação do pip e a conexão com a internet.")
        sys.exit(1)

# Importa as funções dos scripts refatorados
try:
    import dados_cnpj_baixa
    import dados_cnpj_para_sqlite
except ImportError:
    print("ERRO: Verifique se os scripts 'dados_cnpj_baixa.py' e 'dados_cnpj_para_sqlite.py' estão na mesma pasta.")
    sys.exit(1)

# Nomes dos scripts que serão executados como subprocessos
SCRIPT_REDE_DB = 'rede_cria_tabela_rede.db.py'
SCRIPT_LINKS_ETE = 'rede_cria_tabela_cnpj_links_ete.py'

# Caminhos dos arquivos de banco de dados que podem ser recriados
DB_CNPJ = 'dados-publicos/cnpj.db'
DB_REDE = 'dados-publicos/rede.db'
DB_REDE_SEARCH = 'dados-publicos/rede_search.db'
DB_LINKS_ETE = 'dados-publicos/cnpj_links_ete.db'

def run_script_as_subprocess(script_name, force_delete):
    """
    Executa um script Python como um subprocesso.
    Os prompts de confirmação do script original serão exibidos.
    """
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        print(f"ERRO: Script '{script_name}' não encontrado.")
        return

    # A lógica de apagar os arquivos de DB é tratada aqui, antes de chamar o script.
    # Isso simplifica a lógica, embora os scripts ainda tenham suas próprias checagens.
    if force_delete:
        if script_name == SCRIPT_REDE_DB:
            if os.path.exists(DB_REDE): os.remove(DB_REDE)
            if os.path.exists(DB_REDE_SEARCH): os.remove(DB_REDE_SEARCH)
        elif script_name == SCRIPT_LINKS_ETE:
            if os.path.exists(DB_LINKS_ETE): os.remove(DB_LINKS_ETE)

    print("-" * 60)
    print(f"{time.asctime()}: Executando o script '{script_name}' como subprocesso.")
    print("AVISO: Este script pode solicitar confirmação no console.")
    print("-" * 60)

    # Usamos `sys.executable` para garantir que estamos usando o mesmo interpretador Python.
    # `text=True` para ver o output em tempo real, `input` para passar os 'yes'
    try:
        # A melhor forma de lidar com os prompts é deixar o usuário interagir.
        # Tentar automatizar com `input` pode ser frágil se o texto do prompt mudar.
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nERRO ao executar o script '{script_name}'. Código de saída: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\nOperação interrompida pelo usuário durante a execução de '{script_name}'.")
        sys.exit(1)


def main():
    verificar_e_instalar_dependencias()

    parser = argparse.ArgumentParser(description="Script mestre para criar as bases de dados da RedeCNPJ.")
    parser.add_argument(
        '--force-delete',
        action='store_true',
        help='Força a exclusão de arquivos e bancos de dados existentes antes de iniciar.'
    )
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Pula a etapa de download dos arquivos ZIP da Receita Federal.'
    )
    parser.add_argument(
        '--skip-links-ete',
        action='store_true',
        help='Pula a criação da base de dados opcional de links (cnpj_links_ete.db).'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Iniciando processo de criação de todas as bases de dados da RedeCNPJ.")
    print(f"Opções: force-delete={args.force_delete}, skip-download={args.skip_download}, skip-links-ete={args.skip_links_ete}")
    print("=" * 60)

    # Etapa 1: Baixar arquivos da Receita Federal
    if not args.skip_download:
        dados_cnpj_baixa.baixar_arquivos(force_delete=args.force_delete)
    else:
        print("Etapa 1: Download de arquivos pulada conforme solicitado.")

    # Etapa 2: Criar o banco de dados principal (cnpj.db)
    dados_cnpj_para_sqlite.criar_cnpj_db(force_delete=args.force_delete)

    # Etapa 3: Criar o banco de dados de rede (rede.db e rede_search.db)
    # Este script não foi refatorado para ser importável, então o executamos como subprocesso.
    run_script_as_subprocess(SCRIPT_REDE_DB, args.force_delete)

    # Etapa 4: Criar o banco de dados de links ETE (opcional)
    if not args.skip_links_ete:
        # Este script também será executado como subprocesso.
        run_script_as_subprocess(SCRIPT_LINKS_ETE, args.force_delete)
    else:
        print("\nEtapa 4: Criação da base de links (ETE) pulada conforme solicitado.")

    print("\n" + "=" * 60)
    print(f"{time.asctime()}: Processo de criação de bases concluído com sucesso!")
    print("=" * 60)

if __name__ == '__main__':
    main()
