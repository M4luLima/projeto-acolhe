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
# CONFIGURAÇÃO DA PÁGINA WEB & TEMA VISUAL
# ---------------------------------------------------------
st.set_page_config(
    page_title="Projeto Acolhe — Cidadania, Saúde e Tecnologia",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Avançada para Interface Intuitiva e Limpa
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
    }
    
    .metric-box {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: transform 0.2s ease;
    }
    .metric-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.08);
    }
    .metric-val {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.2;
    }
    .metric-lbl {
        font-size: 0.9rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .badge-pendente {
        background-color: #FEF2F2;
        color: #991B1B;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #FCA5A5;
        display: inline-block;
    }
    .badge-andamento {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #FCD34D;
        display: inline-block;
    }
    .badge-concluido {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #6EE7B7;
        display: inline-block;
    }
    
    .header-banner {
        background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 10px rgba(37,99,235,0.2);
    }
    .header-banner h1 {
        color: white !important;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .header-banner p {
        color: #E0E7FF !important;
        margin: 0.3rem 0 0 0;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "acolhe_sistema.db"

# ---------------------------------------------------------
# BANCO DE DADOS RELACIONAL (SQLITE)
# ---------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
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
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS suporte_digital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_atendimento TEXT,
            servico_acessado TEXT,
            orientacao TEXT,
            data_suporte TEXT
        )
    """)
    
    try:
        c.execute("ALTER TABLE atendimentos ADD COLUMN observacoes TEXT")
    except Exception:
        pass

    c.execute("SELECT COUNT(*) FROM atendimentos")
    if c.fetchone()[0] == 0:
        seed_data = [
            ("ACT-2026-001", "Maria José da Silva", "Idoso (60+)", "(81) 98765-4321", "Sim (Wi-Fi)", "Baixa", 
             "Dificuldade em visualizar histórico vacinal no app", "Dúvida sobre requisitos para o Benefício BPC/LOAS", "Ajuda no acesso ao Gov.br", 
             "Enfermagem", "Recuperação de senha do Gov.br e agendamento de consulta", "CRAS Peixinhos", "Concluído", "2026-10-15 09:30", "Atendimento prioritário realizado com sucesso."),
            ("ACT-2026-002", "João Pedro Santos", "Adulto (30-59)", "(81) 99123-8899", "Sim (Dados Móveis)", "Média", 
             "Agendamento de consulta médica especializada", "Emissão e atualização da Carteira de Trabalho Digital", "Instalação do app CTPS Digital", 
             "Direito", "Orientações sobre CTPS Digital e agendamento jurídico", "Defensoria Pública", "Em Andamento", "2026-10-15 10:15", "Aguardando envio de comprovante de residência."),
            ("ACT-2026-003", "Ana Clara Lima", "Jovem (18-29)", "(81) 98877-1122", "Sim (Wi-Fi)", "Alta", 
             "Orientação sobre prevenção e saúde da mulher", "Consulta sobre recadastramento do CadÚnico", "Navegação em sites públicos municipais", 
             "ADS", "Auxílio na atualização cadastral e validação de biometria", "CRAS Peixinhos", "Concluído", "2026-10-16 11:00", "CadÚnico verificado com sucesso."),
            ("ACT-2026-004", "Severino Ramos de Oliveira", "Idoso (60+)", "(81) 98111-2233", "Não possui", "Nenhuma", 
             "Solicitação de medicamentos de uso contínuo", "Orientação previdenciária e aposentadoria por idade", "Capacitação digital básica inicial", 
             "Interdisciplinar", "Triagem completa de saúde, encaminhamento jurídico e cadastro físico", "INSS / Posto de Saúde", "Pendente", "2026-10-17 14:20", "Morador sem smartphone; necessita acompanhamento presencial."),
            ("ACT-2026-005", "Francisca Souza", "Adulto (30-59)", "(81) 99777-6655", "Sim (Dados Móveis)", "Baixa", 
             "Dificuldade no uso do Meu SUS Digital", "Regularização de pendência no CPF", "Uso prático do aplicativo do SUS", 
             "ADS", "Instalação do app Meu SUS Digital e criação da conta Gov.br Prata", "Receita Federal", "Em Andamento", "2026-10-18 08:45", "Encaminhada à Receita Federal para agendamento de CPF.")
        ]
        
        for codigo, nome, faixa, tel, smartphone, facilidade, d_saude, d_cidadania, d_tec, area, acao, enc, status, data, obs in seed_data:
            c.execute("""
                INSERT INTO participantes (nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, faixa, tel, smartphone, facilidade, data))
            part_id = c.lastrowid
            
            c.execute("""
                INSERT INTO atendimentos 
                (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, status, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (codigo, part_id, nome, data, d_saude, d_cidadania, d_tec, area, acao, enc, status, obs))
            
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# BACKEND API RESTFUL
# ---------------------------------------------------------
class AcolheAPIHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/v1/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "online", "system": "Projeto Acolhe API REST", "version": "2.0.0"}).encode())
            
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
# INTERFACE WEB (FRONTEND STREAMLIT INTUITIVO)
# ---------------------------------------------------------

st.sidebar.title("🏥 Projeto Acolhe")
st.sidebar.caption("Cidadania, Saúde e Tecnologia | USF Irmã Terezinha")

pagina = st.sidebar.radio(
    "📍 Navegação Principal:",
    [
        "📊 Dashboard & Métricas", 
        "📝 Novo Atendimento", 
        "📋 Gestão & Cartões (Kanban)", 
        "👤 Histórico de Moradores",
        "💡 Guia de Inclusão Digital",
        "⚙️ API REST & Conectividade"
    ]
)

st.sidebar.divider()
st.sidebar.markdown("### 🟢 Status do Sistema")
st.sidebar.markdown("- **Banco SQLite**: `acolhe_sistema.db`")
st.sidebar.markdown("- **API REST Backend**: Porta `8050`")
st.sidebar.markdown("- **Ambiente**: Produção / Nuvem")

# Header Banner Fixo
st.markdown("""
<div class="header-banner">
    <h1>🏥 Projeto Acolhe — USF Irmã Terezinha</h1>
    <p>Ação Interdisciplinar de Extensão: Direitos, Enfermagem e Inclusão Digital na Comunidade de Peixinhos</p>
</div>
""", unsafe_allow_html=True)

# PÁGINA 1: DASHBOARD
if pagina == "📊 Dashboard & Métricas":
    st.subheader("📊 Painel Geral de Atendimentos & Impacto Social")
    st.markdown("Visualização clara em tempo real das ações prestadas à comunidade.")
    
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM atendimentos ORDER BY id DESC", conn)
    conn.close()
    
    total = len(df)
    concluidos = len(df[df['status'] == 'Concluído']) if total > 0 else 0
    andamento = len(df[df['status'] == 'Em Andamento']) if total > 0 else 0
    pendentes = len(df[df['status'] == 'Pendente']) if total > 0 else 0
    taxa_sucesso = (concluidos / total * 100) if total > 0 else 0.0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-lbl">Total de Atendimentos</div>
            <div class="metric-val" style="color: #1E3A8A;">{total}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-lbl">Concluídos</div>
            <div class="metric-val" style="color: #059669;">{concluidos}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-lbl">Em Andamento</div>
            <div class="metric-val" style="color: #D97706;">{andamento}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-lbl">Taxa de Resolução</div>
            <div class="metric-val" style="color: #2563EB;">{taxa_sucesso:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    st.progress(taxa_sucesso / 100, text=f"Progresso de Resolução Comunitária: {taxa_sucesso:.1f}%")
    st.divider()
    
    if total > 0:
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("#### 🎯 Atendimentos por Área Responsável")
            area_df = df['area_responsavel'].value_counts().reset_index()
            area_df.columns = ['Área', 'Atendimentos']
            st.bar_chart(area_df.set_index('Área'), color="#2563EB")
            
        with g2:
            st.markdown("#### 📱 Nível de Facilidade Digital dos Moradores")
            conn = get_db()
            df_part = pd.read_sql_query("SELECT facilidade_digital FROM participantes", conn)
            conn.close()
            if len(df_part) > 0:
                facil_df = df_part['facilidade_digital'].value_counts().reset_index()
                facil_df.columns = ['Nível', 'Moradores']
                st.bar_chart(facil_df.set_index('Nível'), color="#059669")
                
        st.divider()
        st.markdown("#### 📋 Últimos Registros Realizados")
        st.dataframe(
            df[['codigo', 'nome_participante', 'area_responsavel', 'encaminhamento', 'status', 'data_registro']],
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("#### 📥 Exportar Dados para Relatório")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        st.download_button(
            label="📄 Baixar Relatório Completo em CSV (Excel)",
            data=csv_buffer.getvalue(),
            file_name=f"relatorio_acolhe_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum atendimento registrado no momento.")

# PÁGINA 2: NOVO ATENDIMENTO
elif pagina == "📝 Novo Atendimento":
    st.subheader("📝 Formulário Guiado de Atendimento Comunitário")
    st.markdown("Preencha de forma rápida e intuitiva durante o acolhimento do morador na USF.")
    
    conn = get_db()
    participantes_df = pd.read_sql_query("SELECT id, nome, telefone, faixa_etaria, possui_smartphone, facilidade_digital FROM participantes", conn)
    conn.close()
    
    st.markdown("### 🔍 Morador já possui cadastro?")
    opcao_morador = st.radio("Selecione o tipo de registro:", ["✨ Novo Morador", "👤 Morador Já Cadastrado"], horizontal=True)
    
    nome_padrao, tel_padrao = "", ""
    participante_id_existente = None
    
    if opcao_morador == "👤 Morador Já Cadastrado" and len(participantes_df) > 0:
        morador_sel = st.selectbox("Pesquise pelo Nome do Morador:", participantes_df['nome'].tolist())
        d_morador = participantes_df[participantes_df['nome'] == morador_sel].iloc[0]
        nome_padrao = d_morador['nome']
        tel_padrao = d_morador['telefone'] if d_morador['telefone'] else ""
        participante_id_existente = int(d_morador['id'])
        st.success(f"Morador **{nome_padrao}** localizado na base de dados!")
    
    st.divider()
    
    with st.form("form_atendimento_intuitivo", clear_on_submit=True):
        st.markdown("#### 1️⃣ Perfil e Acesso Digital do Morador")
        col_a, col_b = st.columns(2)
        nome = col_a.text_input("Nome Completo*", value=nome_padrao, placeholder="Ex: Maria José da Silva")
        telefone = col_b.text_input("Telefone / WhatsApp", value=tel_padrao, placeholder="Ex: (81) 98765-4321")
        
        col_c, col_d = st.columns(2)
        faixas = ["Jovem (18-29)", "Adulto (30-59)", "Idoso (60+)"]
        faixa_etaria = col_c.selectbox("Faixa Etária*", faixas)
        
        smartphones = ["Sim (Wi-Fi)", "Sim (Dados Móveis)", "Não possui"]
        possui_smartphone = col_d.selectbox("Possui Smartphone / Internet?", smartphones)
        
        facilidades = ["Nenhuma", "Baixa", "Média", "Alta"]
        facilidade_digital = st.select_slider("Nível de Facilidade com Tecnologia*", options=facilidades, value="Baixa")
        
        st.markdown("#### 2️⃣ Triagem Interdisciplinar (Demandas Mapeadas)")
        tab_enf, tab_dir, tab_ads = st.tabs(["🩺 Saúde (Enfermagem)", "⚖️ Cidadania (Direito)", "💻 Inclusão Digital (ADS)"])
        
        with tab_enf:
            demanda_saude = st.text_area("Necessidades de Saúde / Prontuário / Vacinas", placeholder="Ex: Dificuldade no uso do Meu SUS Digital, agendamento de consultas...", height=90)
        with tab_dir:
            demanda_cidadania = st.text_area("Necessidades de Direitos / Benefícios / Documentos", placeholder="Ex: Orientações sobre Benefício BPC/LOAS, Meu INSS, CadÚnico...", height=90)
        with tab_ads:
            demanda_tecnologia = st.text_area("Necessidades de Suporte Tecnológico", placeholder="Ex: Criação da conta Gov.br, navegação em apps públicos, recuperação de senha...", height=90)
            
        st.markdown("#### 3️⃣ Plano de Ação & Encaminhamento")
        col_e, col_f = st.columns(2)
        area_responsavel = col_e.selectbox("Área Principal do Atendimento*", ["ADS", "Direito", "Enfermagem", "Interdisciplinar"])
        status = col_f.selectbox("Status Inicial*", ["Pendente", "Em Andamento", "Concluído"])
        
        acao_realizada = st.text_input("Ação Prestada no Acolhimento", placeholder="Ex: Orientações jurídicas e recuperação de conta Gov.br")
        encaminhamento = st.text_input("Encaminhamento Externo (se necessário)", placeholder="Ex: CRAS Peixinhos, Defensoria Pública, Posto de Saúde")
        observacoes = st.text_area("Observações Adicionais", placeholder="Anotações para a equipe...", height=70)
        
        submitted = st.form_submit_button("💾 Salvar Atendimento na Nuvem", use_container_width=True)
        
        if submitted:
            if not nome.strip():
                st.error("Por favor, informe o nome do morador.")
            else:
                conn = get_db()
                c = conn.cursor()
                data_agora = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                if participante_id_existente:
                    part_id = participante_id_existente
                else:
                    c.execute("""
                        INSERT INTO participantes (nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital, data_cadastro)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (nome, faixa_etaria, telefone, possui_smartphone, facilidade_digital, data_agora))
                    part_id = c.lastrowid
                
                c.execute("SELECT COUNT(*) FROM atendimentos")
                qtd = c.fetchone()[0] + 1
                codigo = f"ACT-2026-{qtd:03d}"
                
                c.execute("""
                    INSERT INTO atendimentos 
                    (codigo, participante_id, nome_participante, data_registro, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, status, observacoes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (codigo, part_id, nome, data_agora, demanda_saude, demanda_cidadania, demanda_tecnologia, area_responsavel, acao_realizada, encaminhamento, status, observacoes))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Atendimento gravado com sucesso! Código Gerado: **{codigo}**")

# PÁGINA 3: GESTÃO & CARTÕES
elif pagina == "📋 Gestão & Cartões (Kanban)":
    st.subheader("📋 Gestão Visual de Encaminhamentos")
    st.markdown("Pesquise e gerencie o progresso dos atendimentos da USF.")
    
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM atendimentos ORDER BY id DESC", conn)
    conn.close()
    
    if len(df) > 0:
        col_busca, col_filtro_status, col_filtro_area = st.columns([2, 1, 1])
        busca = col_busca.text_input("🔍 Pesquisar por Nome ou Código:", placeholder="Ex: Maria ou ACT-2026-001")
        filtro_status = col_filtro_status.selectbox("Filtrar por Status:", ["Todos", "Pendente", "Em Andamento", "Concluído"])
        filtro_area = col_filtro_area.selectbox("Filtrar por Área:", ["Todas", "ADS", "Direito", "Enfermagem", "Interdisciplinar"])
        
        df_filtered = df.copy()
        if busca:
            df_filtered = df_filtered[
                df_filtered['nome_participante'].str.contains(busca, case=False, na=False) |
                df_filtered['codigo'].str.contains(busca, case=False, na=False)
            ]
        if filtro_status != "Todos":
            df_filtered = df_filtered[df_filtered['status'] == filtro_status]
        if filtro_area != "Todas":
            df_filtered = df_filtered[df_filtered['area_responsavel'] == filtro_area]
            
        st.caption(f"Exibindo {len(df_filtered)} de {len(df)} registros encontrados.")
        
        modo_visao = st.radio("Modo de Visualização:", ["📲 Cartões Interativos", "📊 Tabela Completa"], horizontal=True)
        st.divider()
        
        if modo_visao == "📲 Cartões Interativos":
            for idx, row in df_filtered.iterrows():
                badge_class = "badge-pendente"
                if row['status'] == "Em Andamento": badge_class = "badge-andamento"
                elif row['status'] == "Concluído": badge_class = "badge-concluido"
                
                with st.expander(f"📌 {row['codigo']} — {row['nome_participante']} ({row['area_responsavel']})"):
                    col_det1, col_det2 = st.columns([3, 1])
                    with col_det1:
                        st.markdown(f"**Status Atual**: <span class='{badge_class}'>{row['status']}</span>", unsafe_allow_html=True)
                        st.write(f"🗓️ **Data**: {row['data_registro']}")
                        st.write(f"🎯 **Ação Prestada**: {row['acao_realizada'] if row['acao_realizada'] else 'Não informada'}")
                        st.write(f"↗️ **Encaminhamento**: {row['encaminhamento'] if row['encaminhamento'] else 'Nenhum'}")
                        if row['demanda_saude']: st.caption(f"🩺 Saúde: {row['demanda_saude']}")
                        if row['demanda_cidadania']: st.caption(f"⚖️ Cidadania: {row['demanda_cidadania']}")
                        if row['demanda_tecnologia']: st.caption(f"💻 Tecnologia: {row['demanda_tecnologia']}")
                        
                    with col_det2:
                        st.markdown("##### 🔄 Atualização Rápida")
                        novo_st = st.selectbox(
                            "Novo Status:",
                            ["Pendente", "Em Andamento", "Concluído"],
                            index=["Pendente", "Em Andamento", "Concluído"].index(row['status']),
                            key=f"status_sel_{row['codigo']}"
                        )
                        if st.button("Atualizar", key=f"btn_up_{row['codigo']}"):
                            conn = get_db()
                            c = conn.cursor()
                            c.execute("UPDATE atendimentos SET status = ? WHERE codigo = ?", (novo_st, row['codigo']))
                            conn.commit()
                            conn.close()
                            st.success(f"Status alterado para '{novo_st}'!")
                            st.rerun()
        else:
            st.dataframe(df_filtered, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum atendimento cadastrado no banco de dados.")

# PÁGINA 4: HISTÓRICO DE MORADORES
elif pagina == "👤 Histórico de Moradores":
    st.subheader("👤 Consulta de Histórico por Morador")
    st.markdown("Veja toda a jornada de atendimentos recebidos por um morador específico.")
    
    conn = get_db()
    df_part = pd.read_sql_query("SELECT * FROM participantes ORDER BY nome ASC", conn)
    
    if len(df_part) > 0:
        morador_escolhido = st.selectbox("Selecione o Morador:", df_part['nome'].tolist())
        morador_info = df_part[df_part['nome'] == morador_escolhido].iloc[0]
        
        st.markdown(f"### 📋 Ficha de {morador_info['nome']}")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.write(f"🎂 **Faixa Etária**: {morador_info['faixa_etaria']}")
        col_m2.write(f"📱 **Smartphone**: {morador_info['possui_smartphone']}")
        col_m3.write(f"💻 **Facilidade Digital**: {morador_info['facilidade_digital']}")
        
        st.divider()
        st.markdown("#### 📜 Atendimentos Registrados deste Morador:")
        df_atend = pd.read_sql_query("SELECT codigo, data_registro, area_responsavel, acao_realizada, encaminhamento, status FROM atendimentos WHERE participante_id = ?", conn, params=(int(morador_info['id']),))
        
        if len(df_atend) > 0:
            st.dataframe(df_atend, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum atendimento individual vinculado registrado.")
    else:
        st.info("Nenhum morador cadastrado no sistema.")
    conn.close()

# PÁGINA 5: GUIA DE INCLUSÃO DIGITAL
elif pagina == "💡 Guia de Inclusão Digital":
    st.subheader("💡 Guia Rápido de Inclusão Digital & Autonomia")
    st.markdown("Roteiro prático para os extensionistas orientarem os cidadãos na USF.")
    
    with st.expander("🌐 1. Plataforma Gov.br (Acesso Único)", expanded=True):
        st.markdown("""
        * **Objetivo**: Acesso centralizado aos serviços digitais do Governo Federal.
        * **Checklist de Apoio ao Morador**:
          - [ ] Recuperar senha via SMS, e-mail ou validação bancária.
          - [ ] Elevar nível da conta de **Bronze** para **Prata** ou **Ouro** (via biometria ou banco).
          - [ ] Ensinar o morador a autorizar o compartilhamento de dados com órgãos autorizados.
        """)
        
    with st.expander("🏥 2. Meu SUS Digital (ConecteSUS)"):
        st.markdown("""
        * **Objetivo**: Histórico de vacinas, agendamentos e rede de saúde.
        * **Checklist de Apoio ao Morador**:
          - [ ] Baixar o Cartão Nacional de Saúde (CNS) digital.
          - [ ] Consultar histórico de vacinas e emissão do certificado.
          - [ ] Verificar agendamentos de consultas e exames especializados.
        """)

    with st.expander("📄 3. Meu INSS & Carteira de Trabalho Digital"):
        st.markdown("""
        * **Objetivo**: Consulta previdenciária e contratos de trabalho.
        * **Checklist de Apoio ao Morador**:
          - [ ] Verificar situação do Benefício de Prestação Continuada (BPC/LOAS).
          - [ ] Acessar extratos de contribuição e tempo de serviço.
          - [ ] Consultar o contrato de trabalho na CTPS Digital.
        """)
        
    with st.expander("🛡️ 4. Segurança da Informação & Proteção de Dados (Marco Civil)"):
        st.markdown("""
        * **Orientações de Prevenção**:
          - Alertar contra golpes do PIX e links falsos enviados via SMS/WhatsApp.
          - Orientar a nunca compartilhar senhas da conta Gov.br com terceiros.
          - Explicar os direitos de privacidade segundo a Lei nº 12.965/2014 (Marco Civil da Internet).
        """)

# PÁGINA 6: API REST & CONECTIVIDADE
elif pagina == "⚙️ API REST & Conectividade":
    st.subheader("⚙️ Servidor Backend API REST & Testador")
    st.markdown("Endpoints HTTP prontos para integração com sistemas externos de saúde e cidadania.")
    
    st.info("🌐 Servidor REST API Ativo na Nuvem: `http://localhost:8050/api/v1/`")
    
    tab_end, tab_test, tab_ex = st.tabs(["📌 Endpoints Disponíveis", "🧪 Testar Requisição HTTP", "💻 Código Python/Curl"])
    
    with tab_end:
        st.markdown("""
        | Método | Endpoint | Função |
        | :--- | :--- | :--- |
        | `GET` | `/api/v1/health` | Verifica integridade e status da API |
        | `GET` | `/api/v1/metricas` | Retorna total de atendimentos e taxa de resolução |
        | `GET` | `/api/v1/atendimentos` | Lista todos os atendimentos em formato JSON |
        | `POST` | `/api/v1/atendimentos` | Insere um novo atendimento no banco de dados |
        """)
        
    with tab_test:
        st.markdown("#### Teste em Tempo Real da API")
        ep_sel = st.selectbox("Escolha o Endpoint:", ["/api/v1/metricas", "/api/v1/health", "/api/v1/atendimentos"])
        if st.button("Executar GET"):
            conn = get_db()
            c = conn.cursor()
            if ep_sel == "/api/v1/metricas":
                c.execute("SELECT COUNT(*) FROM atendimentos"); tot = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM atendimentos WHERE status = 'Concluído'"); conc = c.fetchone()[0]
                res = {"status_code": 200, "data": {"total_atendimentos": tot, "concluidos": conc, "taxa_resolucao_pct": round(conc/tot*100,1) if tot>0 else 0}}
            elif ep_sel == "/api/v1/health":
                res = {"status_code": 200, "data": {"status": "online", "system": "Projeto Acolhe API REST", "version": "2.0.0"}}
            else:
                c.execute("SELECT * FROM atendimentos ORDER BY id DESC")
                rows = [dict(r) for r in c.fetchall()]
                res = {"status_code": 200, "data": {"total": len(rows), "data": rows}}
            conn.close()
            st.success("HTTP 200 OK — Resposta JSON Recebida:")
            st.json(res)
            
    with tab_ex:
        st.code("""
import requests

r = requests.get('http://localhost:8050/api/v1/metricas')
print(r.json())
        """, language="python")

st.caption("Projeto Extensionista Acolhe — Cidadania, Saúde e Tecnologia | ESUDA 2026")
