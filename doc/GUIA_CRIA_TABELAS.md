# Guia Detalhado do Processo de Criação de Tabelas

## 1. Introdução

O diretório `rede_cria_tabelas` contém um conjunto de scripts Python que formam um pipeline de ETL (Extract, Transform, Load). A sua finalidade é baixar os dados públicos brutos de CNPJ disponibilizados pela Receita Federal, processá-los e estruturá-los em bancos de dados SQLite otimizados para o uso na aplicação principal da RedeCNPJ.

Estes scripts **não são parte da aplicação web interativa**, mas sim ferramentas de preparação de dados que devem ser executadas previamente. Sem a execução bem-sucedida deste pipeline, a aplicação principal não terá dados para exibir. O processo é intensivo em uso de CPU, memória e disco, e pode levar várias horas para ser concluído.

## 2. Visão Geral do Processo

O pipeline de dados pode ser dividido em três grandes etapas, executadas em sequência:

1.  **Download (Extração):** O primeiro script baixa os arquivos `.zip` contendo os dados brutos (em formato CSV) do portal de dados abertos da Receita Federal.
2.  **Conversão para a Base Principal (Transformação/Carga):** O segundo script descompacta os arquivos baixados e os importa para um banco de dados SQLite principal, o `cnpj.db`. Durante este processo, ele realiza transformações cruciais nos dados e cria índices para otimizar futuras consultas.
3.  **Criação das Bases Otimizadas (Transformação/Carga):** Os scripts finais leem a base `cnpj.db` e criam bancos de dados secundários (`rede.db`, `rede_search.db`, `cnpj_links_ete.db`) que são altamente otimizados para as funcionalidades específicas da aplicação, como a rápida expansão do grafo de relacionamentos e a busca textual por nomes.

## 3. Dependências

Para executar os scripts neste diretório, as seguintes bibliotecas Python são necessárias, conforme listado no arquivo `rede_cria_tabelas/requirements.txt`:

*   `pandas` e `sqlalchemy`: Para manipulação de dados e interação com o banco de dados SQLite.
*   `dask` e `dask-expr`: Para processamento de dados em paralelo, essencial para lidar com o grande volume dos arquivos da Receita sem esgotar a memória RAM.
*   `beautifulsoup4`, `requests`, `lxml`: Para fazer o scraping da página da Receita e encontrar os links de download mais recentes.
*   `wget`, `parfive`: Para realizar o download dos arquivos de forma eficiente e paralela.
*   `pyarrow`: Usado como um motor de execução eficiente para Dask e Pandas.

## 4. Análise Detalhada dos Scripts

Esta seção detalha o funcionamento de cada script individualmente.

### 4.1. `dados_cnpj_baixa.py`

*   **Propósito:** Baixar os arquivos de dados públicos de CNPJ mais recentes do site da Receita Federal.
*   **Funcionamento:**
    1.  **Verificação de Pré-requisitos (`requisitos()`):** Antes de iniciar, o script verifica se os diretórios de destino (`dados-publicos-zip` e `dados-publicos`) estão vazios. Caso não estejam, ele solicita a confirmação do usuário para apagar o conteúdo existente, garantindo que dados de datas diferentes não sejam misturados.
    2.  **Scraping de Links:** Utiliza as bibliotecas `requests` e `BeautifulSoup4` para acessar a URL principal de dados abertos da Receita. Ele parseia o HTML da página para encontrar o link do diretório mais recente (ex: `2024-08/`).
    3.  **Listagem de Arquivos:** Em seguida, acessa a página do diretório mais recente e, novamente com `BeautifulSoup4`, extrai as URLs de todos os arquivos que terminam com `.zip`.
    4.  **Download Paralelo:** Utiliza a biblioteca `parfive` para baixar todos os arquivos da lista de forma paralela (com até 5 conexões simultâneas), o que acelera significativamente o processo. Os arquivos `.zip` são salvos no diretório `dados-publicos-zip`.

### 4.2. `dados_cnpj_para_sqlite.py`

*   **Propósito:** Descompactar os arquivos brutos e carregá-los em um banco de dados SQLite (`cnpj.db`), realizando as transformações e indexações necessárias.
*   **Funcionamento:**
    1.  **Descompactação:** O script primeiro itera sobre todos os arquivos `.zip` na pasta `dados-publicos-zip` e os extrai para a pasta `dados-publicos` usando a biblioteca `zipfile`.
    2.  **Carga de Tabelas Pequenas:** Para as tabelas de códigos (CNAE, Municípios, Países, etc.), que são pequenas, ele utiliza o `pandas` para ler os CSVs e carregá-los diretamente no `cnpj.db`, criando índices em suas chaves primárias.
    3.  **Carga de Tabelas Grandes (com Dask):** Para os arquivos massivos de Empresas, Estabelecimentos e Sócios, o script adota uma abordagem mais robusta para não esgotar a memória:
        *   Primeiro, ele cria a estrutura das tabelas no SQLite com comandos `CREATE TABLE`.
        *   Em seguida, utiliza `dask.dataframe.read_csv` para ler os grandes arquivos CSV em pedaços (chunks). Dask processa os dados de forma "preguiçosa" e em paralelo, sem carregar tudo na memória de uma vez.
        *   `dask.dataframe.to_sql` é usado para inserir esses chunks de dados nas tabelas do SQLite.
    4.  **Transformação e Indexação (SQL):** Após carregar todos os dados brutos, o script executa uma longa sequência de comandos SQL para refinar o banco de dados:
        *   Converte campos de texto para numéricos (ex: `capital_social`).
        *   Cria a coluna `cnpj` completa (14 dígitos) na tabela `estabelecimento`.
        *   **Cria a tabela `socios` final:** Esta é uma etapa crucial. A tabela original de sócios da Receita não os vincula a um CNPJ de 14 dígitos. Este script faz a junção (`JOIN`) dos sócios com a tabela de estabelecimentos para associar cada sócio ao CNPJ da **matriz** da empresa, criando uma tabela de sócios limpa e pronta para ser usada.
        *   **Cria Índices:** Por fim, ele cria múltiplos índices (`CREATE INDEX`) nas colunas mais consultadas (`cnpj`, `razao_social`, `cnpj_cpf_socio`, `nome_socio`), o que é absolutamente vital para a performance das buscas na aplicação principal.
    5.  **Limpeza:** Opcionalmente, apaga os arquivos CSV descompactados para economizar espaço em disco.
### 4.3. `rede_cria_tabela_rede.db.py`

*   **Propósito:** Criar as bases de dados `rede.db` e `rede_search.db`, que são as mais importantes para a performance e funcionalidade da aplicação de visualização.
*   **Funcionamento:**
    1.  **Criação da Tabela de Ligações (`rede.db`):**
        *   Este é o passo mais importante de todo o pipeline. O script executa uma série de comandos SQL (`sql_ligacao`) para ler a base `cnpj.db` e construir a tabela `ligacao`.
        *   A tabela `ligacao` é uma representação simples e direta de todas as relações societárias, de representação legal e de filial/matriz. Cada linha contém `id1` (origem), `id2` (destino) e `descricao` (tipo de relação).
        *   Os IDs são padronizados com prefixos (`PJ_` para empresas, `PF_` para pessoas físicas, `PE_` para sócios no exterior), espelhando o formato usado pela aplicação.
        *   Ao pré-processar e materializar todas essas relações em uma única tabela, o script evita que a aplicação principal tenha que fazer `JOIN`s complexos e lentos em tempo de execução. As consultas para expandir o grafo se tornam extremamente rápidas, pois consultam apenas esta tabela otimizada.
    2.  **Criação do Índice de Busca (`rede_search.db`):**
        *   O script cria uma tabela virtual especial (`CREATE VIRTUAL TABLE id_search USING fts5`). O `fts5` é uma extensão do SQLite que cria um poderoso índice de busca em texto completo.
        *   Ele popula esta tabela com o conteúdo de todos os campos que podem ser pesquisados (razão social, nome fantasia, nome de sócio), concatenando o ID do nó com o texto (ex: `PJ_12345678901234-NOME DA EMPRESA`).
        *   Isso permite que a aplicação principal encontre qualquer entidade com uma única consulta `MATCH`, que é ordens de magnitude mais rápida do que usar `LIKE '%termo%'` em tabelas normais.

### 4.4. `rede_cria_tabela_cnpj_links_ete.py`

*   **Propósito:** Criar o banco de dados auxiliar `cnpj_links_ete.db` para encontrar relações indiretas entre empresas com base em **E**ndereços, **T**elefones ou **E**-mails em comum.
*   **Funcionamento:**
    1.  **Extração e Normalização:** O script lê a tabela `estabelecimento` do `cnpj.db` em grandes blocos. Para cada bloco, ele extrai os dados de endereço, telefone e e-mail.
    2.  **Normalização de Endereços (`normalizaEndereco`):** Esta é a parte mais complexa. A função `normalizaEndereco` aplica uma série de regras para padronizar os endereços: converte para maiúsculas, remove acentos e pontuação, expande abreviações (`R` -> `RUA`, `AV` -> `AVENIDA`), separa números de letras e, crucialmente, **ordena as palavras alfabeticamente**. O resultado é um "hash" canônico do endereço, que permite que `Rua Principal, 123` e `Principal Rua Nº 123` sejam identificados como o mesmo local.
    3.  **Agrupamento:** Para cada tipo de dado (endereço, telefone, e-mail), o script agrupa os dados normalizados e conta quantos CNPJs estão associados a cada um.
    4.  **Criação de Links:** Ele cria uma tabela final `link_ete`, inserindo uma linha para cada CNPJ que compartilha um endereço, telefone ou e-mail com pelo menos uma outra empresa. O link é feito entre o ID da empresa (`PJ_...`) e um ID que representa a informação compartilhada (`EN_` para endereço, `TE_` para telefone, `EM_` para e-mail).

### 4.5. `cria_tabela_cnep.py`

*   **Propósito:** Baixar os dados de empresas punidas do Cadastro Nacional de Empresas Punidas (CNEP), mantido pela Controladoria-Geral da União (CGU), e criar uma base de dados local para consulta.
*   **Funcionamento:**
    1.  **Verificação de Atualização:** Antes de baixar, o script verifica a data da última modificação do arquivo no servidor (através do cabeçalho HTTP `Last-Modified`) e compara com a data salva localmente em um arquivo de metadados (`cnep_metadata.json`). O download só prossegue se houver uma nova versão disponível.
    2.  **Download e Processamento:** O script baixa o arquivo `.zip` do Portal da Transparência, o descompacta em memória e lê o arquivo CSV contido nele com a biblioteca `pandas`.
    3.  **Filtragem e Limpeza:** Ele filtra os dados para manter apenas as "PESSOAS JURÍDICAS", seleciona as colunas de interesse (CNPJ, nome da empresa, tipo de sanção, datas, etc.) e remove qualquer formatação do CNPJ para manter apenas os 14 dígitos.
    4.  **Criação do Banco de Dados:** Os dados limpos são salvos (ou atualizados) no banco de dados `dados-publicos/dados_externos.db`, em uma tabela chamada `cnep`. Um índice é criado na coluna `cnpj` para otimizar as consultas.

### 4.6. `cria_tabela_ceis.py`

*   **Propósito:** Baixar os dados de empresas punidas do Cadastro de Empresas Inidôneas e Suspensas (CEIS), também mantido pela CGU, e adicioná-los à base de dados local.
*   **Funcionamento:**
    1.  **Download e Processamento:** O script acessa o link direto para o arquivo `.csv` do CEIS no Portal da Transparência. Ele baixa e processa o arquivo usando `pandas`.
    2.  **Filtragem e Limpeza:** Assim como o script do CNEP, ele seleciona as colunas relevantes, limpa e padroniza o número do CNPJ.
    3.  **Criação do Banco de Dados:** Os dados são salvos na tabela `ceis` dentro do mesmo banco de dados `dados-publicos/dados_externos.db`, permitindo que a aplicação consulte ambas as fontes de sanção em um único local.

### 4.7. `cria_tabela_correcionais.py`

*   **Propósito:** Processar os dados de sanções aplicadas a **pessoas físicas** a partir do arquivo de "Dados Correcionais" da CGU.
*   **Funcionamento:**
    1.  **Download Manual (Pré-requisito):** Diferente dos outros scripts, este **não realiza o download automático**. O usuário deve baixar manualmente o arquivo `dados_correcionais.zip` e colocá-lo na pasta `dados-publicos-zip/`.
    2.  **Processamento:** O script descompacta o arquivo `.zip` em memória, lê o CSV de sanções e filtra os dados para manter apenas as sanções aplicadas a pessoas físicas.
    3.  **Limpeza:** A coluna de CPF é limpa para conter apenas números, facilitando o `JOIN` com os dados da Receita.
    4.  **Criação do Banco de Dados:** Os dados limpos são salvos na tabela `correcionais` dentro do banco `dados-publicos/dados_externos.db`.

## 5. Fluxo de Execução Recomendado

Para gerar todas as bases de dados necessárias para a aplicação a partir do zero, os scripts devem ser executados na seguinte ordem, dentro do diretório `rede_cria_tabelas`:

1.  **`python dados_cnpj_baixa.py`**
    *   **O que faz:** Baixa os arquivos `.zip` da Receita para a pasta `dados-publicos-zip/`.
    *   **Pré-requisito:** Acesso à internet.

2.  **`python dados_cnpj_para_sqlite.py`**
    *   **O que faz:** Processa os arquivos `.zip` e cria a base principal `dados-publicos/cnpj.db`.
    *   **Pré-requisito:** Execução bem-sucedida do passo 1.

3.  **`python rede_cria_tabela_rede.db.py`**
    *   **O que faz:** Lê `cnpj.db` e cria as bases otimizadas `dados-publicos/rede.db` e `dados-publicos/rede_search.db`.
    *   **Pré-requisito:** Execução bem-sucedida do passo 2.

4.  **`python rede_cria_tabela_cnpj_links_ete.py`**
    *   **O que faz:** (Opcional) Lê `cnpj.db` e cria a base `dados-publicos/cnpj_links_ete.db` para vínculos por endereço/telefone/email.
    *   **Pré-requisito:** Execução bem-sucedida do passo 2.

5.  **`python cria_tabela_cnep.py`**
    *   **O que faz:** (Opcional) Baixa os dados do CNEP e cria/atualiza a base `dados-publicos/dados_externos.db`.
    *   **Pré-requisito:** Acesso à internet.

6.  **`python cria_tabela_ceis.py`**
    *   **O que faz:** (Opcional) Baixa os dados do CEIS e cria/atualiza a base `dados-publicos/dados_externos.db`.
    *   **Pré-requisito:** Acesso à internet.

7.  **`python cria_tabela_correcionais.py`**
    *   **O que faz:** (Opcional) Processa os dados de sanções a pessoas físicas (Dados Correcionais da CGU) e os adiciona à base `dados-publicos/dados_externos.db`.
    *   **Pré-requisito:** Download manual do arquivo `dados_correcionais.zip` para a pasta `dados-publicos-zip/`.

Após a conclusão, todos os arquivos `.db` gerados na pasta `dados-publicos/` devem ser movidos para a pasta `rede/bases/` para que a aplicação principal possa encontrá-los.
