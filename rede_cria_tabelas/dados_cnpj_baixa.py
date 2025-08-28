# -*- coding: utf-8 -*-
"""
lista relação de arquivos na página de dados públicos da receita federal
e faz o download
"""
from bs4 import BeautifulSoup
import requests, wget, os, sys, time, glob, parfive

# url_dados_abertos = 'https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/' # Deprecated
# url_dados_abertos = 'http://200.152.38.155/CNPJ/dados_abertos_cnpj/' # Deprecated
# url_dados_abertos = 'https://arquivos.receitafederal.gov.br/cnpj/dados_abertos_cnpj/' # Deprecated
url_dados_abertos = 'https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/'

pasta_zip = r"dados-publicos-zip" #local dos arquivos zipados da Receita
pasta_cnpj = 'dados-publicos'

def requisitos(force_delete):
    """Verifica e prepara as pastas de destino. Apaga arquivos existentes se `force_delete` for True."""
    if not os.path.isdir(pasta_cnpj):
        os.mkdir(pasta_cnpj)
    if not os.path.isdir(pasta_zip):
        os.mkdir(pasta_zip)

    arquivos_existentes = list(glob.glob(os.path.join(pasta_cnpj, '*.*'))) + list(glob.glob(os.path.join(pasta_zip, '*.*')))
    if arquivos_existentes:
        if force_delete:
            print(f'A opção --force-delete está ativa. Apagando {len(arquivos_existentes)} arquivos existentes...')
            for arq in arquivos_existentes:
                print('Apagando arquivo ' + arq)
                os.remove(arq)
        else:
            print('As pastas de destino não estão vazias. Use --force-delete para apagar os arquivos existentes.')
            print('Arquivos encontrados: ' + ', '.join(arquivos_existentes))
            sys.exit(1)

def baixar_arquivos(force_delete=False, skip_download=False):
    """Função principal para baixar os arquivos de dados abertos da Receita Federal."""
    requisitos(force_delete)

    print(time.asctime(), 'Início do download dos arquivos da Receita Federal.')

    print(f'Acessando {url_dados_abertos} para obter a lista de arquivos...')
    try:
        soup_pagina_dados_abertos = BeautifulSoup(requests.get(url_dados_abertos).text, features="lxml")
        ultima_referencia = sorted([link.get('href') for link in soup_pagina_dados_abertos.find_all('a') if link.get('href').startswith('20')])[-1]
    except Exception as e:
        print(f'Erro ao acessar a página de dados abertos: {e}')
        sys.exit(1)

    url = url_dados_abertos + ultima_referencia

    try:
        soup = BeautifulSoup(requests.get(url).text, features="lxml")
    except Exception as e:
        print(f"Erro ao acessar a URL da última referência ({url}): {e}")
        sys.exit(1)

    lista_urls = []
    print('Relação de Arquivos em ' + url)
    for link in soup.find_all('a'):
        if str(link.get('href')).endswith('.zip'):
            cam = link.get('href')
            if not cam.startswith('http'):
                print(url + cam)
                lista_urls.append(url + cam)
            else:
                print(cam)
                lista_urls.append(cam)

    if skip_download:
        print("\n--skip-download ativado. Pulando o download dos arquivos.")
        return

    print(f'\nEncontrados {len(lista_urls)} arquivos para download.')

    print(time.asctime(), 'Início do Download dos arquivos...')

    # Baixa usando parfive, para download em paralelo
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36", "Accept": "*/*"}
    downloader = parfive.Downloader(max_conn=5, max_splits=1, config=parfive.SessionConfig(headers=headers))
    for file_url in lista_urls:
        downloader.enqueue_file(file_url, path=pasta_zip, filename=os.path.split(file_url)[1])

    results = downloader.download()

    print(f'\n{time.asctime()} Finalizou o download!')
    print(f"Total de arquivos baixados com sucesso: {len(results.completed)}")
    if results.failed:
        print(f"ERRO: {len(results.failed)} arquivos falharam ao baixar.")
        for err in results.errors:
            print(err.exception)

if __name__ == '__main__':
    print("Este script baixa os arquivos de dados abertos da Receita Federal.")
    resp_delete = input(f'AVISO: Se as pastas {pasta_zip} e {pasta_cnpj} não estiverem vazias, os arquivos serão apagados. Deseja continuar? (y/n)? ')
    if resp_delete.lower() not in ['y', 's']:
        sys.exit("Operação cancelada pelo usuário.")

    resp_download = input(f'Deseja baixar os arquivos para a pasta {pasta_zip} (y/n)? ')
    if resp_download.lower() not in ['y', 's']:
        sys.exit("Operação cancelada pelo usuário.")

    baixar_arquivos(force_delete=True)

    print(f'\n\n{time.asctime()} Finalizou {sys.argv[0]}!!!')
    input('Pressione Enter para sair.')
