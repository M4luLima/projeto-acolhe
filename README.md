# Projeto Acolhe — Sistema Web Integrado (Full-Stack + REST API + DB)

Sistema web completo desenvolvido para a ação extensionista **Projeto Acolhe: Cidadania, Saúde e Tecnologia** na USF Irmã Terezinha (Peixinhos).

## Arquitetura do Sistema
- **Frontend Interativo**: Interface Web desenvolvida em Streamlit (Dashboard, Formulário de Diagnóstico, Gestão de Encaminhamentos e Guia Digital).
- **Banco de Dados Relacional**: SQLite3 (acolhe_sistema.db) com tabelas normalizadas para participantes, atendimentos e suporte digital.
- **REST API Backend**: Servidor HTTP RESTful com endpoints JSON para integração (/api/v1/metricas, /api/v1/atendimentos, /api/v1/health).

## Como Executar Localmente
1. Instale as dependências:
   pip install -r requirements.txt
2. Execute o sistema web:
   streamlit run sistema_acolhe_completo.py
3. Acesse no seu navegador em http://localhost:8501.

## Como Subir para a Nuvem
1. Crie um repositório no GitHub e adicione os arquivos do projeto.
2. Acesse a plataforma de hospedagem de sua preferência (Streamlit Cloud, Render, Railway ou Fly.io).
3. Selecione o repositório e confirme a publicação do site.

---
Grupo 2 — Análise e Desenvolvimento de Sistemas (ADS)
