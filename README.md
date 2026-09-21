# dev-local-artifact-pruner

O **dev-local-artifact-pruner** é uma ferramenta desktop local-first desenvolvida em Python e PySide6 para auditar projetos de desenvolvimento locais, verificar sua inatividade através do histórico do Git e podar com segurança artefatos regeneráveis pesados (`node_modules`, `venv`, `.venv`, caches) e arquivos não versionados elegíveis, liberando espaço em disco.

## Objetivo

Auditar diretórios locais de desenvolvimento, apresentar diagnósticos claros de inatividade através do histórico do Git e permitir a poda seletiva e reversível de dependências pesadas, sem jamais colocar em risco o código-fonte, branches ou documentações do desenvolvedor.

## Premissas

- **Execução 100% Local**: Sem telemetria, envio de dados, backend web ou sincronização remota.
- **Segurança de Dados**: Arquivos de documentação (`.md`, `.txt`, `.html`), variáveis de ambiente (`.env*`) e bancos de dados (`*.sqlite`, `*.db`) são estritamente protegidos e nunca removidos.
- **Resiliência no Windows**: Bypass automático de atributos de somente leitura (`FILE_ATTRIBUTE_READONLY`) comuns em dependências do `node_modules`.
- **Reversibilidade Automatizada**: Gravação do script `rebuild_dependencies.py` na raiz de cada projeto limpo contendo os comandos reais para restauração do ambiente.

## Stack Prevista

- Python 3.11 ou superior.
- PySide6 para interface desktop.
- Subprocess e Pathlib para integração com o Git e manipulação de arquivos.
- pytest para testes automatizados.

## Estrutura do Projeto

```text
.
├── pyproject.toml
├── README.md
├── src/
│   └── dev_local_artifact_pruner/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── git_client.py
│       │   ├── models.py
│       │   ├── pruner.py
│       │   ├── rebuilder.py
│       │   ├── rules.py
│       │   └── scanner.py
│       └── utils/
│           ├── __init__.py
│           ├── disk_usage.py
│           ├── formatters.py
│           └── safe_delete.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_disk_usage.py
    ├── test_formatters.py
    ├── test_git_client.py
    ├── test_models.py
    ├── test_pruner.py
    ├── test_rebuilder.py
    ├── test_rules.py
    ├── test_safe_delete.py
    ├── test_scaffold.py
    └── test_scanner.py
```
