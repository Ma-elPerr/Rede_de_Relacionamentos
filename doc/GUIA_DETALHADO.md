# Guia Detalhado da Aplicação RedeCNPJ

## 1. Introdução

A aplicação RedeCNPJ é uma ferramenta de OSINT (Open Source Intelligence) projetada para visualizar graficamente os relacionamentos entre empresas e seus sócios, utilizando os dados públicos do Cadastro Nacional da Pessoa Jurídica (CNPJ) disponibilizados pela Receita Federal do Brasil.

O objetivo principal é oferecer uma interface intuitiva que permita a analistas, jornalistas e pesquisadores explorar e entender as complexas redes de conexões societárias de forma visual e interativa. A aplicação transforma as tabelas de dados brutos em um grafo dinâmico, onde cada empresa e sócio é um "nó" e a relação entre eles é uma "aresta" ou "ligação".

## 2. Arquitetura Geral

A aplicação é construída sobre uma arquitetura cliente-servidor clássica, composta por três componentes principais que trabalham em conjunto:

1.  **Frontend (Cliente):** É a interface com a qual o usuário interage diretamente no navegador. Consiste em uma única página HTML (`rede_template.html`) que utiliza intensivamente JavaScript para renderizar o grafo, manipular a interface e se comunicar com o backend.
    *   **Tecnologias:** HTML5, CSS3, JavaScript.
    *   **Bibliotecas Principais:**
        *   `VivaGraphJS`: Biblioteca para renderização e manipulação de grafos de larga escala.
        *   `alertify.js`: Utilizada para criar diálogos, pop-ups e notificações.
        *   Código JavaScript customizado para gerenciar a lógica da interface, eventos do usuário e comunicação com a API.

2.  **Backend (Servidor):** É o cérebro da aplicação, responsável por processar as solicitações do frontend, consultar o banco de dados e retornar os dados formatados. Foi desenvolvido em Python utilizando o microframework Flask.
    *   **Tecnologias:** Python, Flask.
    *   **Arquivo Principal:** `rede/rede.py`.
    *   **Funções:** Define as rotas da API (endpoints), gerencia a lógica de negócio, controla o acesso e serve a página principal.

3.  **Banco de Dados (Persistência):** É onde todos os dados de CNPJs, sócios e relacionamentos são armazenados. A aplicação utiliza bancos de dados SQLite, que são arquivos leves e portáteis.
    *   **Tecnologia:** SQLite.
    *   **Bancos Principais:**
        *   `cnpj.db`: Contém os dados brutos da Receita Federal (empresas, estabelecimentos, sócios, etc.).
        *   `rede.db`: Uma base pré-processada contendo as ligações diretas entre as entidades (nós), otimizada para a construção do grafo.
        *   `rede_search.db`: Contém um índice de busca em texto completo para permitir pesquisas rápidas por nome de empresa ou sócio.
    *   **Módulo de Acesso:** A interação com o banco de dados é centralizada no módulo `rede/rede_sqlite_cnpj.py`.
*   **Bancos de Dados Externos:** A arquitetura suporta a integração de bancos de dados adicionais (ex: `dados_externos.db`) para enriquecer os dados principais com informações de outras fontes. Atualmente, são utilizadas fontes da Controladoria-Geral da União (CGU):
    *   **CNEP e CEIS:** Listas de sanções aplicadas a **empresas**.
    *   **Dados Correcionais:** Lista de sanções aplicadas a **pessoas físicas**.

O fluxo de comunicação funciona da seguinte maneira:
- O usuário acessa a URL principal.
- O **Backend (Flask)** serve a página `rede_template.html` para o navegador.
- O **Frontend (JavaScript)**, ao carregar, pode fazer uma requisição inicial à API do backend para buscar os dados de um CNPJ específico ou carregar um grafo salvo.
- Quando o usuário interage com o grafo (ex: dando um duplo-clique em um nó), o **Frontend** envia uma requisição `fetch` para uma rota específica da API no **Backend**.
- O **Backend** recebe a requisição, utiliza o módulo `rede_sqlite_cnpj.py` para consultar o **Banco de Dados** SQLite. Ele pode anexar (`ATTACH`) o banco `dados_externos.db` e fazer um `LEFT JOIN` para verificar se uma empresa (PJ) ou pessoa (PF) consta nas tabelas de sanções (`cnep`, `ceis`, `correcionais`). O backend então processa os resultados e os retorna para o **Frontend** em formato JSON.
- O **Frontend** recebe o JSON e utiliza o `VivaGraphJS` para adicionar os novos nós e ligações ao grafo. Se um nó vier com um marcador de sanção, o frontend aplica uma estilização diferente:
    - **Borda Vermelha:** Para empresas (`PJ_...`) com sanções nos cadastros CNEP ou CEIS.
    - **Borda Amarela:** Para pessoas físicas (`PF_...`) com sanções no cadastro de Dados Correcionais.
- Além disso, ao passar o mouse sobre um nó sancionado, o **tooltip** exibirá os detalhes da sanção correspondente.

## 3. O Backend (Servidor Flask - `rede.py`)

O arquivo `rede/rede.py` é o ponto de entrada e o controlador central do lado do servidor. Ele utiliza o microframework Flask para criar um servidor web que responde às requisições do frontend.

**Principais Responsabilidades:**

*   **Servir a Página Principal:** Quando o usuário acessa a raiz da aplicação, este script renderiza o template `rede_template.html` e o envia para o navegador.
*   **Definir a API RESTful:** Expõe uma série de endpoints (rotas) que o frontend pode chamar para obter dados ou executar ações.
*   **Gerenciar Requisições:** Processa as requisições HTTP, extrai parâmetros (como CNPJs, camadas de profundidade, etc.) e chama as funções apropriadas no módulo de banco de dados (`rede_sqlite_cnpj.py`).
*   **Formatar Respostas:** Pega os resultados do banco de dados (geralmente listas e dicionários Python) e os serializa para o formato JSON antes de enviá-los de volta ao frontend. Para otimização, utiliza a biblioteca `orjson` que é mais rápida que a biblioteca `json` padrão do Flask.
*   **Controle de Acesso e Segurança:** Implementa um limitador de requisições (`Flask-Limiter`) para prevenir abuso da API e diferencia permissões entre usuários locais (`127.0.0.1`) e remotos.

### Rotas da API (Endpoints)

Abaixo estão as rotas mais importantes definidas em `rede.py`:

#### **`@app.route("/rede/")`**
*   **Função:** `serve_html_pagina()`
*   **Método:** `GET`, `POST`
*   **Descrição:** É a rota principal que serve a página da aplicação. Ela pode receber um CNPJ inicial na URL (ex: `/rede/grafico/1/12345678901234`) ou carregar um grafo salvo do servidor (`/rede/grafico_no_servidor/...`). Ela prepara um dicionário `parametros` com todas as configurações iniciais e o passa para o template `rede_template.html` para renderização.

#### **`@app.route('/rede/grafojson/<tipo>/<int:camada>/<cpfcnpj>')`**
*   **Função:** `serve_rede_json_cnpj()`
*   **Método:** `POST`
*   **Descrição:** Este é o endpoint mais crucial para a interatividade do grafo. É chamado quando o usuário expande um nó (ex: duplo-clique).
    *   `tipo`: Define o tipo de busca, como `cnpj` para expansão normal ou `caminhos` para encontrar rotas entre nós.
    *   `camada`: Um inteiro que define quantos níveis de relacionamento devem ser buscados a partir dos nós de entrada.
    *   O corpo da requisição (`request.get_json()`) contém uma lista dos IDs (PF\_ ou PJ\_) a serem expandidos.
*   **Retorno:** Um objeto JSON contendo duas listas: `no` (os novos nós encontrados) e `ligacao` (as novas ligações). Ex: `{'no': [...], 'ligacao': [...]}`.

#### **`@app.route('/rede/dadosjson/<cpfcnpj>')`**
*   **Função:** `serve_dados_detalhes()`
*   **Método:** `POST`
*   **Descrição:** Busca e retorna todos os dados detalhados de um único CNPJ ou CPF. O frontend chama esta rota quando o usuário solicita ver os detalhes de um nó (tecla 'D').
*   **Retorno:** Um objeto JSON com todos os campos de dados daquele nó.

#### **`@app.route('/rede/consulta_cnpj/')`**
*   **Função:** `serve_dados_html()`
*   **Método:** `GET`
*   **Descrição:** Renderiza uma página HTML (`dados_cnpj.html`) formatada para exibir os dados detalhados de um ou mais CNPJs, incluindo a lista de sócios. É a rota usada quando o usuário pressiona SHIFT+D.

#### **`@app.route('/rede/dadosemarquivo/<formato>')`**
*   **Função:** `serve_dadosEmArquivo()`
*   **Método:** `POST`
*   **Descrição:** Permite exportar os dados do grafo atual para diferentes formatos de arquivo. O frontend envia os dados do grafo visível no corpo da requisição.
    *   `formato`: Pode ser `xlsx` para Excel ou `anx` para o formato i2 Chart Reader.
*   **Retorno:** Um arquivo para download no formato solicitado.

#### **`@app.route('/rede/mapa')`**
*   **Função:** `serve_mapa()`
*   **Método:** `POST`
*   **Descrição:** Recebe uma lista de nós, utiliza o módulo `mapa.py` para gerar um mapa HTML (usando Folium/Leaflet) com os endereços das empresas e retorna este mapa para ser exibido em uma nova aba.

#### **Rotas de Arquivos (`/rede/arquivos_json/...`, `/rede/arquivos_json_upload/...`)**
*   **Descrição:** Um conjunto de rotas para gerenciar o salvamento e carregamento de grafos no servidor. Permitem que o usuário salve o estado atual de sua análise em um arquivo JSON no servidor e o recarregue posteriormente através de um link.

## 4. O Coração dos Dados (Módulo de Banco de Dados - `rede_sqlite_cnpj.py`)

Este módulo é a camada de acesso e processamento de dados. Ele é o único componente que interage diretamente com os bancos de dados SQLite, abstraindo toda a complexidade das consultas SQL do resto da aplicação.

**Principais Responsabilidades:**

*   **Conexão com os Bancos de Dados:** Gerencia a conexão com os diversos arquivos `.db` (`cnpj.db`, `rede.db`, `rede_search.db`, etc.).
*   **Busca de Entidades:** Contém as funções para encontrar empresas e sócios a partir de um nome ou de um número de documento.
*   **Construção da Rede:** Implementa a lógica principal para encontrar os relacionamentos entre as entidades em múltiplos níveis (camadas).
*   **Recuperação de Dados Detalhados:** Busca todos os campos de uma empresa ou sócio quando solicitado.
*   **Formatação de Dados:** Converte os dados brutos do banco (códigos, datas no formato `aaaammdd`) em um formato legível para o usuário.

### Funções e Lógica Essencial

#### **Busca Inicial: `separaEntrada()` e `buscaPorNome()`**

Quando um usuário digita algo na caixa de busca, a função `separaEntrada()` é a primeira a ser chamada. Ela analisa o texto e determina se é:
*   Um CNPJ (completo ou radical de 8 dígitos).
*   Um CPF (completo ou o miolo de 6 dígitos).
*   Um nome.

Se for um nome, `separaEntrada()` chama a função `buscaPorNome()`. Esta, por sua vez, executa uma consulta `MATCH` no banco de dados de busca (`rede_search.db`), que possui uma tabela (`id_search`) otimizada para busca textual (Full-Text Search - FTS). Isso permite encontrar rapidamente uma empresa ou sócio mesmo que o nome não esteja completo.

#### **Construção do Grafo: `camadasRede()`**

Esta é a função mais complexa e central do módulo, responsável por construir a rede de relacionamentos.

**Fluxo de Execução:**

1.  **Criação de Tabelas Temporárias:** A função inicia criando tabelas temporárias em memória no SQLite (`tmp_ids`, `tmp_ligacao`). Isso é fundamental para a performance, pois todas as operações subsequentes são feitas nessas tabelas pequenas e rápidas, em vez de consultar as tabelas gigantes do banco principal a cada passo.
2.  **População Inicial:** A tabela `tmp_ids` é populada com o conjunto inicial de IDs (PF\_ ou PJ\_) fornecido pelo frontend.
3.  **Loop Iterativo por Camada:** A função entra em um loop que executa uma vez para cada `camada` solicitada. Em cada iteração:
    *   Ela faz um `JOIN` entre a tabela `tmp_ids` (que contém os nós da camada anterior) e a tabela `ligacao` do banco `rede.db`. A tabela `ligacao` é a chave para a performance, pois ela já contém as conexões diretas pré-calculadas (`id1`, `id2`, `descricao da ligação`).
    *   Todos os novos IDs encontrados nesse `JOIN` são adicionados à tabela `tmp_ids`.
    *   Todas as novas ligações são adicionadas à tabela `tmp_ligacao`.
    *   O processo se repete, usando os nós recém-adicionados como ponto de partida para a próxima camada.
4.  **Limites:** O loop pode ser interrompido se o número de nós exceder um limite (`kLimiteCamada`) ou se o tempo de consulta for muito longo, para evitar sobrecarga do servidor.
5.  **Finalização e Geração do JSON:** Após o loop, a função chama `camadasRede_json()`.

#### **Geração do JSON: `camadasRede_json()` e `dadosDosNosCNPJs()`**

1.  **`camadasRede_json()`:** Pega as tabelas temporárias finais (`tmp_ids` e `tmp_ligacao`) e organiza os dados.
2.  **`dadosDosNosCNPJs()`:** Para cada ID de CNPJ (`PJ_...`) encontrado, esta função faz uma consulta ao banco principal `cnpj.db` para buscar os dados completos da empresa (razão social, nome fantasia, endereço, etc.).
3.  **`ajustaLabelIcone()`:** Determina qual ícone deve ser usado para cada tipo de nó (empresa pública, privada, pessoa física, etc.) com base em seus dados, como o código de natureza jurídica.
4.  **Montagem Final:** A função consolida todas as informações e monta o objeto JSON final `{'no': [...], 'ligacao': [...]}` que será enviado ao frontend.

Este design, que utiliza uma tabela de ligações pré-processada (`rede.db`) e tabelas temporárias em memória, é o que permite que a aplicação explore redes complexas de forma relativamente rápida, mesmo operando sobre um volume de dados muito grande.

## 5. A Interface do Usuário (Frontend - `rede_template.html`)

Este arquivo é o único ponto de entrada para o cliente. Ele contém a estrutura HTML, os estilos CSS e, mais importante, todo o código JavaScript que gerencia a lógica da interface do usuário, a visualização do grafo e a comunicação com o backend.

**Principais Responsabilidades:**

*   **Estrutura da Página:** Define os elementos HTML, como a área principal do grafo (`<div id="principal">`), os botões de ação e o menu de contexto.
*   **Inicialização do Grafo:** Contém o código que inicializa a biblioteca `VivaGraphJS`, configura o motor de layout de física (`forceDirected`) e o renderizador SVG.
*   **Renderização de Nós e Ligações:** Define as funções `graphics.node()` e `graphics.link()` que determinam a aparência de cada nó e ligação no grafo. Isso inclui o ícone a ser usado, o texto do rótulo, a cor e o comportamento do tooltip.
*   **Gerenciamento de Eventos:** Captura todas as interações do usuário, como cliques do mouse, duplo-cliques, movimentos da roda do mouse (zoom) e pressionamento de teclas.
*   **Comunicação com a API:** Contém as funções JavaScript que fazem as chamadas `fetch` para a API do backend Flask.
*   **Atualização do Grafo:** Processa as respostas JSON do backend e utiliza as funções do `VivaGraphJS` (`graph.addNode()`, `graph.addLink()`, `graph.removeNode()`) para atualizar dinamicamente a visualização.

### Funções e Lógica Essencial

#### **Inicialização: `main()`**

Esta função é executada assim que a página é carregada (`onload`). Ela:
1.  Chama `ajustaAmbiente()` para configurar a interface (ex: popular o menu de ícones, ajustar para mobile).
2.  Inicializa o `Viva.Graph.Layout.forceDirected` para gerenciar a física do grafo.
3.  Inicializa o `Viva.Graph.View.renderer` para desenhar o grafo na tela.
4.  Verifica se há dados iniciais passados pelo Flask (no objeto `gparam.inicio`) e, se houver, chama a função apropriada para carregar o grafo inicial (ex: `menu_incluirCamada()` ou `inserirJson()`).

#### **Renderização Visual: `graphics.node()` e `graphics.link()`**

*   **`graphics.node(function(node){...})`:** Esta função é chamada pelo `VivaGraphJS` para cada nó que precisa ser desenhado. Ela retorna um grupo de elementos SVG (`<g>`) que compõem o nó visual:
    *   Um retângulo (`<rect>`) para a cor de fundo.
    *   Uma imagem (`<image>`) para o ícone, cuja URL é determinada pela função `iconeF()`.
    *   Um texto (`<text>`) com `tspan`s para o ID, a descrição e a nota do nó.
    *   Um retângulo de seleção animado, que fica visível quando o nó é selecionado.
    *   Handlers de eventos como `onmousedown` e `ondblclick` são anexados aqui.

*   **`graphics.link(function(link){...})`:** Similarmente, esta função desenha a linha (`<path>`) e o texto (`<text>`) para cada ligação.

#### **Comunicação com o Backend: `menu_incluirCamada()` e `inserirJson()`**

*   **`menu_incluirCamada(idin, camada, tipo)`:** Esta é a principal função de busca de dados.
    1.  Ela constrói a URL da API do backend, como `/rede/grafojson/cnpj/2/`.
    2.  Cria o corpo (`body`) da requisição, que é uma string JSON contendo a lista de IDs dos nós selecionados.
    3.  Usa a API `fetch` para enviar uma requisição `POST` para o servidor.
    4.  No `.then()` da promessa do `fetch`, ela recebe a resposta JSON do servidor e a passa para a função `inserirJson()`.

*   **`inserirJson(jsonIn, texto, ...)`:** Esta função recebe o JSON do backend e atualiza o grafo.
    1.  Ela percorre a lista `jsonIn.no`. Para cada nó, ela verifica se já existe no grafo (`graph.hasNode()`). Se não existir, ela o adiciona com `graph.addNode(noaux.id, noaux)`.
    2.  Ela percorre a lista `jsonIn.ligacao` e adiciona cada nova ligação com `graph.addLink(ligaux.origem, ligaux.destino, ligaux)`.
    3.  O `VivaGraphJS` automaticamente detecta essas adições e atualiza a renderização na tela.

#### **Gerenciamento de Eventos: `evento_teclasDown(e)` e `onContextMenu(e)`**

*   **`evento_teclasDown(e)`:** Um grande `switch-case` (implementado com `if-else`) que mapeia códigos de teclas (`e.code`) e modificadores (`e.shiftKey`, `teclaCtrlF(e)`) para funções específicas do menu (ex: `KeyI` chama `menu_inserir()`, `Delete` chama `menu_excluirNosSelecionados()`).
*   **`onContextMenu(e)`:** Previne o menu de contexto padrão do navegador e exibe o menu customizado (`<menu id='menu_contexto'>`) na posição do clique do mouse.

A interface é, portanto, um sistema reativo: uma ação do usuário dispara um evento, que chama uma função, que faz uma requisição à API, que por sua vez aciona a função de inserção de dados, fechando o ciclo e atualizando a tela.

## 6. Fluxo de Dados - Um Exemplo Prático

Para consolidar o entendimento de como as partes da aplicação interagem, vamos detalhar o fluxo de eventos que ocorre quando um usuário realiza a ação mais comum: expandir um nó de uma empresa para ver seus sócios.

**Cenário:** O usuário vê um nó de uma empresa no grafo e dá um duplo-clique sobre ele.

1.  **Captura do Evento (Frontend):**
    *   O handler de evento `ui.ondblclick` definido na função `graphics.node()` dentro de `rede_template.html` é acionado.
    *   Este handler chama a função `menu_incluir1Camada(node.id)`.

2.  **Preparação da Requisição (Frontend):**
    *   A função `menu_incluir1Camada()` determina que esta é a primeira expansão para este nó (ou a próxima camada sequencial) e chama `menu_incluirCamada(node.id, 1, 'cnpj')`.
    *   Dentro de `menu_incluirCamada()`, o JavaScript constrói a URL da API: `base + 'grafojson/cnpj/1/' + id_do_no`.
    *   Ele cria o corpo da requisição POST, que é uma string JSON contendo o ID do nó clicado: `JSON.stringify(['PJ_12345678901234'])`.
    *   Uma chamada `fetch` é enviada para o backend.

3.  **Processamento da Requisição (Backend):**
    *   O servidor Flask (`rede.py`) recebe a requisição na rota `@app.route('/rede/grafojson/cnpj/<int:camada>/<cpfcnpj>')`.
    *   A função `serve_rede_json_cnpj()` é executada. Ela extrai a `camada` (1) e a lista de IDs do corpo da requisição.
    *   Ela chama a função `rede_relacionamentos.camadasRede(camada=1, listaIds=['PJ_12345678901234'], ...)`, delegando a tarefa para o módulo de banco de dados.

4.  **Consulta ao Banco de Dados (Módulo de Dados):**
    *   A função `camadasRede()` em `rede_sqlite_cnpj.py` inicia.
    *   Ela cria tabelas temporárias em memória (`tmp_ids`, `tmp_ligacao`).
    *   A `tmp_ids` é populada com `['PJ_12345678901234']`.
    *   A função executa uma consulta SQL que faz um `JOIN` entre a `tmp_ids` e a tabela `ligacao` do banco `rede.db`. A consulta busca todas as ligações onde `id1` ou `id2` seja o CNPJ da empresa.
    *   Os resultados (os sócios e outras empresas ligadas) são inseridos nas tabelas temporárias.
    *   A função `camadasRede_json()` é chamada. Ela busca os detalhes de cada novo ID encontrado (nomes dos sócios, etc.) no banco `cnpj.db`.
    *   Finalmente, ela monta e retorna um grande objeto JSON contendo a lista de novos nós (`no`) e novas ligações (`ligacao`).

5.  **Resposta e Renderização (Backend e Frontend):**
    *   De volta a `rede.py`, a função `serve_rede_json_cnpj()` recebe o objeto do módulo de dados e o serializa para JSON usando `orjson.dumps()`.
    *   O servidor Flask envia a resposta JSON de volta para o navegador.
    *   No frontend, o `.then()` da chamada `fetch` original é executado. Ele recebe o JSON e o passa para a função `inserirJson(data, ...)`.
    *   `inserirJson()` itera sobre as listas `data.no` e `data.ligacao`. Para cada item, ela chama `graph.addNode()` e `graph.addLink()`.
    *   A biblioteca `VivaGraphJS` detecta as adições ao modelo de dados do grafo, e o motor de layout de física calcula as novas posições. O renderizador SVG desenha os novos nós e ligações na tela.

O usuário vê o grafo se expandir, com os nós dos sócios aparecendo conectados ao nó da empresa que ele clicou. Todo esse processo, do clique à renderização, ocorre de forma assíncrona em poucos segundos.

## 7. Interações e Funcionalidades

A tabela abaixo mapeia as principais ações do usuário para as funções JavaScript e rotas do backend correspondentes.

| Ação do Usuário | Atalho | Função JS Principal | Rota Backend (se aplicável) | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **Expandir Nó** | Duplo-Clique / Tecla `1`-`9` | `menu_incluir1Camada()` / `menu_incluirCamada()` | `/rede/grafojson/cnpj/...` | Busca e adiciona nós e ligações de uma nova camada. |
| **Ver Detalhes** | Tecla `D` | `menu_dados()` | `/rede/dadosjson/...` | Exibe um popup com os dados detalhados de um nó. |
| **Ver Detalhes em Nova Aba** | `Shift`+`D` | `menu_dados(true)` | `/rede/consulta_cnpj/` | Abre uma nova aba com uma página formatada dos dados do CNPJ. |
| **Inserir/Buscar** | Tecla `I` / Botão `+` | `menu_inserir()` | `/rede/grafojson/cnpj/...` | Abre um prompt para buscar um CNPJ/CPF/Nome e o adiciona ao grafo. |
| **Criar Novo Item** | Tecla `U` | `menu_ligar_novo()` | N/A | Cria um novo nó genérico (não-PF/PJ) no grafo. |
| **Salvar Grafo (Local)** | Menu | `menu_salvaJsonArquivo()` | N/A | Salva o estado do grafo em um arquivo JSON no computador do usuário. |
| **Salvar Grafo (Servidor)** | Menu | `menu_exportaJSONServidor()` | `/rede/arquivos_json_upload/...` | Salva o estado do grafo em um arquivo JSON no servidor e fornece um link compartilhável. |
| **Carregar Grafo (Servidor)** | Menu | `menu_importaJSONServidor()` | `/rede/arquivos_json/...` | Carrega um grafo a partir de um arquivo JSON salvo no servidor. |
| **Exportar para Excel** | Menu / Botão | `menu_exportaExcel()` | `/rede/dadosemarquivo/xlsx` | Exporta os dados dos nós visíveis para um arquivo `.xlsx`. |
| **Mostrar no Mapa** | Menu / Botão | `menu_exportaArquivo(false, 'osm')` | `/rede/mapa` | Gera e exibe um mapa com os endereços das empresas. |
| **Excluir Nós** | Tecla `Del` | `menu_excluirNosSelecionados()` | N/A | Remove os nós selecionados do grafo. |
| **Pausar/Continuar Layout** | Barra de Espaço | `menu_rendererAtivarParar()` | N/A | Pausa ou continua a simulação de física do grafo. |

## 8. Configuração e Scripts Auxiliares

### Arquivo de Configuração (`rede.ini`)

Este arquivo permite personalizar diversos aspectos do comportamento da aplicação sem a necessidade de alterar o código-fonte. Ele é lido pelo módulo `rede_config.py` no início da execução.

**Seções e Parâmetros Importantes:**

*   **`[BASE]`**: Define os caminhos para os arquivos de banco de dados SQLite. É aqui que se aponta para as bases `cnpj.db`, `rede.db`, etc.
*   **`[ETC]`**: Contém configurações diversas.
    *   `limiter_padrao`: Controla o limite de requisições à API.
    *   `busca_google`, `busca_chaves`: Habilita ou desabilita as funcionalidades de busca no Google.
    *   `kLimiteCamada`: Define o número máximo de nós que uma expansão de camada pode gerar, para evitar sobrecarga.
*   **`[INICIO]`**: Permite definir uma mensagem de advertência que aparece quando a aplicação é aberta.

### Scripts de Criação das Bases (`rede_cria_tabelas/`)

Esta pasta contém um conjunto de scripts Python essenciais que **não fazem parte da aplicação principal**, mas são ferramentas cruciais para **preparar os dados** que a aplicação irá usar.

A Receita Federal disponibiliza os dados públicos em uma série de arquivos `.zip` contendo CSVs. Esses dados brutos não são adequados para as consultas rápidas que a aplicação necessita. O propósito dos scripts neste diretório é:

1.  **Baixar os Dados:** O script `dados_cnpj_baixa.py` baixa os arquivos `.zip` mais recentes do site de dados abertos da Receita.
2.  **Converter para SQLite:** O script `dados_cnpj_para_sqlite.py` descompacta os arquivos e os importa para um banco de dados SQLite (`cnpj.db`), criando as tabelas `empresas`, `estabelecimento`, `socios`, etc. Este processo pode levar várias horas e consumir dezenas de gigabytes de espaço em disco.
3.  **Criar a Base de Rede:** O script `rede_cria_tabela_rede.db.py` executa o passo mais importante: ele lê a base `cnpj.db` e cria a base `rede.db`. Ele processa todas as relações de sociedade e cria a tabela `ligacao`, que contém as conexões diretas entre os nós (PF e PJ). Esta base pré-processada é o que garante a performance da aplicação na hora de expandir o grafo.
4.  **Criar Outras Bases:** Scripts como `rede_cria_tabela_cnpj_links_ete.py` criam bases de dados adicionais para outros tipos de vínculos.

Após a execução desses scripts, os arquivos `.db` gerados devem ser movidos para a pasta `rede/bases/` para que a aplicação principal possa utilizá-los. Este processo de atualização das bases precisa ser refeito periodicamente (idealmente, todo mês) para manter os dados da aplicação atualizados.
