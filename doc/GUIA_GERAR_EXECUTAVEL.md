# Guia: Gerando um Executável Único (`.exe`)

Este guia explica como compilar todos os scripts de criação de tabelas em um único arquivo executável (`.exe`) para Windows. Este executável poderá ser executado com um duplo clique e funcionará de forma independente, sem a necessidade de ter o Python instalado na máquina de destino (desde que seja o mesmo sistema operacional Windows).

## Pré-requisitos

1.  **Ambiente Python:** Você precisa ter um ambiente Python (versão 3.9 a 3.12) funcionando na sua máquina de desenvolvimento. A forma mais fácil de garantir isso é seguindo o [guia de instalação para Windows](./instalacao_windows.md).
2.  **Código Fonte:** Você deve ter o código fonte do projeto `rede-cnpj` baixado em sua máquina.

## Passo a Passo para Gerar o `.exe`

### Passo 1: Instalar Dependências

Abra o terminal de sua preferência (Anaconda Prompt, cmd.exe, PowerShell) e navegue até a pasta `rede_cria_tabelas` dentro do projeto.

```sh
cd caminho/para/rede-cnpj-master/rede_cria_tabelas
```

Execute o seguinte comando para instalar todas as dependências necessárias, incluindo o `pyinstaller`:

```sh
pip install -r requirements.txt
```

### Passo 2: Executar o PyInstaller

Com o `pyinstaller` instalado, você pode agora gerar o executável. Na mesma pasta (`rede_cria_tabelas`), execute o seguinte comando:

```sh
pyinstaller rede_cria_tabelas.spec
```

Este comando utiliza o arquivo de configuração `rede_cria_tabelas.spec` (que já está no projeto) para encontrar o script principal e incluir todos os outros arquivos necessários no pacote.

O processo de compilação pode levar alguns minutos.

### Passo 3: Localizar e Usar o Executável

Após a conclusão do processo, o PyInstaller criará algumas pastas. O seu arquivo executável estará localizado dentro da pasta `dist`.

-   **Caminho do arquivo:** `rede_cria_tabelas/dist/criar_todas_as_bases.exe`

Agora você pode mover este arquivo `criar_todas_as_bases.exe` para qualquer local, inclusive para outras máquinas (com Windows), e executá-lo com um duplo clique.

Ao ser executado, ele abrirá um console (janela de terminal) e iniciará o processo completo de download e criação das bases de dados, exatamente como o script Python faria.
