# -*- coding: utf-8 -*-
"""
Created on Sun Jan 10 09:17:19 2021
@author: github rictom/rede-cnpj
"""
import configparser, argparse, os, sys

config = configparser.ConfigParser()
par = None # Will hold the parsed arguments after initialization
referenciaBD = '' # Initialize as empty string

def runParser():
    parser = argparse.ArgumentParser(description='descrição', epilog='rictom')
    # Add arguments, ensuring defaults are sourced from the global config object
    parser.add_argument('-i', '--inicial', action='store', dest='cpfcnpjInicial', default='', type=str, help='1 ou mais cnpj separados por ponto e vírgula; Nome ou Razao Social Completa')
    parser.add_argument('-c', '--camada', action='store', dest='camadaInicial', type=int, default=1, help='camada')
    parser.add_argument('-k', '--conf_file', action='store', default='rede.ini',help="defina arquivo de configuração", metavar="FILE")
    parser.add_argument('-j', '--json', action='store', dest='idArquivoServidor', default='', type=str, help='nome json no servidor')
    parser.add_argument('-a', '--lista', action='store', dest='arquivoEntrada', default='',help="inserir itens de arquivo em gráfico", metavar="FILE")
    parser.add_argument('-e', '--encoding', action='store', dest='encodingArquivo', default='utf8',help="codificação do arquivo", metavar="FILE")
    parser.add_argument('-p', '--pasta', action='store', dest='pasta_arquivos', default=config.get('BASE', 'pasta_arquivos', fallback='arquivos'), type=str, help='pasta de arquivos do usuário do projeto')
    parser.add_argument('-f', '--porta_flask', action='store', dest='porta_flask', type=int, default=config.getint('BASE', 'porta_flask', fallback=5000), help='porta da aplicação')
    parser.add_argument('-t', '--texto-embaixo', action='store_true', dest='btextoEmbaixoIcone', default=True,  help='texto em baixo do ícone' )
    parser.add_argument('-T', '--texto-ao-lado', action='store_false', dest='btextoEmbaixoIcone',  help='texto ao lado do ícone' )
    parser.add_argument('-m', '--n-mensagem', action='store_false', dest='bExibeMensagemInicial', default=config.getboolean('INICIO', 'exibe_mensagem_advertencia', fallback=True),  help='não exibe mensagem inicial' )
    parser.add_argument('-M', '--mensagem',action='store_true', dest='bExibeMensagemInicial', default=config.getboolean('INICIO', 'exibe_mensagem_advertencia', fallback=True), help='exibe mensagem inicial')
    parser.add_argument('-y', '--n-menuinserir', action='store_false', dest='bMenuInserirInicial', default=config.getboolean('INICIO', 'exibe_menu_inserir', fallback=True), help='não exibe menu para inserir no inicio' )
    parser.add_argument('-Y', '--menuinserir', action='store_true', dest='bMenuInserirInicial', default=config.getboolean('INICIO', 'exibe_menu_inserir', fallback=True), help='exibe menu para inserir no inicio' )
    parser.add_argument('-d', '--download', action='store_true', dest='bArquivosDownload', default=config.getboolean('ETC', 'arquivos_download', fallback=False), help='permitir download da pasta arquivos' )
    parser.add_argument('-D', '--n-download', action='store_false', dest='bArquivosDownload', default=config.getboolean('ETC', 'arquivos_download', fallback=False), help='permitir download da pasta arquivos' )
    parser.add_argument('-n', '--sheet-name', action='store', dest='excel_sheet_name',default=0, help='nome da aba do excel')
    parser.add_argument('-s', '--separador', action='store', dest='separador', default='\t', help='separador arquivo csv')
    parser.add_argument('-l', '--tipo_lista', action='store', dest='tipo_lista',default='', help='define tipo de entrada, _+  _* _>')

    known_args, _ = parser.parse_known_args()
    return known_args

def load_config_and_parse_args():
    global par, config, referenciaBD

    # Create a new parser to find the config file path from command line
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument('-k', '--conf_file', action='store', default='rede.ini', help="Define arquivo de configuração", metavar="FILE")
    args, _ = conf_parser.parse_known_args()
    conf_file_path = args.conf_file

    # If the default name is used, search for it robustly
    if conf_file_path == 'rede.ini':
        path1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rede.ini') # Same dir as this script
        path2 = 'rede.ini' # Current working dir
        if os.path.exists(path1):
            conf_file_path = path1
        elif os.path.exists(path2):
            conf_file_path = path2
    
    # Load the configuration from the found path
    if os.path.exists(conf_file_path):
        config = configparser.ConfigParser() # Reset config
        config.read(conf_file_path, encoding='utf8')
    else:
        print(f'O arquivo de configuracao {conf_file_path} não foi localizado. Parando...')
        sys.exit(1)

    # Re-parse all arguments with defaults from the loaded config
    par = runParser()

    if par.arquivoEntrada and not os.path.exists(par.arquivoEntrada):
        print('O arquivo ' + par.arquivoEntrada + ' não existe. Parando...')
        sys.exit(1)

    referenciaBD = config.get('BASE', 'referencia_bd', fallback='')
    return par

# This block will only run when the script is executed directly
if __name__ == '__main__':
    load_config_and_parse_args()
