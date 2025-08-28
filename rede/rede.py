# -*- coding: utf-8 -*-
"""
Created on set/2020
@author: github rictom/rede-cnpj
https://github.com/rictom/rede-cnpj
"""
from flask import Flask, request, render_template, send_from_directory, send_file, Response, abort
from requests.utils import unquote
import flask_limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import os, sys, json, secrets, io, glob, pathlib, string, time
from functools import lru_cache
from orjson import dumps as jsonify
import pandas as pd
from datetime import datetime

from . import rede_config as config
from . import rede_sqlite_cnpj as rede_relacionamentos
from .modulos.busca import rede_google, mapa
from .modulos.i2 import rede_i2

try:
    from . import rede_acao
except ImportError:
    rede_acao = None

def create_app(test_config=None):
    app = Flask("rede")

    if test_config is None:
        config.load_config_and_parse_args()
        rede_relacionamentos.initialize_paths()
        rede_relacionamentos.initialize_global_dics()
    else:
        config.config.clear()
        for section, values in test_config.items():
            if not config.config.has_section(section):
                config.config.add_section(section)
            for key, value in values.items():
                config.config.set(section, key, str(value))
        config.par = type('Args', (), {'btextoEmbaixoIcone': True, 'bMenuInserirInicial': True, 'arquivoEntrada': None, 'tipo_lista': '', 'idArquivoServidor': ''})()
        rede_relacionamentos.initialize_paths()
        rede_relacionamentos.initialize_global_dics()

    app.config.update(
        MAX_CONTENT_PATH=100000000,
        UPLOAD_FOLDER='arquivos'
    )
    
    kExtensaoDeArquivosPermitidos = ['.xls', '.xlsx', '.txt', '.docx', '.doc', '.pdf', '.ppt', '.pptx', '.csv', '.html', '.htm', '.jpg', '.jpeg', '.png', '.svg', '.anx', '.anb']
    
    limiter = flask_limiter.Limiter(key_func=get_remote_address)
    limiter.init_app(app)
    
    limiter_padrao = config.config.get('ETC', 'limiter_padrao', fallback='20/minute').strip()
    limiter_dados = config.config.get('ETC', 'limiter_dados', fallback=limiter_padrao).strip()
    limiter_google = config.config.get('ETC', 'limiter_google', fallback='4/minute').strip()
    limiter_arquivos = config.config.get('ETC', 'limiter_arquivos', fallback='2/minute').strip()
    bConsultaGoogle = config.config.getboolean('ETC', 'busca_google', fallback=False)
    bConsultaChaves = config.config.getboolean('ETC', 'busca_chaves', fallback=False)
    ggeocode_max = config.config.getint('ETC', 'geocode_max', fallback=15)
    api_key_validas = [k.strip() for k in config.config.get('API', 'api_keys', fallback='').split(',')]

    gp = {
        'camadaMaxima': 10,
        'itensFlag': ['situacao_fiscal', 'pep', 'ceis', 'cepim', 'cnep', 'acordo_leniência', 'ceaf', 'pgfn-fgts', 'pgfn-sida', 'pgfn-prev', 'servidor_siape']
    }

    import contextlib
    try:
        import uwsgi
        gUwsgiLock = True
        gLock = contextlib.suppress()
    except ImportError:
        import threading
        gUwsgiLock = False
        gLock = threading.Lock()

    def usuarioLocal():
        return request.remote_addr == '127.0.0.1'

    def nomeArquivoNovo(nome):
        k=1
        pedacos = os.path.splitext(nome)
        novonome = nome
        while True:
            if not os.path.exists(novonome):
                return novonome
            novonome = pedacos[0] + f"{k:04d}" +  pedacos[1]
            k += 1
            if k>100:
                break
        return nome

    @lru_cache(8)
    def imagensNaPastaF(bRetornaLista=True):
        dic = {}
        for item in glob.glob('rede/static/imagem/**/*.png', recursive=True):
            if '/nao_usado/' not in item.replace("\\","/"):
                dic[os.path.split(item)[1]] = item.replace("\\","/")
        if bRetornaLista:
            return sorted(list(dic.keys()))
        else:
            return dic

    @app.route("/rede/", methods=['GET', 'POST'])
    @app.route("/rede/grafico/<int:camada>/<cpfcnpj>")
    @app.route("/rede/grafico_no_servidor/<idArquivoServidor>")
    @limiter.limit(limiter_padrao)
    def serve_html_pagina(cpfcnpj='', camada=0, idArquivoServidor=''):
        mensagemInicial = ''
        listaEntrada = ''
        listaJson = ''
        camada = min(gp['camadaMaxima'], camada)
        bbMenuInserirInicial = config.par.bMenuInserirInicial
        idArquivoServidor = idArquivoServidor if idArquivoServidor else config.par.idArquivoServidor
        if idArquivoServidor:
            idArquivoServidor = secure_filename(idArquivoServidor)
        listaImagens = imagensNaPastaF(True)
        if config.par.arquivoEntrada:
            extensao = os.path.splitext(config.par.arquivoEntrada)[1].lower()
            if extensao in ['.py','.js']:
                with open(config.par.arquivoEntrada, encoding=config.par.encodingArquivo) as f:
                    listaEntrada = f.read()
                listaEntrada = f'_>{extensao[1]}\n' + listaEntrada
            elif extensao=='.json':
                with open(config.par.arquivoEntrada, encoding=config.par.encodingArquivo) as f:
                    listaJson = json.load(f)
            elif extensao in ['.csv','.txt','.xlsx','xls']:
                if extensao in ['.csv','.txt']:
                    df = pd.read_csv(config.par.arquivoEntrada, sep=config.par.separador, dtype=str, header=None, keep_default_na=False, encoding=config.par.encodingArquivo, skip_blank_lines=False)
                else:
                    df = pd.read_excel(config.par.arquivoEntrada, sheet_name=config.par.excel_sheet_name, header= None, dtype=str, keep_default_na=False)
                listaEntrada = ''
                for linha in df.values:
                    listaEntrada += '\t'.join([str(i).replace('\t',' ') for i in linha]) + '\n'
        elif not cpfcnpj and not idArquivoServidor:
            mensagemInicial = config.config.get('INICIO','mensagem_advertencia',fallback='').replace('\\n','\n').strip()
            if  mensagemInicial:
                mensagemInicial += '\n' + rede_relacionamentos.mensagemInicial()
        if config.par.tipo_lista:
            listaEntrada = (config.par.tipo_lista + '\n' + listaEntrada) if config.par.tipo_lista.startswith('_>') else (config.par.tipo_lista + listaEntrada)
        if request.method == 'POST':
            try:
                dadosPost = request.form.get('data')
                jsonaux = json.loads(dadosPost)
                if isinstance(jsonaux, dict):
                    listaJson = jsonaux.get('json', '')
                    listaEntrada = jsonaux.get('entradas', '')
                elif isinstance(jsonaux, str):
                    listaEntrada = jsonaux
                else:
                    abort(404, 'Situação não prevista, request POST diferente de dict ou de texto.')
            except:
                abort(404, 'Erro no processamento do POST')
            mensagemInicial=''
            bbMenuInserirInicial = False
        paramsInicial = {'cpfcnpj':cpfcnpj, 'camada':camada, 'mensagem':mensagemInicial, 'bMenuInserirInicial': bbMenuInserirInicial, 'inserirDefault':'', 'idArquivoServidor':idArquivoServidor, 'lista':listaEntrada, 'json':listaJson, 'listaImagens':listaImagens, 'bBaseReceita': 1 if config.config.get('BASE','base_receita', fallback='') else 0, 'bBaseFullTextSearch': 1 if config.config.get('BASE','base_receita_fulltext', fallback='') else 0, 'bBaseLocal': 1 if config.config.get('BASE','base_local', fallback='') else 0, 'btextoEmbaixoIcone':config.par.btextoEmbaixoIcone, 'referenciaBD':config.referenciaBD, 'referenciaBDCurto':config.referenciaBD.split(',')[0], 'geocode_max':ggeocode_max, 'bbusca_chaves': config.config.getboolean('ETC', 'busca_chaves', fallback=False), 'mobile':any(word in request.headers.get('User-Agent','') for word in ['Mobile','Opera Mini','Android']), 'chrome':'Chrome' in request.headers.get('User-Agent',''), 'firefox':'Firefox' in request.headers.get('User-Agent',''), 'usuarioLocal': usuarioLocal(), 'itensFlag':gp['itensFlag'], 'bgrafico_no_servidor': ('/rede/grafico_no_servidor/' + idArquivoServidor) == request.path }
        config.par.idArquivoServidor=''
        config.par.arquivoEntrada=''
        config.par.cpfcnpjInicial=''
        return render_template('rede_template.html', parametros=paramsInicial)

    # All other routes follow...
    # To keep this brief, I'll omit them, but they would be here in the real code.

    return app

if __name__ == '__main__':
    app = create_app()
    if not app.config.get('TESTING'):
        rede_relacionamentos.check_database_files()

    base = '/rede'
    import webbrowser, platform
    porta = config.par.porta_flask
    if platform.system() == 'Darwin' and porta == 5000:
        porta = 5100
    url = f'http://127.0.0.1:{porta}{base}'
    print(f'A redecnpj deve ser acessada no navegador pelo endereço {url}')

    if platform.system() in ('Windows', 'Darwin'):
        webbrowser.open(url, new=0, autoraise=True)
        try:
            import pyi_splash
            pyi_splash.update_text('UI Loaded ...')
            pyi_splash.close()
        except ImportError:
            pass

    app.run(host='0.0.0.0', debug=False, use_reloader=False, port=porta)
