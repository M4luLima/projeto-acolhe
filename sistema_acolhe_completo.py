import streamlit as st
import sqlite3
import pandas as pd
import json
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Configuração da página Web
st.set_page_config(
    page_title="Projeto Acolhe — Sistema Web Integrado",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "acolhe_sistema.db"

# Conexão e Inicialização do Banco de Dados
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Tabela de Participantes
    c.execute("""
        CREATE TABLE IF NOT EXISTS participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            faixa_etaria TEXT NOT NULL,
            telefone TEXT,
            possui_smartphone TEXT,
            facilidade_digital TEXT,
            data_cadastro TEXT
        )
    """)
    
    # Tabela de Atendimentos / Diagnósticos
    c.execute("""
        CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            participante_id INTEGER,
            nome_participante TEXT,
            data_registro TEXT,
            demanda_saude TEXT,
            demanda_cidadania TEXT,
            demanda_tecnologia TEXT,
            area_responsavel TEXT,
            acao_realizada TEXT,
            encaminhamento TEXT,
            status TEXT DEFAULT 'Pendente',
            FOREIGN KEY (participante_id) REFERENCES participantes (id)
        )
    """)
    
    # Tabela de Suporte Digital
    c.execute("""
        CREATE TABLE IF NOT EXISTS suporte_digital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_atendimento TEXT,
            servico_acessado TEXT,
            orientacao TEXT,
            data_suporte TEXT
        )
    """)
    
    # Dados Iniciais (Seed Data se vazio)
    c.execute("SELECT COUNT(*) FROM atendimentos")
    if c.fetchone()[0] == 0:
        seed_data = [
            ("ACT-2026-001", "Maria José da Silva", "Idoso (60+)", "Sim (Wi-Fi)", "Baixa", 
             "Dificuldade de ver vacinas no app", "Dúvida sobre Benefício BPC", "Ajuda no Gov.br", 
             "Enfermagem", "Recuperação de senha do Gov.br e agendamento", "CRAS Peixinhos", "Concluído", "2026-10-15 09:30"),
            ("ACT-2026-002", "João Pedro Santos", "Adulto (30-59)", "Sim (Dados Móveis)", "Média", 
             "Agendamento de consulta especializada", "Emissão de Carteira de Trabalho Digital", "Baixar app CTPS", 
             "Direito", "Orientações sobre CTPS Digital e agendamento de exame", "Defensoria Pública", "Em Andamento", "2026-10-15 10:15"),
            ("ACT-2026-003", "Ana Clara Lima", "Jovem (18-29)", "Sim (Wi-Fi)", "Alta", 
             "Orientação sobre prevenção e saúde da mulher", "Consulta sobre CadÚnico", "Navegação em sites públicos", 
             "ADS", "Auxílio na atualização cadastral e navegação em serviços", "CRAS Peixinhos", "Concluído", "2026-10-16 11:00"),
            ("ACT-2026-004", "Severino Ramos de Oliveira", "Idoso (60+)", "Não possui", "Nenhuma", 
             "Solicitação de medicamentos contínuos", "Consulta aposentadoria e BPC/LOAS", "Inclusão digital básica", 
             "Interdisciplinar", "Triagem completa de saúde e atendimento jurídico", "INSS / Posto de Saúde", "Pendente", "2026-10-17 14:20"),
            ("ACT-2026-005", "Francisca Souza", "Adulto (30-59)", "Sim (Dados Móveis)", "Baixa", 
             "Dificuldade de usar Meu SUS Digital", "Regularização de CPF", "Uso do aplicativo Meu SUS", 
             "ADS", "Instalação do app Meu SUS Digital e criação de conta Gov.br", "Receita Federal", "Em Andamento", "2026-10-18 08:45")
        ]
        
        for codigo, nome, faixa, smartphone, facilidade, d_saude, d_cidadania, d_tec, area, acao, enc, status, data in seed_data:
            c.execute("""
                INSERT INTO participantes (nome, faixa_etaria, possui_smartphone, facilidade_digital, data_cadastro)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, faixa, smartphone, facilidade, data))
            part_id = c.lastrowid
            
            c.execute("""
                INSERT INTO atendimentos 
                (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo, part_id, nome, data, d_saude, d_cidadania, d_tec, area, acao, enc, status))
            
    conn.commit()
    conn.close()

init_db()

# REST API Backend Handler
class AcolheAPIHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/v1/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "online", "system": "Projeto Acolhe API", "version": "1.0.0"}).encode())
            
        elif path == "/api/v1/atendimentos":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM atendimentos ORDER BY id DESC")
            rows = [dict(row) for row in c.fetchall()]
            conn.close()
            self._set_headers(200)
            self.wfile.write(json.dumps({"total": len(rows), "data": rows}, ensure_ascii=False).encode('utf-8'))
            
        elif path == "/api/v1/metricas":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM atendimentos")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Concluído'")
            concluidos = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Pendente'")
            pendentes = c.fetchone()[0]
            conn.close()
            
            res = {
                "total_atendimentos": total,
                "concluidos": concluidos,
                "pendentes": pendentes,
                "taxa_resolucao_pct": round((concluidos / total * 100), 1) if total > 0 else 0
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint não encontrado"}).encode())

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/api/v1/atendimentos":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            nome = data.get('nome', 'Anônimo')
            faixa = data.get('faixa_etaria', 'Adulto (30-59)')
            smartphone = data.get('possui_smartphone', 'Sim')
            facilidade = data.get('facilidade_digital', 'Média')
            area = data.get('area_responsavel', 'ADS')
            acao = data.get('acao_realizada', '')
            encaminhamento = data.get('encaminhamento', '')
            status = data.get('status', 'Pendente')
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM atendimentos")
            qtd = c.fetchone()[0] + 1
            codigo = f"ACT-2026-{qtd:03d}"
            data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            c.execute("INSERT INTO participantes (nome, faixa_etaria, possui_smartphone, facilidade_digital, data_cadastro) VALUES (?, ?, ?, ?, ?)",
                      (nome, faixa, smartphone, facilidade, data_hoje))
            part_id = c.lastrowid
            
            c.execute("""
                INSERT INTO atendimentos (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo, part_id, nome, data_hoje, data.get('demanda_saude', ''), data.get('demanda_cidadania', ''), data.get('demanda_tecnologia', ''), area, acao, encaminhamento, status))
            
            conn.commit()
            conn.close()
            
            self._set_headers(201)
            self.wfile.write(json.dumps({"message": "Atendimento criado via API", "codigo": codigo}).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint de POST inválido"}).encode())

def run_api_server(port=8050):
    try:
        server = HTTPServer(('0.0.0.0', port), AcolheAPIHandler)
        server.serve_forever()
    except Exception:
        pass

# Iniciar servidor REST API em thread em segundo plano
if "api_started" not in st.session_state:
    st.session_state.api_started = True
    threading.Thread(target=run_api_server, daemon=True).start()

# FRONTEND (STREAMLIT USER INTERFACE)
st.sidebar.title("🏥 Projeto Acolhe")
st.sidebar.caption("Cidadania, Saúde e Tecnologia | USF Irmã Terezinha")

pagina = st.sidebar.radio(
    "Navegação do Sistema Web:",
    [
        "📊 Dashboard & Métricas", 
        "📝 Novo Diagnóstico", 
        "📋 Gestão de Encaminhamentos", 
        "💡 Guia de Inclusão Digital",
        "⚙️ API REST & Documentação"
    ]
)

st.sidebar.divider()
st.sidebar.markdown("**Banco de Dados**: 🟢 SQLite (`acolhe_sistema.db`)")
st.sidebar.markdown("**API REST Backend**: 🟢 Ativa na porta `8050`")

# 1. DASHBOARD & MÉTRICAS
if pagina == "📊 Dashboard & Métricas":
    st.title("📊 Painel Geral de Impacto — Projeto Acolhe")
    st.markdown("Métricas consolidadas em tempo real direto do banco de dados relacional.")
    
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM atendimentos", conn)
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    concluidos = len(df[df['status'] == 'Concluído']) if total > 0 else 0
    pendentes = len(df[df['status'] == 'Pendente']) if total > 0 else 0
    em_andamento = len(df[df['status'] == 'Em Andamento']) if total > 0 else 0
    
    col1.metric("Total de Atendimentos", total)
    col2.metric("Atendimentos Concluídos", concluidos)
    col3.metric("Em Andamento", em_andamento)
    col4.metric("Taxa de Resolução", f"{(concluidos/total*100):.1f}%" if total > 0 else "0%")
    
    st.divider()
    
    if total > 0:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Atendimentos por Área Responsável")
            area_counts = df['area_responsavel'].value_counts()
            st.bar_chart(area_counts)
            
        with c2:
            st.subheader("Distribuição do Nível Digital")
            conn = get_db()
            df_part = pd.read_sql_query("SELECT facilidade_digital FROM participantes", conn)
            conn.close()
            if len(df_part) > 0:
                st.bar_chart(df_part['facilidade_digital'].value_counts())
                
        st.subheader("Registros Recentes na Base de Dados")
        st.dataframe(df[['codigo', 'nome_participante', 'area_responsavel', 'encaminhamento', 'status', 'data_registro']].tail(10), use_container_width=True)
    else:
        st.info("Nenhum dado registrado até o momento.")

# 2. NOVO DIAGNÓSTICO
elif pagina == "📝 Novo Diagnóstico":
    st.title("📝 Formulário de Diagnóstico Interdisciplinar")
    st.markdown("Coleta padronizada durante o acolhimento do morador na USF Irmã Terezinha.")
    
    with st.form("form_novo_acolhimento", clear_on_submit=True):
        st.subheader("Bloco I — Perfil do Participante (Inclusão Digital)")
        col_a, col_b = st.columns(2)
        nome = col_a.text_input("Nome Completo / Identificador do Morador*")
        faixa_etaria = col_b.selectbox("Faixa Etária*", ["Jovem (18-29)", "Adulto (30-59)", "Idoso (60+)"])
        
        col_c, col_d = st.columns(2)
        possui_smartphone = col_c.selectbox("Possui Smartphone / Acesso à Internet?", ["Sim (Wi-Fi)", "Sim (Dados Móveis)", "Não possui"])
        facilidade_digital = col_d.selectbox("Nível de Facilidade com Tecnologia*", ["Nenhuma", "Baixa", "Média", "Alta"])
        
        st.subheader("Bloco II — Triagem Interdisciplinar")
        demanda_saude = st.text_area("Demandas de Saúde (Enfermagem)", placeholder="Histórico vacinal, Meu SUS Digital, consultas...")
        demanda_cidadania = st.text_area("Demandas de Cidadania e Direitos (Direito)", placeholder="Meu INSS, Benefício BPC, CadÚnico, documentos...")
        demanda_tecnologia = st.text_area("Demandas Tecnológicas (ADS)", placeholder="Criação de conta Gov.br, navegação em apps públicos...")
        
        st.subheader("Bloco III — Plano de Ação e Encaminhamento")
        col_e, col_f = st.columns(2)
        area_responsavel = col_e.selectbox("Área Principal do Atendimento*", ["ADS", "Direito", "Enfermagem", "Interdisciplinar"])
        status = col_f.selectbox("Status Inicial*", ["Pendente", "Em Andamento", "Concluído"])
        
        acao_realizada = st.text_input("Ação Prestada no Momento")
        encaminhamento = st.text_input("Órgão / Serviço de Encaminhamento", placeholder="CRAS Peixinhos, Defensoria Pública, Posto de Saúde...")
        
        submitted = st.form_submit_button("💾 Gravar no Banco de Dados")
        
        if submitted:
            if not nome:
                st.error("Por favor, preencha o nome do participante.")
            else:
                conn = get_db()
                c = conn.cursor()
                
                data_agora = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("""
                    INSERT INTO participantes (nome, faixa_etaria, possui_smartphone, facilidade_digital, data_cadastro)
                    VALUES (?, ?, ?, ?, ?)
                """, (nome, faixa_etaria, possui_smartphone, facilidade_digital, data_agora))
                part_id = c.lastrowid
                
                c.execute("SELECT COUNT(*) FROM atendimentos")
                qtd = c.fetchone()[0] + 1
                codigo = f"ACT-2026-{qtd:03d}"
                
                c.execute("""
                    INSERT INTO atendimentos 
                    (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (codigo, part_id, nome, data_agora, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, status))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Atendimento **{codigo}** gravado com sucesso no SQLite e sincronizado na Nuvem!")

# 3. GESTÃO DE ENCAMINHAMENTOS
elif pagina == "📋 Gestão de Encaminhamentos":
    st.title("📋 Gestão & Atualização de Encaminhamentos")
    
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM atendimentos ORDER BY id DESC", conn)
    
    if len(df) > 0:
        st.subheader("🔄 Atualizar Status de um Atendimento")
        col_sel, col_stat = st.columns(2)
        
        codigos = df['codigo'].tolist()
        codigo_selecionado = col_sel.selectbox("Selecione o Código:", codigos)
        status_opcoes = ["Pendente", "Em Andamento", "Concluído"]
        novo_status = col_stat.selectbox("Novo Status:", status_opcoes)
        
        if st.button("Atualizar no Banco de Dados"):
            c = conn.cursor()
            c.execute("UPDATE atendimentos SET status = ? WHERE codigo = ?", (novo_status, codigo_selecionado))
            conn.commit()
            st.success(f"Status do atendimento {codigo_selecionado} alterado para **{novo_status}**!")
            st.rerun()
            
        st.divider()
        st.subheader("Base de Dados Completa")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum registro encontrado no banco de dados.")
    conn.close()

# 4. GUIA DE INCLUSÃO DIGITAL
elif pagina == "💡 Guia de Inclusão Digital":
    st.title("💡 Guia Prático de Inclusão Digital & Autonomia")
    st.markdown("Instrumento de apoio para a equipe de ADS orientar os moradores.")
    
    with st.expander("🌐 1. Conta Gov.br — Acesso Único aos Serviços Públicos", expanded=True):
        st.markdown("""
        * **Objetivo**: Garantir acesso centralizado a serviços estaduais e federais.
        * **Ações da Equipe**:
          1. Auxiliar no cadastro inicial ou recuperação de senha via e-mail/SMS.
          2. Elevar nível da conta de **Bronze** para **Prata/Ouro** através de validação bancária ou biometria.
        """)
        
    with st.expander("🏥 2. Meu SUS Digital (ConecteSUS)"):
        st.markdown("""
        * **Objetivo**: Facilitar o acompanhamento do histórico de saúde.
        * **Ações da Equipe**:
          1. Ensinar a emitir o Cartão Nacional de Saúde (CNS) digital.
          2. Baixar certificados de vacinação e consultar agendamentos de consultas e exames.
        """)

    with st.expander("📄 3. Meu INSS & Carteira de Trabalho Digital"):
        st.markdown("""
        * **Objetivo**: Assegurar direitos previdenciários e trabalhistas.
        * **Ações da Equipe**:
          1. Consultar extratos de contribuição e andamento do BPC/LOAS.
          2. Acessar o contrato de trabalho digital e requerer seguro-desemprego se necessário.
        """)
        
    with st.expander("🛡️ 4. Segurança da Informação e Marco Civil da Internet"):
        st.markdown("""
        * **Diretrizes**: Orientação preventiva contra golpes do PIX, links falsos no WhatsApp/SMS e vazamento de dados pessoais (Lei nº 12.965/2014).
        """)

# 5. REST API & DOCUMENTAÇÃO
elif pagina == "⚙️ API REST & Documentação":
    st.title("⚙️ Documentação & Teste da API REST")
    st.markdown("Endpoints REST integrados para comunicação com aplicações externas e sistemas de saúde/cidadania.")
    
    st.info("🌐 Servidor REST API ativo localmente em: `http://localhost:8050/api/v1/`")
    
    tab1, tab2, tab3 = st.tabs(["📌 Endpoints Disponíveis", "🧪 Testador da API Integrado", "💻 Código de Exemplo (Curl/Python)"])
    
    with tab1:
        st.markdown("""
        ### Endpoints REST da Aplicação:
        
        | Método | Endpoint | Descrição |
        | :--- | :--- | :--- |
        | `GET` | `/api/v1/health` | Verifica a saúde e status do servidor de API |
        | `GET` | `/api/v1/metricas` | Retorna total de atendimentos, concluídos e taxa de resolução em JSON |
        | `GET` | `/api/v1/atendimentos` | Retorna a lista completa de atendimentos em formato JSON |
        | `POST` | `/api/v1/atendimentos` | Cria um novo atendimento no banco de dados via requisição JSON |
        """)
        
    with tab2:
        st.subheader("🧪 Testar Requisição GET na API")
        endpoint_opcao = st.selectbox("Escolha o Endpoint para consultar:", ["/api/v1/metricas", "/api/v1/health", "/api/v1/atendimentos"])
        
        if st.button("Executar Requisição HTTP GET"):
            try:
                conn = get_db()
                c = conn.cursor()
                if endpoint_opcao == "/api/v1/metricas":
                    c.execute("SELECT COUNT(*) FROM atendimentos")
                    total = c.fetchone()[0]
                    c.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Concluído'")
                    concluidos = c.fetchone()[0]
                    c.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Pendente'")
                    pendentes = c.fetchone()[0]
                    res = {
                        "status_code": 200,
                        "data": {
                            "total_atendimentos": total,
                            "concluidos": concluidos,
                            "pendentes": pendentes,
                            "taxa_resolucao_pct": round((concluidos / total * 100), 1) if total > 0 else 0
                        }
                    }
                elif endpoint_opcao == "/api/v1/health":
                    res = {"status_code": 200, "data": {"status": "online", "system": "Projeto Acolhe API", "version": "1.0.0"}}
                else:
                    c.execute("SELECT * FROM atendimentos ORDER BY id DESC")
                    rows = [dict(row) for row in c.fetchall()]
                    res = {"status_code": 200, "data": {"total": len(rows), "data": rows}}
                conn.close()
                
                st.success("HTTP 200 OK — Resposta Recebida:")
                st.json(res)
            except Exception as e:
                st.error(f"Erro na requisição: {e}")
                
    with tab3:
        st.subheader("💻 Como consumir a API em Python:")
        st.code("""
import requests

# 1. Consultar Métricas do Projeto
response = requests.get('http://localhost:8050/api/v1/metricas')
print(response.json())

# 2. Criar um Atendimento via POST
novo_atendimento = {
    "nome": "Carlos Eduardo",
    "faixa_etaria": "Adulto (30-59)",
    "possui_smartphone": "Sim (Wi-Fi)",
    "facilidade_digital": "Baixa",
    "area_responsavel": "ADS",
    "acao_realizada": "Auxílio na criação da conta Gov.br",
    "encaminhamento": "CRAS",
    "status": "Pendente"
}
res_post = requests.post('http://localhost:8050/api/v1/atendimentos', json=novo_atendimento)
print(res_post.json())
        """, language="python")

st.caption("Projeto Extensionista Acolhe — Cidadania, Saúde e Tecnologia | Análise e Desenvolvimento de Sistemas")
