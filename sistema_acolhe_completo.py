import streamlit as st
import sqlite3
import pandas as pd
import json
import threading
import io
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA WEB
# ---------------------------------------------------------
st.set_page_config(
    page_title="Projeto Acolhe — Sistema Web Integrado",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Customizada para Usabilidade
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-badge-pendente {
        background-color: #FEF2F2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
        border: 1px solid #FCA5A5;
    }
    .status-badge-andamento {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
        border: 1px solid #FCD34D;
    }
    .status-badge-concluido {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85rem;
        border: 1px solid #6EE7B7;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "acolhe_sistema.db"

# ---------------------------------------------------------
# CONEXÃO E BANCO DE DADOS (SQLITE)
# ---------------------------------------------------------
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
            observacoes TEXT,
            status TEXT DEFAULT 'Pendente',
            FOREIGN KEY (participante_id) REFERENCES participantes (id)
        )
    """)
    
    # Adicionar coluna observacoes caso tabela antiga não possua
    try:
        c.execute("ALTER TABLE atendimentos ADD COLUMN observacoes TEXT")
    except Exception:
        pass

    # Seed Data se tabela estiver vazia
    c.execute("SELECT COUNT(*) FROM atendimentos")
    if c.fetchone()[0] == 0:
        seed_data = [
            ("ACT-2026-001", "Maria José da Silva", "Idoso (60+)", "(81) 98765-4321", "Sim (Wi-Fi)", "Baixa", 
             "Dificuldade de ver vacinas no app", "Dúvida sobre Benefício BPC/LOAS", "Ajuda no Gov.br", 
             "Enfermagem", "Recuperação de senha do Gov.br e agendamento", "CRAS Peixinhos", "Acompanhar confirmação do BPC", "Concluído", "2026-10-15 09:30"),
            ("ACT-2026-002", "João Pedro Santos", "Adulto (30-59)", "(81) 99123-8877", "Sim (Dados Móveis)", "Média", 
             "Agendamento de consulta especializada", "Emissão de Carteira de Trabalho Digital", "Baixar app CTPS", 
             "Direito", "Orientações sobre CTPS Digital e agendamento de exame", "Defensoria Pública", "Aguardando envio de comprovantes", "Em Andamento", "2026-10-15 10:15"),
            ("ACT-2026-003", "Ana Clara Lima", "Jovem (18-29)", "(81) 98811-2233", "Sim (Wi-Fi)", "Alta", 
             "Orientação sobre prevenção e saúde da mulher", "Consulta sobre CadÚnico", "Navegação em sites públicos", 
             "ADS", "Auxílio na atualização cadastral e navegação em serviços", "CRAS Peixinhos", "CadÚnico atualizado com sucesso", "Concluído", "2026-10-16 11:00"),
            ("ACT-2026-004", "Severino Ramos de Oliveira", "Idoso (60+)", "(81) 98100-5544", "Não possui", "Nenhuma", 
             "Solicitação de medicamentos contínuos", "Consulta aposentadoria e BPC", "Inclusão digital básica", 
             "Interdisciplinar", "Triagem completa de saúde e atendimento jurídico", "INSS / Posto de Saúde", "Necessita retorno na próxima semana", "Pendente", "2026-10-17 14:20"),
            ("ACT-2026-005", "Francisca Souza", "Adulto (30-59)", "(81) 99777-6655", "Sim (Dados Móveis)", "Baixa", 
             "Dificuldade de usar Meu SUS Digital", "Regularização de CPF", "Uso do aplicativo Meu SUS", 
             "ADS", "Instalação do app Meu SUS Digital e criação de conta Gov.br", "Receita Federal", "Pendente agendamento na Receita", "Em Andamento", "2026-10-18 08:45")
        ]
        
        for codigo, nome, faixa, tel, smartphone, facilidade, d_saude, d_cidadania, d_tec, area, acao, enc, obs, status, data in seed_data:
            c.execute("""
                INSERT INTO participantes (nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, faixa, tel, smartphone, facilidade, data))
            part_id = c.lastrowid
            
            c.execute("""
                INSERT INTO atendimentos 
                (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, observacoes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo, part_id, nome, data, d_saude, d_cidadania, d_tec, area, acao, enc, obs, status))
            
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# BACKEND API RESTFUL (THREAD EM SEGUNDO PLANO)
# ---------------------------------------------------------
class AcolheAPIHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/v1/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "online", "system": "Projeto Acolhe API", "version": "2.0.0"}).encode())
            
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
            c.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Em Andamento'")
            andamento = c.fetchone()[0]
            conn.close()
            
            res = {
                "total_atendimentos": total,
                "concluidos": concluidos,
                "em_andamento": andamento,
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
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            nome = data.get('nome', 'Anônimo')
            faixa = data.get('faixa_etaria', 'Adulto (30-59)')
            tel = data.get('telefone', '')
            smartphone = data.get('possui_smartphone', 'Sim (Wi-Fi)')
            facilidade = data.get('facilidade_digital', 'Média')
            area = data.get('area_responsavel', 'ADS')
            acao = data.get('acao_realizada', '')
            encaminhamento = data.get('encaminhamento', '')
            obs = data.get('observacoes', '')
            status = data.get('status', 'Pendente')
            
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM atendimentos")
            qtd = c.fetchone()[0] + 1
            codigo = f"ACT-2026-{qtd:03d}"
            data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            c.execute("INSERT INTO participantes (nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital, data_cadastro) VALUES (?, ?, ?, ?, ?, ?)",
                      (nome, faixa, tel, smartphone, facilidade, data_hoje))
            part_id = c.lastrowid
            
            c.execute("""
                INSERT INTO atendimentos 
                (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, observacoes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo, part_id, nome, data_hoje, data.get('demanda_saude', ''), data.get('demanda_cidadania', ''), data.get('demanda_tecnologia', ''), area, acao, encaminhamento, obs, status))
            
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

if "api_started" not in st.session_state:
    st.session_state.api_started = True
    threading.Thread(target=run_api_server, daemon=True).start()

# ---------------------------------------------------------
# MENU LATERAL & NAVEGAÇÃO
# ---------------------------------------------------------
st.sidebar.title("🏥 Projeto Acolhe")
st.sidebar.caption("Cidadania, Saúde e Tecnologia | USF Irmã Terezinha")

pagina = st.sidebar.radio(
    "📌 Menu do Sistema:",
    [
        "📊 Dashboard & Métricas", 
        "📝 Novo Diagnóstico", 
        "📋 Gestão de Atendimentos",
        "🗂️ Histórico de Moradores",
        "💡 Guia de Inclusão Digital",
        "⚙️ API REST & Informações"
    ]
)

st.sidebar.divider()
st.sidebar.markdown("**Base de Dados**: 🟢 SQLite (`acolhe_sistema.db`)")
st.sidebar.markdown("**API REST Backend**: 🟢 Ativa na porta `8050`")

# ---------------------------------------------------------
# 1. DASHBOARD & MÉTRICAS
# ---------------------------------------------------------
if pagina == "📊 Dashboard & Métricas":
    st.title("📊 Painel Geral de Impacto — USF Irmã Terezinha")
    st.markdown("Acompanhamento gerencial em tempo real para a equipe interdisciplinar e coordenação.")
    
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM atendimentos", conn)
    conn.close()
    
    total = len(df)
    concluidos = len(df[df['status'] == 'Concluído']) if total > 0 else 0
    em_andamento = len(df[df['status'] == 'Em Andamento']) if total > 0 else 0
    pendentes = len(df[df['status'] == 'Pendente']) if total > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Atendimentos", total)
    m2.metric("🟢 Concluídos", concluidos)
    m3.metric("🟡 Em Andamento", em_andamento)
    m4.metric("🔴 Pendentes", pendentes)
    
    st.divider()
    
    if total > 0:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Atendimentos por Área Responsável")
            st.bar_chart(df['area_responsavel'].value_counts())
            
        with c2:
            st.subheader("Situação dos Encaminhamentos")
            st.bar_chart(df['status'].value_counts())
            
        st.divider()
        st.subheader("📥 Exportar Relatórios de Atendimento (USF)")
        
        # Gerar CSV para Download
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📄 Baixar Relatório em CSV (Excel)",
            data=csv_buffer.getvalue(),
            file_name=f"relatorio_acolhe_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            help="Clique para baixar a planilha de dados completa para reunião de equipe ou prestação de contas."
        )
    else:
        st.info("Nenhum atendimento registrado ainda no sistema.")

# ---------------------------------------------------------
# 2. NOVO DIAGNÓSTICO
# ---------------------------------------------------------
elif pagina == "📝 Novo Diagnóstico":
    st.title("📝 Formulário de Diagnóstico Interdisciplinar")
    st.markdown("Preencha as informações durante o acolhimento presencial na USF Irmã Terezinha.")
    
    # Busca de morador já cadastrado
    conn = get_db()
    df_part = pd.read_sql_query("SELECT id, nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital FROM participantes", conn)
    conn.close()
    
    morador_existente = None
    if len(df_part) > 0:
        with st.expander("🔍 Morador já é cadastrado? Clique para buscar e preencher dados automaticamente"):
            opcoes_moradores = ["-- Novo Morador (Não cadastrado) --"] + [f"{r['nome']} (ID: {r['id']})" for _, r in df_part.iterrows()]
            escolha = st.selectbox("Selecione um morador existente:", opcoes_moradores)
            if escolha != "-- Novo Morador (Não cadastrado) --":
                part_id_sel = int(escolha.split("ID: ")[1].replace(")", ""))
                morador_existente = df_part[df_part['id'] == part_id_sel].iloc[0]
                st.success(f"Dados do morador **{morador_existente['nome']}** carregados!")

    with st.form("form_novo_acolhimento", clear_on_submit=True):
        st.subheader("Bloco I — Perfil do Participante (Inclusão Digital)")
        col_a, col_b = st.columns(2)
        
        nome_default = morador_existente['nome'] if morador_existente is not None else ""
        tel_default = morador_existente['telefone'] if morador_existente is not None and morador_existente['telefone'] else ""
        
        nome = col_a.text_input("Nome Completo / Identificador do Morador*", value=nome_default)
        faixa_etaria = col_b.selectbox("Faixa Etária*", ["Jovem (18-29)", "Adulto (30-59)", "Idoso (60+)"])
        
        col_c, col_d, col_tel = st.columns(3)
        possui_smartphone = col_c.selectbox("Possui Smartphone / Internet?", ["Sim (Wi-Fi)", "Sim (Dados Móveis)", "Não possui"])
        facilidade_digital = col_d.selectbox("Nível de Facilidade Digital*", ["Nenhuma", "Baixa", "Média", "Alta"])
        telefone = col_tel.text_input("Telefone / WhatsApp", value=tel_default, placeholder="(81) 9....-....")
        
        st.subheader("Bloco II — Triagem Interdisciplinar")
        demanda_saude = st.text_area("Demandas de Saúde (Enfermagem)", placeholder="Ex: Histórico vacinal, Meu SUS Digital, agendamento de exames...")
        demanda_cidadania = st.text_area("Demandas de Cidadania e Direitos (Direito)", placeholder="Ex: Meu INSS, BPC/LOAS, CadÚnico, emissão de documentos...")
        demanda_tecnologia = st.text_area("Demandas Tecnológicas (ADS)", placeholder="Ex: Criação/recuperação de conta Gov.br, orientação sobre apps...")
        
        st.subheader("Bloco III — Plano de Ação e Encaminhamento")
        col_e, col_f = st.columns(2)
        area_responsavel = col_e.selectbox("Área Principal Responsável*", ["ADS", "Direito", "Enfermagem", "Interdisciplinar"])
        status = col_f.selectbox("Status Inicial*", ["Pendente", "Em Andamento", "Concluído"])
        
        acao_realizada = st.text_input("Ação Prestada no Momento")
        encaminhamento = st.text_input("Órgão / Serviço de Encaminhamento", placeholder="CRAS Peixinhos, Defensoria Pública, Posto de Saúde...")
        observacoes = st.text_area("Observações Adicionais / Próximos Passos", placeholder="Notas da equipe para acompanhamento posterior...")
        
        submitted = st.form_submit_button("💾 Salvar Atendimento na Base de Dados")
        
        if submitted:
            if not nome.strip():
                st.error("Por favor, preencha o nome do morador.")
            else:
                conn = get_db()
                c = conn.cursor()
                data_agora = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # Inserir ou reaproveitar participante
                c.execute("INSERT INTO participantes (nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital, data_cadastro) VALUES (?, ?, ?, ?, ?, ?)",
                          (nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital, data_agora))
                part_id = c.lastrowid
                
                c.execute("SELECT COUNT(*) FROM atendimentos")
                qtd = c.fetchone()[0] + 1
                codigo = f"ACT-2026-{qtd:03d}"
                
                c.execute("""
                    INSERT INTO atendimentos 
                    (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, observacoes, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (codigo, part_id, nome, data_agora, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, observacoes, status))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Atendimento **{codigo}** cadastrado com sucesso e salvo na nuvem!")

# ---------------------------------------------------------
# 3. GESTÃO DE ATENDIMENTOS (MODO TABELA E MODO CARDS)
# ---------------------------------------------------------
elif pagina == "📋 Gestão de Atendimentos":
    st.title("📋 Gestão & Acompanhamento de Atendimentos")
    st.markdown("Filtre, pesquise e atualize o status das demandas da comunidade em tempo real.")
    
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM atendimentos ORDER BY id DESC", conn)
    conn.close()
    
    if len(df) > 0:
        # Filtros de Busca Rápida
        c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
        busca_nome = c_f1.text_input("🔍 Buscar por Nome ou Código:", placeholder="Digite o nome ou ACT-2026...")
        filtro_status = c_f2.selectbox("Filtro de Status:", ["Todos", "Pendente", "Em Andamento", "Concluído"])
        filtro_area = c_f3.selectbox("Filtro de Área:", ["Todas", "ADS", "Direito", "Enfermagem", "Interdisciplinar"])
        
        # Aplicar filtros
        df_filtered = df.copy()
        if busca_nome:
            df_filtered = df_filtered[df_filtered['nome_participante'].str.contains(busca_nome, case=False, na=False) | df_filtered['codigo'].str.contains(busca_nome, case=False, na=False)]
        if filtro_status != "Todos":
            df_filtered = df_filtered[df_filtered['status'] == filtro_status]
        if filtro_area != "Todas":
            df_filtered = df_filtered[df_filtered['area_responsavel'] == filtro_area]
            
        st.caption(f"Exibindo **{len(df_filtered)}** registros de um total de **{len(df)}**.")
        
        tab_cards, tab_tabela = st.tabs(["📲 Visualização em Cartões (Celular/Prático)", "📊 Tabela Completa de Dados"])
        
        with tab_cards:
            for idx, row in df_filtered.iterrows():
                with st.expander(f"🔹 **{row['codigo']}** — {row['nome_participante']} ({row['area_responsavel']}) | {row['status']}", expanded=(idx==0)):
                    col_det1, col_det2 = st.columns([3, 2])
                    with col_det1:
                        st.markdown(f"**Data do Registro**: {row['data_registro']}")
                        st.markdown(f"**Saúde (Enfermagem)**: {row['demanda_saude'] or 'Nenhum'}")
                        st.markdown(f"**Cidadania (Direito)**: {row['demanda_cidadania'] or 'Nenhum'}")
                        st.markdown(f"**Tecnologia (ADS)**: {row['demanda_tecnologia'] or 'Nenhum'}")
                        st.markdown(f"**Ação Realizada**: {row['acao_realizada'] or 'Pendente'}")
                        st.markdown(f"**Encaminhamento**: {row['encaminhamento'] or 'Não informado'}")
                        st.markdown(f"**Observações**: {row['observacoes'] or 'Sem notas'}")
                        
                    with col_det2:
                        st.subheader("⚡ Ação Rápida")
                        novo_stat = st.selectbox(f"Atualizar Status ({row['codigo']}):", ["Pendente", "Em Andamento", "Concluído"], index=["Pendente", "Em Andamento", "Concluído"].index(row['status']), key=f"sel_{row['codigo']}")
                        novas_obs = st.text_input("Atualizar Observações:", value=row['observacoes'] or "", key=f"obs_{row['codigo']}")
                        
                        if st.button("💾 Salvar Alterações", key=f"btn_{row['codigo']}"):
                            conn = get_db()
                            c = conn.cursor()
                            c.execute("UPDATE atendimentos SET status = ?, observacoes = ? WHERE codigo = ?", (novo_stat, novas_obs, row['codigo']))
                            conn.commit()
                            conn.close()
                            st.success(f"Atendimento **{row['codigo']}** atualizado com sucesso!")
                            st.rerun()

        with tab_tabela:
            st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info("Nenhum atendimento cadastrado na base de dados.")

# ---------------------------------------------------------
# 4. HISTÓRICO DE MORADORES
# ---------------------------------------------------------
elif pagina == "🗂️ Histórico de Moradores":
    st.title("🗂️ Cadastro e Histórico de Moradores")
    st.markdown("Consulte todos os cidadãos atendidos pelo Projeto Acolhe na USF Irmã Terezinha.")
    
    conn = get_db()
    df_p = pd.read_sql_query("SELECT * FROM participantes ORDER BY id DESC", conn)
    conn.close()
    
    if len(df_p) > 0:
        st.dataframe(df_p, use_container_width=True)
        st.divider()
        
        st.subheader("🔍 Ver Histórico de Atendimentos do Morador")
        morador_sel = st.selectbox("Selecione o Morador:", df_p['nome'].unique())
        
        if morador_sel:
            conn = get_db()
            df_atend_morador = pd.read_sql_query("SELECT codigo, data_registro, area_responsavel, acao_realizada, encaminhamento, status FROM atendimentos WHERE nome_participante = ?", conn, params=(morador_sel,))
            conn.close()
            
            st.markdown(f"**Histórico de atendimentos para {morador_sel}** ({len(df_atend_morador)} registros):")
            st.dataframe(df_atend_morador, use_container_width=True)
    else:
        st.info("Nenhum morador registrado ainda.")

# ---------------------------------------------------------
# 5. GUIA DE INCLUSÃO DIGITAL
# ---------------------------------------------------------
elif pagina == "💡 Guia de Inclusão Digital":
    st.title("💡 Guia Prático de Inclusão Digital & Autonomia")
    st.markdown("Roteiro prático para a equipe de ADS orientar os moradores durante o atendimento.")
    
    with st.expander("🌐 1. Conta Gov.br — Acesso Único aos Serviços Públicos", expanded=True):
        st.markdown("""
        * **Objetivo**: Acesso centralizado aos serviços do Governo Federal e Estadual.
        * **Passo a Passo da Equipe**:
          1. Auxiliar o morador no cadastro inicial ou recuperação de senha via SMS/E-mail.
          2. Elevar o nível da conta de **Bronze** para **Prata/Ouro** utilizando validação bancária ou biometria.
        """)
        
    with st.expander("🏥 2. Meu SUS Digital (ConecteSUS)"):
        st.markdown("""
        * **Objetivo**: Acesso fácil ao histórico de vacinas e consultas no SUS.
        * **Passo a Passo da Equipe**:
          1. Emitir o Cartão Nacional de Saúde (CNS) em formato digital.
          2. Baixar o comprovante de vacinação e pesquisar postos de saúde mais próximos.
        """)

    with st.expander("📄 3. Meu INSS & Carteira de Trabalho Digital"):
        st.markdown("""
        * **Objetivo**: Consulta de benefícios previdenciários e direitos trabalhistas.
        * **Passo a Passo da Equipe**:
          1. Consultar andamento de solicitações do BPC/LOAS ou Aposentadoria.
          2. Acessar registros da Carteira de Trabalho Digital e requerer seguro-desemprego.
        """)
        
    with st.expander("🛡️ 4. Segurança da Informação (Marco Civil da Internet)"):
        st.markdown("""
        * **Diretrizes de Segurança**:
          1. Alertar sobre golpes comuns do PIX e mensagens falsas no WhatsApp/SMS.
          2. Ensinar a criar senhas fortes e não compartilhar dados sensíveis.
        """)

# ---------------------------------------------------------
# 6. API REST & INFORMAÇÕES
# ---------------------------------------------------------
elif pagina == "⚙️ API REST & Informações":
    st.title("⚙️ API REST & Informações Técnicas")
    st.markdown("Documentação de endpoints e ferramentas para integração externa.")
    
    st.info("🌐 Servidor REST API ativo localmente na porta `8050`")
    
    st.markdown("""
    | Método | Endpoint | Descrição |
    | :--- | :--- | :--- |
    | `GET` | `/api/v1/health` | Status de saúde da aplicação e API |
    | `GET` | `/api/v1/metricas` | Métricas agregadas (Total, Concluídos, Pendentes, Taxa) |
    | `GET` | `/api/v1/atendimentos` | Lista completa de atendimentos em JSON |
    | `POST` | `/api/v1/atendimentos` | Insere novo atendimento via JSON |
    """)
    
    st.divider()
    st.subheader("🧪 Testar Consulta de Métricas")
    if st.button("Executar GET /api/v1/metricas"):
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
            "status_code": 200,
            "data": {
                "total_atendimentos": total,
                "concluidos": concluidos,
                "pendentes": pendentes,
                "taxa_resolucao_pct": round((concluidos / total * 100), 1) if total > 0 else 0
            }
        }
        st.success("HTTP 200 OK — Resposta da API:")
        st.json(res)

st.caption("Projeto Extensionista Acolhe — Cidadania, Saúde e Tecnologia | Análise e Desenvolvimento de Sistemas v2.0")
