import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Sistema de Recomendación Explicable",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "primary":   "#1D9E75",
    "secondary": "#534AB7",
    "accent":    "#EF9F27",
    "danger":    "#D85A30",
    "neutral":   "#B4B2A9",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.main-header{font-family:'DM Serif Display',serif;font-size:2.2rem;color:#E8E6E0;letter-spacing:-0.02em;line-height:1.1;margin-bottom:0.2rem;}
.main-sub{font-size:0.88rem;color:#8A8880;letter-spacing:0.05em;text-transform:uppercase;font-weight:500;}
.rec-card{background:linear-gradient(135deg,#1E2130 0%,#181C28 100%);border:1px solid #2A2F45;border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.65rem;}
.rec-card:hover{border-color:#1D9E75;}
.rec-rank{font-family:'DM Mono',monospace;font-size:0.72rem;color:#1D9E75;font-weight:500;text-transform:uppercase;letter-spacing:0.1em;}
.rec-title{font-size:0.93rem;font-weight:600;color:#E8E6E0;margin:0.2rem 0 0.4rem;line-height:1.3;}
.rec-brand{font-size:0.78rem;color:#8A8880;margin-bottom:0.4rem;}
.reason-pill{display:inline-block;background:rgba(29,158,117,0.12);color:#1D9E75;border-radius:20px;padding:0.12rem 0.55rem;font-size:0.73rem;font-weight:500;margin:0.12rem 0.08rem;}
.kpi-box{background:#1E2130;border:1px solid #2A2F45;border-radius:10px;padding:0.9rem 1.1rem;text-align:center;}
.kpi-value{font-family:'DM Serif Display',serif;font-size:1.9rem;color:#1D9E75;line-height:1;margin-bottom:0.15rem;}
.kpi-label{font-size:0.75rem;color:#8A8880;text-transform:uppercase;letter-spacing:0.06em;}
section[data-testid="stSidebar"]{background:#151822;border-right:1px solid #2A2F45;}
.stTabs [data-baseweb="tab-list"]{background:#1E2130;border-radius:8px;padding:3px;gap:2px;}
.stTabs [data-baseweb="tab"]{border-radius:6px;color:#8A8880;font-weight:500;}
.stTabs [aria-selected="true"]{background:#1D9E75 !important;color:white !important;}
hr{border-color:#2A2F45;}
.profile-card{background:#1E2130;border:1px solid #2A2F45;border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.75rem;}
.stat-chip{display:inline-block;background:rgba(29,158,117,0.1);border:1px solid rgba(29,158,117,0.25);color:#1D9E75;border-radius:8px;padding:0.3rem 0.7rem;font-size:0.76rem;font-weight:500;margin:0.15rem 0.1rem;}
.item-stat{font-size:0.72rem;color:#8A8880;margin-top:0.35rem;}
.popularity-bar{background:#2A2F45;border-radius:3px;height:5px;margin-top:4px;}
.popularity-fill{height:5px;border-radius:3px;}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────
def cnt(x):
    if pd.isna(x) or str(x).strip() == '': return 0
    return len(str(x).split(' · '))

def badge(level):
    cfg = {
        'No_privada':       ('rgba(29,158,117,0.15);color:#1D9E75', '🟢 Baja'),
        'Privada_moderada': ('rgba(239,159,39,0.15);color:#EF9F27',  '🟡 Moderada'),
        'Privada_sensible': ('rgba(216,90,48,0.15);color:#D85A30',   '🔴 Alta'),
    }
    bg, txt = cfg.get(level, ('rgba(180,178,169,0.15);color:#B4B2A9', '❓'))
    return f'<span style="display:inline-block;padding:0.18rem 0.65rem;border-radius:20px;font-size:0.76rem;font-weight:600;background:{bg}">{txt}</span>'

def apply_privacy(explain, level):
    if pd.isna(explain) or str(explain).strip() == '': return ''
    prefs = {
        'No_privada':       dict(brand=True,  cat=True,  hist=True,  temp=True,  rec=True),
        'Privada_moderada': dict(brand=True,  cat=True,  hist=False, temp=True,  rec=True),
        'Privada_sensible': dict(brand=False, cat=False, hist=False, temp=True,  rec=False),
    }
    p = prefs.get(level, prefs['No_privada'])
    keep = []
    for part in str(explain).split(' · '):
        if 'Marca' in part and not p['brand']: continue
        if any(k in part for k in ['Categoría','Macro','afinidades']) and not p['cat']: continue
        if 'junto' in part and not p['hist']: continue
        if 'estacionalidad' in part and not p['temp']: continue
        if any(k in part for k in ['recientes','movimiento']) and not p['rec']: continue
        keep.append(part)
    return ' · '.join(keep)

def pbase():
    return dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='DM Sans', color='#8A8880', size=11))

# ── CARGA ─────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load(f, fb=None):
    for fn in ([f] + ([fb] if fb else [])):
        if fn and Path(fn).exists():
            return pd.read_parquet(fn) if fn.endswith('.parquet') else pd.read_csv(fn)
    return None

with st.spinner("Cargando datos..."):
    recs      = load('app_recs_final.parquet', 'app_recs_final.csv')
    perfiles  = load('app_perfiles.parquet',   'app_perfiles.csv')
    catalogo  = load('app_catalogo.parquet',   'app_catalogo.csv')
    shap_g    = load('xai_shap_global_importance.csv')
    shap_priv = load('xai_shap_by_privacy.csv')
    shap_sl   = load('xai_shap_slice_by_rank.csv')
    calib     = load('xai_score_calibration.csv')
    master    = load('xai_master_findings_table.csv')
    corr_df   = load('xai_shap_signal_correlation.csv')
    # Archivos nuevos de mejoras
    hte_df    = load('hte_experimento.csv')
    fair_df   = load('fairness_catalogo.csv')
    cov_df    = load('cobertura_sistema.csv')
    ild_df    = load('ild_analisis.csv')
    raz_df    = load('razones_por_categoria.csv')
    cf_df     = load('contrafactual_analisis.csv')
    if corr_df is not None and corr_df.columns[0] != corr_df.index[0]:
        corr_df = corr_df.set_index(corr_df.columns[0])

    # Índices para búsqueda rápida
    cat_idx  = catalogo.set_index('asin') if catalogo is not None and 'asin' in catalogo.columns else None
    perf_idx = perfiles.set_index('Survey ResponseID') if perfiles is not None and 'Survey ResponseID' in perfiles.columns else None

# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 0.5rem">
      <div style="font-family:'DM Serif Display',serif;font-size:1.15rem;color:#E8E6E0;line-height:1.25">
        Sistema de<br>Recomendación<br><span style="color:#1D9E75">Explicable</span></div>
      <div style="font-size:0.68rem;color:#8A8880;margin-top:0.4rem;text-transform:uppercase;letter-spacing:0.08em">
        Tesis de Maestría · Franco Yasnig</div>
    </div><hr>""", unsafe_allow_html=True)

    pagina = st.radio("Nav", [
        "🏠  Dashboard de Usuario",
        "🔒  Simulador de Privacidad",
        "📊  Análisis XAI Global",
        "🧪  Experimento & Hallazgos",
        "⚖️  Comparar Usuarios",
        "🔎  Buscador de Ítems",
        "📈  Hallazgos 14·15·16",
        "🎯  Hallazgos 17·18",
        "🔮  Hallazgos 19",
        "⚖️  Legal-by-Design",
    ], label_visibility="collapsed")

    st.markdown("""<hr>
    <div style="font-size:0.7rem;color:#8A8880;line-height:1.8">
      <b style="color:#E8E6E0">Dataset:</b> Amazon Purchases<br>
      <b style="color:#E8E6E0">Usuarios:</b> 5,027<br>
      <b style="color:#E8E6E0">Items:</b> 939,083<br>
      <b style="color:#E8E6E0">Modelo:</b> Híbrido Co-compra<br>
      <b style="color:#E8E6E0">NDCG@10:</b> 0.050<br>
      <b style="color:#E8E6E0">XAI:</b> SHAP + LIME ρ=1.00
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# P1 — DASHBOARD DE USUARIO
# ══════════════════════════════════════════════════════════
if "Dashboard" in pagina:
    st.markdown('<div class="main-header">Dashboard de Usuario</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Recomendaciones personalizadas con explicaciones XAI</div>', unsafe_allow_html=True)
    st.write("")
    st.info("📖 **Cómo usar esta pantalla:** Seleccioná cualquiera de los 3,217 usuarios del estudio. Vas a ver su perfil de compras, las métricas del sistema de recomendación, y los productos recomendados con las razones por las que el modelo los eligió. Las etiquetas verdes en cada producto son las **explicaciones XAI** — el núcleo de esta tesis.")

    if recs is None:
        st.error("No se encontró `app_recs_final.parquet`. Corré el Bloque 5 primero.")
        st.stop()

    users = sorted(recs['Survey ResponseID'].dropna().unique().tolist())
    uid = st.selectbox("Seleccioná un usuario", users,
                       format_func=lambda x: f"Usuario ···{str(x)[-8:]}")

    ur = recs[recs['Survey ResponseID']==uid].copy()
    ur['nr'] = ur['explain'].apply(cnt)
    if 'score_display' in ur.columns:
        ur = ur.sort_values('score_display', ascending=False)

    pl = ur['privacy_level'].iloc[0] if 'privacy_level' in ur.columns else 'Unknown'
    eg = ur['exp_group'].iloc[0] if 'exp_group' in ur.columns else 'na'

    # ── PERFIL DEL CLIENTE ────────────────────────────────
    st.write("")
    st.markdown("**👤 Perfil del cliente**")
    st.caption("Datos históricos del usuario en el dataset Amazon Purchases 2018–2024. La fila superior muestra volumen y gasto. La fila inferior muestra comportamiento: cuándo compró por última vez, si es fiel a una sola marca, y si concentra sus compras en pocas categorías. Los chips de colores muestran sus categorías y marca favoritas con la cantidad de ítems comprados.")

    perf_row = perf_idx.loc[uid] if (perf_idx is not None and uid in perf_idx.index) else None

    def pget(col, default='—'):
        if perf_row is None: return default
        v = perf_row[col] if col in perf_row.index else default
        return v if pd.notna(v) else default

    # Columnas exactas de app_perfiles.parquet
    n_purch     = pget('total_products')
    n_orders    = pget('num_orders')
    total_spend = pget('total_spent')
    avg_price   = pget('avg_ticket')
    recency     = pget('recency_days')
    cat_top1    = pget('category_top1')
    cat_top2    = pget('category_top2')
    cat_top1_q  = pget('category_top1_qty')
    cat_top2_q  = pget('category_top2_qty')
    brand_top1  = pget('top_brand')
    brand_loyal = pget('is_loyal_to_brand')
    cat_spec    = pget('is_category_specialist')
    cat_div     = pget('category_diversity')

    def fmt_num(v, prefix='', suffix='', decimals=0):
        try:
            f = float(v)
            return f"{prefix}{f:,.{decimals}f}{suffix}"
        except: return str(v) if v != '—' else '—'

    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    treated_lbl = " 🧪" if eg == 'treated' else ""
    col_p1.markdown(f'<div class="kpi-box"><div style="margin-bottom:0.3rem">{badge(pl)}</div><div class="kpi-label">Privacidad{treated_lbl}</div></div>', unsafe_allow_html=True)
    col_p2.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.6rem">{fmt_num(n_purch)}</div><div class="kpi-label">Productos comprados</div></div>', unsafe_allow_html=True)
    col_p3.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.6rem">{fmt_num(total_spend,"$")}</div><div class="kpi-label">Gasto total</div></div>', unsafe_allow_html=True)
    col_p4.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.6rem">{fmt_num(avg_price,"$","",2)}</div><div class="kpi-label">Ticket promedio</div></div>', unsafe_allow_html=True)

    # Segunda fila de KPIs
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    col_q1.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.6rem">{fmt_num(n_orders)}</div><div class="kpi-label">Órdenes únicas</div></div>', unsafe_allow_html=True)
    recency_fmt = f"{int(float(recency))} días" if recency != '—' else '—'
    col_q2.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.4rem">{recency_fmt}</div><div class="kpi-label">Última compra</div></div>', unsafe_allow_html=True)
    loyal_txt = "✅ Sí" if str(brand_loyal) in ['True','1','1.0'] else "🔄 No"
    col_q3.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.4rem">{loyal_txt}</div><div class="kpi-label">Leal a marca</div></div>', unsafe_allow_html=True)
    spec_txt = "✅ Sí" if str(cat_spec) in ['True','1','1.0'] else "🔄 No"
    col_q4.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.4rem">{spec_txt}</div><div class="kpi-label">Especialista categoría</div></div>', unsafe_allow_html=True)

    # Chips: categorías y marca
    cat_emoji_map = {'GIFT_CARD':'🎁','ABIS_BOOK':'📚','PET_FOOD':'🐾',
                     'NUTRITIONAL_SUPPLEMENT':'💊','DAIRY_BASED_CHEESE':'🧀',
                     'SCREEN_PROTECTOR':'📱','LAUNDRY_DETERGENT':'🧺',
                     'COMPUTER_COMPONENT':'💻','DOWNLOADABLE_VIDEO_GAME':'🎮',
                     'TOILET_PAPER':'🧻','VEGETABLE':'🥦','BATTERY':'🔋'}
    chips_html = ''
    for cat_v, qty_v in [(cat_top1, cat_top1_q), (cat_top2, cat_top2_q)]:
        if cat_v not in ['—','nan','None'] and str(cat_v).strip():
            emoji = cat_emoji_map.get(str(cat_v), '🛒')
            qty_s = f" · {int(float(qty_v))} items" if qty_v not in ['—','nan','None'] else ''
            chips_html += f'<span class="stat-chip">{emoji} {str(cat_v).replace("_"," ").title()}{qty_s}</span>'
    if brand_top1 not in ['—','nan','None'] and str(brand_top1).strip():
        chips_html += f'<span class="stat-chip">⭐ {brand_top1}</span>'
    if cat_div not in ['—','nan','None']:
        try: chips_html += f'<span class="stat-chip" style="background:rgba(83,74,183,0.12);border-color:rgba(83,74,183,0.3);color:#534AB7">📂 {int(float(cat_div))} categorías distintas</span>'
        except: pass
    if chips_html:
        st.markdown(f"<div style='margin:0.65rem 0 0.75rem'>{chips_html}</div>", unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#2A2F45;margin:0.5rem 0 1rem">', unsafe_allow_html=True)

    # ── RECOMENDACIONES + GRÁFICOS ────────────────────────
    st.markdown('<hr style="border-color:#2A2F45;margin:0.5rem 0 0.75rem">', unsafe_allow_html=True)
    st.caption("📊 **Métricas del sistema para este usuario.** El score máximo es 1.00 cuando el ítem tiene co-compra directa muy fuerte. Las razones promedio indican qué tan explicables son las recomendaciones: más razones = más contexto visible para el usuario.")
    k1,k2,k3,k4 = st.columns(4)
    ms = ur['score_display'].max() if 'score_display' in ur.columns else 0
    for col,val,lbl in [(k1,len(ur),"Recomendaciones"),(k2,f"{ur['nr'].mean():.1f}","Razones promedio"),
                        (k3,f"{(ur['nr']>=1).mean():.0%}","Con ≥1 razón"),(k4,f"{ms:.2f}","Score máximo")]:
        col.markdown(f'<div class="kpi-box"><div class="kpi-value">{val}</div><div class="kpi-label">{lbl}</div></div>', unsafe_allow_html=True)

    st.write("")
    cr, cc = st.columns([3,2])

    with cr:
        st.markdown("**Top recomendaciones**")
        st.caption("Cada card muestra un producto recomendado ordenado por relevancia (score de 0 a 1). Las métricas en gris muestran el desempeño del ítem en el catálogo global. La barra verde indica popularidad relativa respecto al 90% de los productos. Las **etiquetas verdes** son las razones XAI: por qué el modelo eligió ese ítem para este usuario específico.")

        # Percentiles de units_sold del catálogo para normalizar
        units_p90 = None
        if cat_idx is not None and 'units_sold' in cat_idx.columns:
            units_p90 = float(cat_idx['units_sold'].quantile(0.9))

        for i,(_, row) in enumerate(ur.head(10).iterrows(), 1):
            title   = str(row.get('title','Sin título'))[:80] if pd.notna(row.get('title')) else 'Sin título'
            brand   = str(row.get('brand','')) if pd.notna(row.get('brand')) else ''
            cat     = str(row.get('category','')) if pd.notna(row.get('category')) else ''
            explain = str(row.get('explain','')) if pd.notna(row.get('explain')) else ''
            score   = f"{row['score_display']:.3f}" if 'score_display' in row and pd.notna(row.get('score_display')) else ''
            asin    = str(row.get('asin','')) if pd.notna(row.get('asin')) else ''

            # Métricas del producto desde el catálogo
            units_sold    = '—'
            repeat_rate   = '—'
            cat_share     = '—'
            pop_pct       = 0
            repeat_pct    = 0

            if cat_idx is not None and asin in cat_idx.index:
                cat_row = cat_idx.loc[asin]
                def cget(col):
                    v = cat_row[col] if col in cat_row.index else None
                    return v if v is not None and pd.notna(v) else None

                us = cget('units_sold')
                rr = cget('repeat_buyer_rate')
                cs = cget('share_of_cat2_revenue')   # columna exacta del catálogo
                nb = cget('num_buyers')
                rev= cget('gross_revenue')
                avg_p = cget('avg_unit_price_weighted')

                if us is not None:
                    us_f = float(us)
                    units_sold = f"{us_f:,.0f}"
                    pop_pct = min(int(us_f / units_p90 * 100), 100) if units_p90 and units_p90 > 0 else 0
                if rr is not None:
                    rr_f = float(rr)
                    repeat_rate = f"{rr_f:.1%}"
                    repeat_pct = min(int(rr_f * 100), 100)
                if cs is not None:
                    cat_share = f"{float(cs):.2%}"
                if nb is not None:
                    units_sold_extra = f"👥 {int(float(nb)):,} compradores únicos"
                else:
                    units_sold_extra = ''

            cat_emoji = cat_emoji_map.get(cat, '🛒')
            score_val = float(score) if score else 0
            bar_pct   = min(int(score_val * 100), 100)
            bar_color = '#1D9E75' if score_val > 0.5 else ('#EF9F27' if score_val > 0.2 else '#534AB7')

            pills = ''.join(f'<span class="reason-pill">{r.strip()[:48]}</span>'
                            for r in explain.split(' · ') if r.strip()) if explain.strip() else \
                    '<span style="font-size:0.78rem;color:#8A8880;font-style:italic">Sin razones visibles</span>'

            # Métricas del producto como mini-stats
            prod_stats = ''
            if units_sold != '—':
                prod_stats += f'<span style="margin-right:1.2rem">📦 <b style="color:#E8E6E0">{units_sold}</b> <span style="color:#8A8880">unidades</span></span>'
            if 'units_sold_extra' in dir() and units_sold_extra:
                prod_stats += f'<span style="margin-right:1.2rem">{units_sold_extra}</span>'
            if repeat_rate != '—':
                prod_stats += f'<span style="margin-right:1.2rem">🔄 <b style="color:#E8E6E0">{repeat_rate}</b> <span style="color:#8A8880">recurrentes</span></span>'
            if cat_share != '—':
                prod_stats += f'<span>📊 <b style="color:#E8E6E0">{cat_share}</b> <span style="color:#8A8880">del revenue de categoría</span></span>'

            # Barra de popularidad
            pop_bar = ''
            if pop_pct > 0:
                pop_color = '#1D9E75' if pop_pct > 66 else ('#EF9F27' if pop_pct > 33 else '#534AB7')
                pop_label = 'Alta' if pop_pct > 66 else ('Media' if pop_pct > 33 else 'Baja')
                pop_bar = f'''<div style="margin-top:0.5rem">
                  <div style="display:flex;justify-content:space-between;font-size:0.68rem;color:#8A8880;margin-bottom:2px">
                    <span>Popularidad en el catálogo</span><span style="color:{pop_color}">{pop_label} ({pop_pct}%)</span>
                  </div>
                  <div class="popularity-bar"><div class="popularity-fill" style="width:{pop_pct}%;background:{pop_color}"></div></div>
                </div>'''

            st.markdown(f"""
            <div class="rec-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div style="flex:1">
                  <div class="rec-rank">#{i} &nbsp;{cat_emoji} {cat.replace('_',' ').title() if cat else ''}</div>
                  <div class="rec-title">{title}</div>
                  <div class="rec-brand">{brand}</div>
                </div>
                <div style="text-align:right;min-width:70px">
                  <div style="font-family:'DM Mono',monospace;font-size:0.85rem;color:#1D9E75;font-weight:500">{score}</div>
                  <div style="font-size:0.65rem;color:#8A8880;margin-bottom:3px">relevancia</div>
                  <div style="background:#2A2F45;border-radius:3px;height:4px;width:60px">
                    <div style="background:{bar_color};height:4px;border-radius:3px;width:{bar_pct}%"></div>
                  </div>
                </div>
              </div>
              {f'<div class="item-stat" style="margin-top:0.45rem">{prod_stats}</div>' if prod_stats else ''}
              {pop_bar}
              <div style="margin-top:0.5rem">{pills}</div>
            </div>""", unsafe_allow_html=True)

    with cc:
        st.markdown("**Señales explicativas usadas**")
        rc = {'Co-compra':0,'Afinidad':0,'Categoría':0,'Estacional.':0,'Popularidad':0,'Repeat':0,'Otras':0}
        for exp in ur['explain'].dropna():
            for pt in str(exp).split(' · '):
                if 'junto' in pt: rc['Co-compra']+=1
                elif 'Marca' in pt: rc['Afinidad']+=1
                elif 'Categoría' in pt or 'Macro' in pt: rc['Categoría']+=1
                elif 'estacionalidad' in pt: rc['Estacional.']+=1
                elif 'popular' in pt or 'frecuentemente' in pt: rc['Popularidad']+=1
                elif 'recurrente' in pt: rc['Repeat']+=1
                else: rc['Otras']+=1
        df_rc = pd.DataFrame({'S':list(rc.keys()),'N':list(rc.values())})
        df_rc = df_rc[df_rc['N']>0].sort_values('N', ascending=True)
        if len(df_rc):
            fig = px.bar(df_rc,x='N',y='S',orientation='h',
                         color_discrete_sequence=[COLORS['primary']],template='plotly_dark')
            fig.update_layout(**pbase(),height=230,showlegend=False,
                              margin=dict(l=0,r=0,t=10,b=0),
                              xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                              yaxis=dict(gridcolor='rgba(0,0,0,0)'))
            st.plotly_chart(fig, use_container_width=True)
        st.caption("Qué tipo de señal usó el modelo para justificar cada recomendación. **Repeat** = ítem comprado frecuentemente por otros. **Co-compra** = se compra junto a otros ítems del historial. **Estacional** = coincide con el patrón de compra por época del año.")

        st.markdown("**Razones por recomendación**")
        st.caption("Distribución de cuántas razones tiene cada ítem recomendado. Más razones = explicación más completa. Un ítem con 0 razones no tiene justificación visible para este perfil de privacidad.")
        rh = ur['nr'].value_counts().sort_index()
        fig2 = px.bar(x=rh.index.astype(str),y=rh.values,
                      color_discrete_sequence=[COLORS['secondary']],template='plotly_dark')
        fig2.update_layout(**pbase(),height=150,showlegend=False,
                           margin=dict(l=0,r=0,t=10,b=0),
                           xaxis=dict(title='N° razones',gridcolor='rgba(0,0,0,0)'),
                           yaxis=dict(gridcolor='rgba(255,255,255,0.05)'))
        st.plotly_chart(fig2, use_container_width=True)

        # Perfil de compras del usuario en gráfico
        if perf_row is not None:
            st.markdown("**Categorías más compradas**")
            st.caption("Historial real del usuario. Permite verificar si las recomendaciones son coherentes con sus preferencias declaradas por comportamiento de compra.")
            cats_user = {}
            for cat_col, qty_col in [('category_top1','category_top1_qty'),
                                      ('category_top2','category_top2_qty')]:
                cv = pget(cat_col)
                qv = pget(qty_col)
                if cv not in ['—','nan','None'] and str(cv).strip():
                    label = str(cv).replace('_',' ').title()[:22]
                    try: cats_user[label] = float(qv)
                    except: cats_user[label] = 1
            if cats_user:
                df_cats = pd.DataFrame({'Cat':list(cats_user.keys()),
                                        'N':list(cats_user.values())})
                df_cats = df_cats.sort_values('N', ascending=True)
                fig3 = px.bar(df_cats, x='N', y='Cat', orientation='h',
                              color_discrete_sequence=[COLORS['accent']],
                              template='plotly_dark')
                fig3.update_layout(**pbase(), height=max(100, len(df_cats)*45),
                                   showlegend=False,
                                   margin=dict(l=0,r=0,t=10,b=0),
                                   xaxis=dict(title='Items comprados',
                                              gridcolor='rgba(255,255,255,0.05)'),
                                   yaxis=dict(gridcolor='rgba(0,0,0,0)'))
                st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════════════════
# P2 — SIMULADOR DE PRIVACIDAD
# ══════════════════════════════════════════════════════════
elif "Simulador" in pagina:
    st.markdown('<div class="main-header">Simulador de Privacidad</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Cambiá el nivel y observá el impacto en las explicaciones</div>', unsafe_allow_html=True)
    st.write("")
    st.info("🔒 **Qué muestra esta pantalla:** El sistema permite tres niveles de privacidad. Al mover el slider, las razones de cada recomendación cambian en tiempo real — algunas desaparecen porque usan datos que el usuario no quiere compartir. Esto demuestra que el sistema es **explicable bajo cualquier restricción de privacidad**, no solo cuando el usuario comparte todo. Los KPIs muestran cuántas razones se pierden al subir la privacidad.")

    if recs is None:
        st.error("No se encontró `app_recs_final.parquet`."); st.stop()

    users = sorted(recs['Survey ResponseID'].dropna().unique().tolist())
    ctrl, sim = st.columns([1,2])

    with ctrl:
        uid2 = st.selectbox("Usuario", users, key='s_uid',
                            format_func=lambda x: f"···{str(x)[-8:]}")
        priv = st.select_slider("Privacidad",
            options=["No_privada","Privada_moderada","Privada_sensible"],
            value="Privada_sensible",
            format_func=lambda x: {"No_privada":"🟢 Baja — muestra todo",
                                    "Privada_moderada":"🟡 Moderada",
                                    "Privada_sensible":"🔴 Alta — oculta historial"}[x])
        st.write("")
        st.markdown(f"""
        <div style="background:#1E2130;border:1px solid #2A2F45;border-radius:10px;padding:1rem">
          <div style="font-size:0.74rem;color:#8A8880;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem">Qué se comparte</div>
          <div style="font-size:0.8rem;line-height:1.9">
            {"✅" if priv=="No_privada" else "❌"} Historial de compras<br>
            {"✅" if priv in ["No_privada","Privada_moderada"] else "❌"} Marca preferida<br>
            {"✅" if priv in ["No_privada","Privada_moderada"] else "❌"} Categoría favorita<br>
            ✅ Señales estacionales<br>
            ✅ Popularidad del ítem<br>
            ✅ Compradores frecuentes
          </div>
        </div>""", unsafe_allow_html=True)

    with sim:
        ur2 = recs[recs['Survey ResponseID']==uid2].copy()
        if 'score_display' in ur2.columns:
            ur2 = ur2.sort_values('score_display', ascending=False)
        ur2 = ur2.head(8)

        src = 'explain_raw' if 'explain_raw' in ur2.columns else 'explain'
        ur2['esim']  = ur2[src].apply(lambda x: apply_privacy(x, priv))
        ur2['nsim']  = ur2['esim'].apply(cnt)
        ur2['norig'] = ur2['explain'].apply(cnt)

        ao, as_ = ur2['norig'].mean(), ur2['nsim'].mean()
        d = as_ - ao
        dc = "#1D9E75" if d>=0 else "#D85A30"

        m1,m2,m3 = st.columns(3)
        m1.markdown(f'<div class="kpi-box"><div class="kpi-value">{ao:.1f}</div><div class="kpi-label">Razones original</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="kpi-box"><div class="kpi-value" style="color:{dc}">{as_:.1f}</div><div class="kpi-label">Razones simulado</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="kpi-box"><div class="kpi-value" style="color:{dc}">{d:+.1f}</div><div class="kpi-label">Diferencia</div></div>', unsafe_allow_html=True)

        st.markdown("**Recomendaciones con el perfil seleccionado**")
        for i,(_, row) in enumerate(ur2.iterrows(), 1):
            title   = str(row.get('title','Sin título'))[:65] if pd.notna(row.get('title')) else 'Sin título'
            explain = str(row.get('esim','')) if pd.notna(row.get('esim')) else ''
            nr      = cnt(explain)
            ind     = "🟢" if nr>=2 else ("🟡" if nr==1 else "🔴")
            pills   = ''.join(f'<span class="reason-pill">{r.strip()[:45]}</span>'
                              for r in explain.split(' · ') if r.strip()) if explain.strip() else \
                      '<span style="font-size:0.76rem;color:#8A8880;font-style:italic">Sin razones visibles</span>'
            st.markdown(f"""
            <div class="rec-card">
              <div style="display:flex;justify-content:space-between">
                <div class="rec-rank">#{i}</div>
                <div style="font-size:0.72rem;color:#8A8880">{ind} {nr} razones</div>
              </div>
              <div class="rec-title" style="margin-top:0.25rem">{title}</div>
              <div style="margin-top:0.3rem">{pills}</div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# P3 — ANÁLISIS XAI GLOBAL
# ══════════════════════════════════════════════════════════
elif "XAI" in pagina:
    st.markdown('<div class="main-header">Análisis XAI Global</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">SHAP + LIME · Importancia de señales · Calibración</div>', unsafe_allow_html=True)
    st.write("")
    st.info("🔬 **Qué muestra esta pantalla:** Análisis global del modelo usando dos métodos de explicabilidad (SHAP y LIME). SHAP mide cuánto contribuye cada señal al score final en promedio. LIME construye modelos locales lineales alrededor de cada predicción. Que ambos métodos coincidan (ρ=1.00) valida que la interpretación es robusta y no depende del método elegido.")

    t1,t2,t3,t4 = st.tabs(["📈 Importancia SHAP","🔗 Correlación señales","📉 Slice por posición","🎯 Calibración"])

    FL = {'pct_shap_S1_copurchase':'Co-compra','pct_shap_S2_affinities':'Afinidad perfil',
          'pct_shap_S3_temporal_eff':'Estacionalidad','pct_shap_S4_recency_item':'Recencia',
          'pct_shap_S5_popularity':'Popularidad',
          'pct_S1_copurchase':'Co-compra','pct_S2_affinities':'Afinidad perfil',
          'pct_S3_temporal_eff':'Estacionalidad','pct_S4_recency_item':'Recencia',
          'pct_S5_popularity':'Popularidad'}

    with t1:
        if shap_g is None:
            st.info("Corré el bloque XAI para generar `xai_shap_global_importance.csv`.")
        else:
            sg = shap_g.sort_values('mean_abs_shap', ascending=True).copy()
            sg['pct'] = sg['mean_abs_shap']/sg['mean_abs_shap'].sum()*100
            c1,c2 = st.columns([3,2])
            with c1:
                st.markdown("**Importancia relativa SHAP vs peso teórico**")
                st.caption("Las barras verdes (SHAP) muestran la importancia *real* medida empíricamente. Las barras grises son los pesos teóricos asignados al diseñar el modelo. Si SHAP > peso teórico, esa señal discrimina más de lo esperado. **Hallazgo clave:** Co-compra tiene peso=40% pero importancia SHAP=64.8% — su alta varianza la hace mucho más discriminante de lo que sugiere el peso.")
                fig = go.Figure()
                fig.add_trace(go.Bar(y=sg['label'],x=sg['pct'],orientation='h',name='SHAP',
                                     marker_color=COLORS['primary'],marker_line_width=0))
                fig.add_trace(go.Bar(y=sg['label'],x=sg['weight']*100,orientation='h',
                                     name='Peso teórico',marker_color='rgba(180,178,169,0.3)',
                                     marker_line_color='rgba(180,178,169,0.6)',marker_line_width=1))
                fig.update_layout(**pbase(),barmode='overlay',height=300,
                                  legend=dict(orientation='h',y=1.1,font=dict(color='#8A8880',size=10)),
                                  xaxis=dict(title='%',gridcolor='rgba(255,255,255,0.05)'),
                                  yaxis=dict(gridcolor='rgba(0,0,0,0)'))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.markdown("**Tabla de importancia**")
                tbl = sg[['label','weight','mean_abs_shap']].copy()
                tbl['Peso'] = (tbl['weight']*100).map('{:.0f}%'.format)
                tbl['SHAP'] = (tbl['mean_abs_shap']/tbl['mean_abs_shap'].sum()*100).map('{:.1f}%'.format)
                tbl = tbl.rename(columns={'label':'Señal'}).drop(columns=['weight','mean_abs_shap'])
                st.dataframe(tbl.sort_values('SHAP',ascending=False), hide_index=True, use_container_width=True)
                st.markdown("""<div style="background:#1E2130;border:1px solid #2A2F45;border-radius:10px;padding:0.85rem;font-size:0.8rem;color:#8A8880;line-height:1.7;margin-top:0.75rem">
                  <b style="color:#1D9E75">ρ SHAP-LIME = 1.000</b><br>
                  Dos métodos XAI independientes, mismo ranking — interpretabilidad robusta y verificable.
                </div>""", unsafe_allow_html=True)

        if shap_priv is not None:
            st.markdown("**Importancia SHAP por grupo de privacidad**")
            pc = [c for c in shap_priv.columns if c.startswith('pct_shap_')]
            if pc:
                dm = shap_priv[['privacy_level']+pc].melt(id_vars='privacy_level',value_vars=pc,var_name='f',value_name='pct')
                dm['f'] = dm['f'].map(FL).fillna(dm['f'])
                dm['pct'] *= 100
                fp = px.bar(dm,x='f',y='pct',color='privacy_level',barmode='group',
                            color_discrete_map={'No_privada':COLORS['primary'],'Privada_moderada':COLORS['accent'],'Privada_sensible':COLORS['danger']},
                            labels={'pct':'SHAP (%)','f':''},template='plotly_dark')
                fp.update_layout(**pbase(),height=270,
                                 legend=dict(title='',orientation='h',y=1.1,font=dict(color='#8A8880',size=10)),
                                 yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),xaxis=dict(gridcolor='rgba(0,0,0,0)'))
                st.plotly_chart(fp, use_container_width=True)
                st.caption("✅ Variación máxima en co-compra: 0.9% — el modelo de scoring es neutral a la privacidad del usuario.")

    with t2:
        if corr_df is None:
            st.info("Corré el bloque XAI para generar `xai_shap_signal_correlation.csv`.")
        else:
            st.markdown("**Correlación Spearman entre SHAP values — ¿señales sustitutos o complementarias?**")
            st.caption("**Cómo leer este gráfico:** Cada celda muestra la correlación entre dos señales. Verde oscuro = alta correlación (se mueven juntas). Amarillo claro = independientes. Rojo = correlación negativa. Si dos señales tienen ρ≈0, capturan dimensiones distintas del comportamiento de compra — son complementarias, no redundantes. **Hallazgo:** 9 de 10 pares son independientes. La única excepción es recencia-popularidad (ρ=0.54), que tiene sentido: ítems populares tienden a haberse vendido recientemente.")
            z = corr_df.values
            fc = go.Figure(go.Heatmap(z=z,x=list(corr_df.columns),y=list(corr_df.index),
                                      colorscale='RdYlGn',zmid=0,zmin=-1,zmax=1,
                                      text=[[f'{v:.2f}' for v in row] for row in z],
                                      texttemplate='%{text}',textfont=dict(size=11)))
            fc.update_layout(**pbase(),height=360,margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fc, use_container_width=True)

    with t3:
        if shap_sl is None:
            st.info("Corré el bloque XAI para generar `xai_shap_slice_by_rank.csv`.")
        else:
            st.markdown("**Importancia SHAP por posición en el ranking — fallback explícito**")
            st.caption("**Cómo leer este gráfico:** El eje X muestra la posición en el ranking (Top 1-3 son los mejores candidatos, Pos 11-20 los más débiles). El eje Y muestra qué porcentaje del score se explica por cada señal. Lo notable: en el Top 1-3, la co-compra explica el 84.6% del score — el sistema usa casi exclusivamente esa señal para los mejores candidatos. A partir de la posición 4, otras señales como afinidad de perfil y popularidad compensan. Esto se llama **fallback explícito**: el modelo usa señales más débiles cuando la co-compra no es suficientemente fuerte.")
            ps = [c for c in shap_sl.columns if c.startswith('pct_')]
            if ps:
                dm2 = shap_sl[['rank_group']+ps].melt(id_vars='rank_group',value_vars=ps,var_name='f',value_name='pct')
                dm2['f'] = dm2['f'].map(FL).fillna(dm2['f'])
                dm2['pct'] *= 100
                fs = px.line(dm2,x='rank_group',y='pct',color='f',markers=True,
                             color_discrete_map={'Co-compra':COLORS['primary'],'Afinidad perfil':COLORS['secondary'],
                                                 'Popularidad':COLORS['accent'],'Estacionalidad':COLORS['neutral'],'Recencia':'#5DCAA5'},
                             labels={'pct':'SHAP (%)','rank_group':'Posición'},template='plotly_dark')
                fs.update_layout(**pbase(),height=350,
                                 legend=dict(title='',orientation='h',y=1.1,font=dict(color='#8A8880',size=10)),
                                 yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),xaxis=dict(gridcolor='rgba(255,255,255,0.05)'))
                st.plotly_chart(fs, use_container_width=True)
                st.caption("Co-compra cae de 84.6% (Top 1-3) a 55.4% (Pos 11-20) — fallback explícito hacia señales de ítem.")

    with t4:
        if calib is None:
            st.info("Corré el bloque XAI para generar `xai_score_calibration.csv`.")
        else:
            st.markdown("**Calibración del score_final — hit rate por decil**")
            st.caption("**Cómo leer este gráfico:** Los 87,526 pares usuario-ítem se dividen en 10 grupos (deciles) ordenados por score. D1 son los ítems con score más bajo, D10 los de score más alto. El eje Y muestra qué porcentaje de esos ítems el usuario *efectivamente compró* después (hit rate). Si el modelo está bien calibrado, el hit rate debe crecer de izquierda a derecha. **Hallazgo:** La correlación es perfecta (ρ=1.00) — cada decil tiene más compras reales que el anterior. D10 tiene 27 veces más hits que D1, lo que valida que el score predice compras reales.")
            cc1,cc2 = st.columns([3,2])
            with cc1:
                clrs = [COLORS['neutral'] if i<5 else COLORS['primary'] for i in range(len(calib))]
                fca = go.Figure()
                fca.add_trace(go.Bar(x=calib['score_decile'],y=calib['hit_rate']*100,
                                     marker_color=clrs,marker_line_width=0,
                                     text=(calib['hit_rate']*100).map('{:.2f}%'.format),
                                     textposition='outside',textfont=dict(color='#8A8880',size=9)))
                fca.add_hline(y=calib['hit_rate'].mean()*100,line_dash='dash',line_color=COLORS['accent'],
                              annotation_text=f"Media: {calib['hit_rate'].mean():.2%}",
                              annotation_font_color=COLORS['accent'])
                fca.update_layout(**pbase(),height=310,showlegend=False,
                                  xaxis=dict(title='Decil de score',gridcolor='rgba(0,0,0,0)'),
                                  yaxis=dict(title='Hit rate (%)',gridcolor='rgba(255,255,255,0.05)'))
                st.plotly_chart(fca, use_container_width=True)
            with cc2:
                d1  = calib[calib['score_decile']=='D1']['hit_rate'].values[0]
                d10 = calib[calib['score_decile']=='D10']['hit_rate'].values[0]
                ratio = round(d10/d1) if d1>0 else 0
                for v,l in [("ρ=1.00","Correlación decil-hit"),(f"{ratio}x","D10 vs D1"),(f"{d10:.2%}","Hit rate D10")]:
                    st.markdown(f'<div class="kpi-box" style="margin-bottom:0.6rem"><div class="kpi-value">{v}</div><div class="kpi-label">{l}</div></div>', unsafe_allow_html=True)
                st.markdown("""<div style="background:#1E2130;border:1px solid #2A2F45;border-radius:10px;padding:0.85rem;font-size:0.79rem;color:#8A8880;margin-top:0.5rem;line-height:1.7">
                  El score predice compras reales de forma monotónica perfecta — <b style="color:#1D9E75">validez externa</b> del modelo.
                </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# P4 — EXPERIMENTO & HALLAZGOS
# ══════════════════════════════════════════════════════════
elif "Experimento" in pagina:
    st.markdown('<div class="main-header">Experimento & Hallazgos</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Random consent · 13 hallazgos XAI documentados</div>', unsafe_allow_html=True)
    st.write("")

    st.write("")
    st.info("🧪 **Qué muestra esta pantalla:** Contiene el experimento causal de consentimiento y el resumen de los 13 hallazgos del análisis XAI. El experimento responde: ¿habilitar el historial de compras en las explicaciones mejora la explicabilidad? La tabla maestra consolida todos los resultados del estudio en un solo lugar.")

    te, th = st.tabs(["🧪 Experimento de Consentimiento","📋 Tabla Maestra XAI"])

    with te:
        st.caption("**Cómo leer este gráfico:** El eje Y muestra el promedio de razones visibles por recomendación (máximo posible: 3). Los cuatro grupos permiten comparar: el grupo Control es el baseline (sin historial), el grupo Tratado recibió el historial habilitado, y los grupos No_privada y Privada_sensible son referencias de los extremos del sistema. Si el tratamiento funciona, el grupo Tratado debería tener más razones que el Control.")
        st.markdown("""<div style="background:#1E2130;border:1px solid #2A2F45;border-radius:10px;padding:1rem;font-size:0.82rem;color:#8A8880;line-height:1.8;margin-bottom:1.25rem">
          <b style="color:#E8E6E0">Diseño:</b> Usuarios con <span style="color:#EF9F27">Privada_moderada</span> asignados aleatoriamente.<br>
          <b style="color:#1D9E75">Tratado</b> (30% · 112 usuarios): historial habilitado en explicaciones.<br>
          <b style="color:#B4B2A9">Control</b> (70% · 263 usuarios): sin historial (baseline).
        </div>""", unsafe_allow_html=True)

        edf = pd.DataFrame({
            'Grupo': ['Control\n(sin historial)','Tratado\n(con historial)','No_privada\n(referencia)','Privada_sensible'],
            'Avg':   [2.95, 2.99, 3.00, 2.32],
            'color': [COLORS['neutral'],COLORS['primary'],COLORS['secondary'],COLORS['danger']],
        })
        fe = go.Figure(go.Bar(x=edf['Grupo'],y=edf['Avg'],marker_color=edf['color'],marker_line_width=0,
                              text=edf['Avg'].map('{:.2f}'.format),textposition='outside',
                              textfont=dict(color='#8A8880',size=11)))
        fe.add_hline(y=3.0,line_dash='dot',line_color='rgba(255,255,255,0.15)',
                     annotation_text='Máximo (3 razones)',annotation_font_color='#8A8880')
        fe.update_layout(**pbase(),height=330,showlegend=False,
                         yaxis=dict(range=[0,3.4],title='Avg razones visibles',gridcolor='rgba(255,255,255,0.05)'),
                         xaxis=dict(gridcolor='rgba(0,0,0,0)',tickangle=-5))
        st.plotly_chart(fe, use_container_width=True)

        e1,e2,e3 = st.columns(3)
        e1.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#EF9F27">+0.04</div><div class="kpi-label">Efecto del consentimiento</div></div>', unsafe_allow_html=True)
        e2.markdown('<div class="kpi-box"><div class="kpi-value">112/375</div><div class="kpi-label">Usuarios tratados</div></div>', unsafe_allow_html=True)
        e3.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#1D9E75">2.55</div><div class="kpi-label">Avg razones global</div></div>', unsafe_allow_html=True)
        st.write("")
        st.caption("El efecto del consentimiento es pequeño (+0.04) porque las señales de ítem compensan la falta de historial — valida el diseño privacy-by-default.")

    with th:
        if master is None:
            st.info("Corré el bloque XAI para generar `xai_master_findings_table.csv`.")
        else:
            st.markdown("**13 hallazgos documentados del análisis XAI**")
            st.caption("Cada card muestra un hallazgo del estudio: el título en blanco describe qué se encontró, el valor en color es el dato numérico exacto, y el texto en gris explica qué implica para la tesis. Los hallazgos están agrupados por categoría: 🎯 señal dominante, ✅ validación del modelo, 🏗️ decisiones de diseño, ⚡ comportamientos emergentes no diseñados, 🛡️ robustez, ⚠️ limitaciones documentadas, y 🔍 anomalías que requieren explicación.")
            icons  = {'Señal dominante':'🎯','Validación':'✅','Diseño':'🏗️',
                      'Comportamiento emergente':'⚡','Robustez':'🛡️','Limitación':'⚠️','Anomalía':'🔍'}
            colors = {'Señal dominante':COLORS['primary'],'Validación':'#27AE60','Diseño':COLORS['secondary'],
                      'Comportamiento emergente':COLORS['accent'],'Robustez':'#5DCAA5',
                      'Limitación':COLORS['danger'],'Anomalía':'#9B59B6'}
            for cat in ['Señal dominante','Validación','Diseño','Comportamiento emergente','Robustez','Limitación','Anomalía']:
                rows = master[master['categoria']==cat]
                if len(rows)==0: continue
                st.markdown(f"**{icons.get(cat,'•')} {cat}**")
                for _,row in rows.iterrows():
                    c = colors.get(cat, COLORS['primary'])
                    st.markdown(f"""
                    <div class="rec-card" style="margin-bottom:0.45rem">
                      <div style="display:flex;gap:1rem;flex-wrap:wrap">
                        <div style="flex:1;min-width:180px">
                          <div style="font-size:0.87rem;font-weight:600;color:#E8E6E0;margin-bottom:0.18rem">{row['hallazgo']}</div>
                          <div style="font-size:0.78rem;color:{c};font-family:'DM Mono',monospace">{row['valor_resultado']}</div>
                        </div>
                        <div style="flex:1.5;min-width:200px;font-size:0.77rem;color:#8A8880;line-height:1.5;padding-top:0.05rem">
                          {row['implicacion_tesis']}
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)
                st.markdown("")

# ══════════════════════════════════════════════════════════
# P5 — COMPARAR USUARIOS
# ══════════════════════════════════════════════════════════
elif "Comparar" in pagina:
    st.markdown('<div class="main-header">Comparación de Usuarios</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Recomendaciones y perfiles de dos usuarios lado a lado</div>', unsafe_allow_html=True)
    st.write("")
    st.info("⚖️ **Qué muestra esta pantalla:** Compará dos usuarios del estudio. El sistema genera recomendaciones y explicaciones distintas según el perfil, el historial y el nivel de privacidad de cada uno.")

    if recs is None:
        st.error("No se encontró app_recs_final.parquet."); st.stop()

    users = sorted(recs['Survey ResponseID'].dropna().unique().tolist())
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        uid_a = st.selectbox("Usuario A", users, key='cmp_a', format_func=lambda x: f"···{str(x)[-8:]}")
    with col_u2:
        uid_b = st.selectbox("Usuario B", users, index=min(1,len(users)-1), key='cmp_b', format_func=lambda x: f"···{str(x)[-8:]}")

    def get_ud(uid):
        ur = recs[recs['Survey ResponseID']==uid].copy()
        ur['nr'] = ur['explain'].apply(cnt)
        if 'score_display' in ur.columns:
            ur = ur.sort_values('score_display', ascending=False)
        pr = perf_idx.loc[uid] if perf_idx is not None and uid in perf_idx.index else None
        return ur, pr

    ur_a, pr_a = get_ud(uid_a)
    ur_b, pr_b = get_ud(uid_b)

    def pg(pr, col, default='—'):
        if pr is None: return default
        v = pr[col] if col in pr.index else default
        return v if pd.notna(v) else default

    def fm(v, prefix='', suffix='', dec=0):
        try: return f"{prefix}{float(v):,.{dec}f}{suffix}"
        except: return str(v) if v != '—' else '—'

    cat_emoji_map = {'GIFT_CARD':'🎁','ABIS_BOOK':'📚','PET_FOOD':'🐾',
                     'NUTRITIONAL_SUPPLEMENT':'💊','DAIRY_BASED_CHEESE':'🧀',
                     'SCREEN_PROTECTOR':'📱','LAUNDRY_DETERGENT':'🧺',
                     'COMPUTER_COMPONENT':'💻','DOWNLOADABLE_VIDEO_GAME':'🎮','BATTERY':'🔋'}

    st.markdown('<hr style="border-color:#2A2F45;margin:0.75rem 0">', unsafe_allow_html=True)
    h1, h2 = st.columns(2)

    for col_s, uid, ur, pr in [(h1,uid_a,ur_a,pr_a),(h2,uid_b,ur_b,pr_b)]:
        with col_s:
            pl = ur['privacy_level'].iloc[0] if 'privacy_level' in ur.columns and len(ur) else 'Unknown'
            eg = ur['exp_group'].iloc[0] if 'exp_group' in ur.columns and len(ur) else 'na'
            treated = " 🧪" if eg=='treated' else ""
            st.markdown(f"**Usuario ···{str(uid)[-8:]}** &nbsp; {badge(pl)}{treated}", unsafe_allow_html=True)
            k1,k2,k3,k4 = st.columns(4)
            for col_k, val, lbl in [
                (k1, fm(pg(pr,'total_products')), "Productos"),
                (k2, fm(pg(pr,'total_spent'),"$"), "Gasto total"),
                (k3, fm(pg(pr,'avg_ticket'),"$","",2), "Ticket prom."),
                (k4, fm(pg(pr,'recency_days'),"","d"), "Última compra"),
            ]:
                col_k.markdown(f'<div class="kpi-box"><div class="kpi-value" style="font-size:1.3rem">{val}</div><div class="kpi-label">{lbl}</div></div>', unsafe_allow_html=True)
            chips = ''
            for cc, qc in [('category_top1','category_top1_qty'),('category_top2','category_top2_qty')]:
                cv = pg(pr,cc); qv = pg(pr,qc)
                if cv not in ['—','nan','None'] and str(cv).strip():
                    e = cat_emoji_map.get(str(cv),'🛒')
                    q = f" · {int(float(qv))}it" if qv not in ['—','nan','None'] else ''
                    chips += f'<span class="stat-chip">{e} {str(cv).replace("_"," ").title()[:18]}{q}</span>'
            bv = pg(pr,'top_brand')
            if bv not in ['—','nan','None'] and str(bv).strip():
                chips += f'<span class="stat-chip">⭐ {bv}</span>'
            if chips:
                st.markdown(f"<div style='margin:0.5rem 0'>{chips}</div>", unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#2A2F45;margin:0.75rem 0">', unsafe_allow_html=True)
    st.markdown("**Top recomendaciones comparadas**")
    st.caption("Observá cómo cambian los ítems, scores y razones según el perfil de cada usuario.")

    col_r1, col_r2 = st.columns(2)
    for col_s, ur in [(col_r1,ur_a),(col_r2,ur_b)]:
        with col_s:
            for i,(_, row) in enumerate(ur.head(6).iterrows(), 1):
                title   = str(row.get('title','Sin título'))[:55] if pd.notna(row.get('title')) else 'Sin título'
                cat     = str(row.get('category','')) if pd.notna(row.get('category')) else ''
                explain = str(row.get('explain','')) if pd.notna(row.get('explain')) else ''
                score   = f"{row['score_display']:.3f}" if 'score_display' in row and pd.notna(row.get('score_display')) else ''
                emoji   = cat_emoji_map.get(cat,'🛒')
                pills   = ''.join(f'<span class="reason-pill">{r.strip()[:40]}</span>'
                                  for r in explain.split(' · ') if r.strip()) if explain.strip() else \
                          '<span style="font-size:0.74rem;color:#8A8880;font-style:italic">Sin razones</span>'
                st.markdown(f"""
                <div class="rec-card">
                  <div style="display:flex;justify-content:space-between">
                    <div class="rec-rank">#{i} {emoji} {cat.replace('_',' ').title()[:20]}</div>
                    <div style="font-family:monospace;font-size:0.82rem;color:#1D9E75">{score}</div>
                  </div>
                  <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin:0.2rem 0 0.35rem;line-height:1.3">{title}</div>
                  <div>{pills}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#2A2F45;margin:0.75rem 0">', unsafe_allow_html=True)
    st.markdown("**Señales explicativas usadas por cada usuario**")

    def get_sigs(ur):
        rc = {'Co-compra':0,'Afinidad':0,'Categoría':0,'Estacional.':0,'Popularidad':0,'Repeat':0,'Otras':0}
        for exp in ur['explain'].dropna():
            for pt in str(exp).split(' · '):
                if 'junto' in pt: rc['Co-compra']+=1
                elif 'Marca' in pt: rc['Afinidad']+=1
                elif 'Categoría' in pt or 'Macro' in pt: rc['Categoría']+=1
                elif 'estacionalidad' in pt: rc['Estacional.']+=1
                elif 'popular' in pt or 'frecuentemente' in pt: rc['Popularidad']+=1
                elif 'recurrente' in pt: rc['Repeat']+=1
                else: rc['Otras']+=1
        total = sum(rc.values()) or 1
        return {k: v/total*100 for k,v in rc.items() if v > 0}

    sa = get_sigs(ur_a); sb = get_sigs(ur_b)
    all_s = sorted(set(list(sa.keys())+list(sb.keys())))
    fig_c = go.Figure()
    fig_c.add_trace(go.Bar(name=f"A ···{str(uid_a)[-8:]}", x=all_s, y=[sa.get(s,0) for s in all_s],
                           marker_color=COLORS['primary'], marker_line_width=0))
    fig_c.add_trace(go.Bar(name=f"B ···{str(uid_b)[-8:]}", x=all_s, y=[sb.get(s,0) for s in all_s],
                           marker_color=COLORS['secondary'], marker_line_width=0))
    fig_c.update_layout(**pbase(), barmode='group', height=260,
                        margin=dict(l=0,r=0,t=10,b=0),
                        legend=dict(orientation='h',y=1.1,font=dict(color='#8A8880',size=10)),
                        yaxis=dict(title='% del total',gridcolor='rgba(255,255,255,0.05)'),
                        xaxis=dict(gridcolor='rgba(0,0,0,0)'))
    st.plotly_chart(fig_c, use_container_width=True)

# ══════════════════════════════════════════════════════════
# P6 — BUSCADOR DE ÍTEMS
# ══════════════════════════════════════════════════════════
elif "Buscador" in pagina:
    st.markdown('<div class="main-header">Buscador de Ítems</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">¿A quién se le recomendó este producto y por qué?</div>', unsafe_allow_html=True)
    st.write("")
    st.info("🔎 **Vista inversa del sistema:** En vez de 'qué le recomiendo a este usuario', respondemos '¿a quién le recomendé este ítem?'. Permite ver el sesgo de popularidad en acción: los ítems más recomendados (gift cards) aparecen para el 27% de usuarios pero con hit rate más bajo que ítems de nicho.")

    if recs is None or catalogo is None:
        st.error("Datos no disponibles."); st.stop()

    search_term = st.text_input("Buscá un producto por nombre o categoría",
                                placeholder="Ej: Gift Card, Echo Dot, PlayStation, Pet Food...")

    if search_term:
        mask = catalogo['title'].str.contains(search_term, case=False, na=False)
        if 'category' in catalogo.columns:
            mask |= catalogo['category'].str.contains(search_term, case=False, na=False)
        results_cat = catalogo[mask][['asin','title','brand','category',
                                      'units_sold','repeat_buyer_rate','num_buyers']].head(30)
        if len(results_cat) == 0:
            st.warning(f"No se encontraron productos con '{search_term}'.")
        else:
            asins_rec = set(recs['asin'].astype(str).str.strip().unique())
            results_cat = results_cat.copy()
            results_cat['asin_str'] = results_cat['asin'].astype(str).str.strip()
            results_with_recs = results_cat[results_cat['asin_str'].isin(asins_rec)]
            st.markdown(f"**{len(results_cat)} productos encontrados** · {len(results_with_recs)} con recomendaciones activas")

            if len(results_with_recs) > 0:
                titles_map = {row['asin_str']: f"{str(row['title'])[:60]} ({row['category']})"
                              for _, row in results_with_recs.iterrows()}
                selected_asin = st.selectbox("Seleccioná un producto",
                                             list(titles_map.keys()),
                                             format_func=lambda x: titles_map.get(x, x))
                if selected_asin:
                    item_recs = recs[recs['asin'].astype(str).str.strip()==selected_asin].copy()
                    item_recs['nr'] = item_recs['explain'].apply(cnt)
                    cat_row = cat_idx.loc[selected_asin] if cat_idx is not None and selected_asin in cat_idx.index else None

                    st.markdown('<hr style="border-color:#2A2F45;margin:0.75rem 0">', unsafe_allow_html=True)
                    k1,k2,k3,k4,k5 = st.columns(5)
                    n_rec = item_recs['Survey ResponseID'].nunique()
                    pct_rec = n_rec / recs['Survey ResponseID'].nunique() * 100
                    avg_sc  = item_recs['score_display'].mean() if 'score_display' in item_recs.columns else 0
                    avg_nr  = item_recs['nr'].mean()
                    k1.markdown(f'<div class="kpi-box"><div class="kpi-value">{n_rec}</div><div class="kpi-label">Usuarios que lo reciben</div></div>', unsafe_allow_html=True)
                    k2.markdown(f'<div class="kpi-box"><div class="kpi-value">{pct_rec:.1f}%</div><div class="kpi-label">% del total</div></div>', unsafe_allow_html=True)
                    k3.markdown(f'<div class="kpi-box"><div class="kpi-value">{avg_sc:.3f}</div><div class="kpi-label">Score promedio</div></div>', unsafe_allow_html=True)
                    k4.markdown(f'<div class="kpi-box"><div class="kpi-value">{avg_nr:.1f}</div><div class="kpi-label">Razones promedio</div></div>', unsafe_allow_html=True)
                    if cat_row is not None:
                        rr = cat_row['repeat_buyer_rate'] if 'repeat_buyer_rate' in cat_row.index else None
                        rr_str = f"{float(rr):.1%}" if rr is not None and pd.notna(rr) else '—'
                        k5.markdown(f'<div class="kpi-box"><div class="kpi-value">{rr_str}</div><div class="kpi-label">Compradores recurrentes</div></div>', unsafe_allow_html=True)

                    col_d, col_r = st.columns(2)
                    with col_d:
                        st.markdown("**Distribución por nivel de privacidad**")
                        if 'privacy_level' in item_recs.columns:
                            pd_dist = item_recs['privacy_level'].value_counts()
                            fig_pd = px.pie(values=pd_dist.values, names=pd_dist.index,
                                            color=pd_dist.index,
                                            color_discrete_map={'No_privada':COLORS['primary'],
                                                                'Privada_moderada':COLORS['accent'],
                                                                'Privada_sensible':COLORS['danger']},
                                            hole=0.4, template='plotly_dark')
                            fig_pd.update_layout(**pbase(), height=240, margin=dict(l=0,r=0,t=10,b=0),
                                                 legend=dict(font=dict(color='#8A8880',size=9)))
                            st.plotly_chart(fig_pd, use_container_width=True)
                    with col_r:
                        st.markdown("**Razones más usadas para este ítem**")
                        reason_counts = {}
                        for exp in item_recs['explain'].dropna():
                            for part in str(exp).split(' · '):
                                p = part.strip()[:50]
                                if p: reason_counts[p] = reason_counts.get(p,0)+1
                        if reason_counts:
                            top_r = sorted(reason_counts.items(), key=lambda x:-x[1])[:7]
                            df_r  = pd.DataFrame(top_r, columns=['Razón','N'])
                            fig_r = px.bar(df_r.sort_values('N'), x='N', y='Razón', orientation='h',
                                           color_discrete_sequence=[COLORS['primary']], template='plotly_dark')
                            fig_r.update_layout(**pbase(), height=240, margin=dict(l=0,r=0,t=10,b=0),
                                               showlegend=False,
                                               xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                                               yaxis=dict(gridcolor='rgba(0,0,0,0)'))
                            st.plotly_chart(fig_r, use_container_width=True)

                    st.markdown("**Muestra de usuarios que reciben esta recomendación**")
                    sample = item_recs[['Survey ResponseID','privacy_level','score_display','nr','explain']].head(10).copy()
                    sample['Usuario']     = sample['Survey ResponseID'].apply(lambda x: f"···{str(x)[-8:]}")
                    sample['Score']       = sample['score_display'].map('{:.3f}'.format)
                    sample['Razones']     = sample['nr'].astype(str)
                    sample['Explicación'] = sample['explain'].str[:65]
                    st.dataframe(sample[['Usuario','privacy_level','Score','Razones','Explicación']],
                                 hide_index=True, use_container_width=True)
            else:
                st.info(f"Ningún producto con '{search_term}' tiene recomendaciones activas.")

# ══════════════════════════════════════════════════════════
# P7 — HALLAZGOS 14·15·16
# ══════════════════════════════════════════════════════════
elif "Hallazgos 14" in pagina:
    st.markdown('<div class="main-header">Hallazgos 14 · 15 · 16</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">HTE · Fairness del catálogo · Cobertura del sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("📈 **Qué muestra esta pantalla:** Tres análisis nuevos que complementan los 13 hallazgos originales. El HTE revela que el consentimiento beneficia más a usuarios con historial rico. El fairness documenta un sesgo de popularidad estructural (ρ=−0.233). La cobertura muestra que el 36% de usuarios no recibe recomendaciones por densidad insuficiente del grafo.")

    t14, t15, t16 = st.tabs(["🔬 HTE del Experimento","📦 Fairness del Catálogo","👥 Cobertura del Sistema"])

    with t14:
        st.markdown("**Efecto heterogéneo del consentimiento por segmento de usuario**")
        st.caption("**Cómo leer:** Cada barra muestra cuántas razones extra gana el grupo tratado vs el control. La línea punteada es el efecto global (+0.04). Barras verdes = efecto mayor al global. Barras ámbar = menor pero positivo. ✅ = significativo (p<0.05), ⚠️ = no significativo.")
        if hte_df is None:
            st.info("Corré el bloque de mejoras para generar hte_experimento.csv.")
        else:
            tab_h1, tab_h2, tab_h3 = st.tabs(["Por historial","Por tipo de comprador","Por categoría"])
            for tab_sub, dim in [(tab_h1,'Volumen historial'),(tab_h2,'Tipo de comprador'),(tab_h3,'Categoría top')]:
                with tab_sub:
                    sub = hte_df[hte_df['dimension']==dim].sort_values('efecto_hte', ascending=True)
                    if sub.empty:
                        st.info(f"Sin datos para {dim}.")
                        continue
                    clrs = [COLORS['primary'] if e>0.04 else COLORS['accent'] if e>=0 else COLORS['danger']
                            for e in sub['efecto_hte']]
                    txt  = [f"{'✅' if s else '⚠️'} p={p:.3f}" for s,p in zip(sub['significativo'],sub['pval'])]
                    fig  = go.Figure(go.Bar(y=sub['segmento'].str[:30], x=sub['efecto_hte'],
                                           orientation='h', marker_color=clrs, marker_line_width=0,
                                           text=txt, textposition='outside',
                                           textfont=dict(color='#8A8880',size=9)))
                    fig.add_vline(x=0.04, line_dash='dash', line_color=COLORS['neutral'],
                                  annotation_text='Efecto global +0.04',
                                  annotation_font_color=COLORS['neutral'])
                    fig.add_vline(x=0, line_color='white', line_width=0.5, opacity=0.3)
                    fig.update_layout(**pbase(), height=max(220, len(sub)*60),
                                      margin=dict(l=0,r=120,t=10,b=0),
                                      xaxis=dict(title='Efecto HTE (razones extra)',
                                                 gridcolor='rgba(255,255,255,0.05)'),
                                      yaxis=dict(gridcolor='rgba(0,0,0,0)'))
                    st.plotly_chart(fig, use_container_width=True)
            st.caption("**Hallazgo 14:** Historial rico (+0.064, p<0.001) tiene efecto 2.5x mayor que cold-start (+0.026, p=0.60 no sig.). El consentimiento solo funciona si hay historial que desbloquear. Implicación: diseño de consentimiento adaptativo por segmento.")

    with t15:
        st.markdown("**Concentración del catálogo y sesgo de popularidad**")
        st.caption("**Cómo leer:** La curva de Lorenz muestra concentración de recomendaciones — si se aleja de la diagonal, pocos ítems acaparan la mayoría. El gráfico de hit rate por cuartil muestra si los más recomendados son también los más relevantes. Si el hit rate cae al subir el cuartil, hay sesgo de popularidad.")
        if fair_df is None:
            st.info("Corré el bloque de mejoras para generar fairness_catalogo.csv.")
        else:
            col_f1, col_f2 = st.columns([3,2])
            with col_f1:
                fs = fair_df.sort_values('n_usuarios_rec', ascending=False).copy()
                n_tot = len(fs)
                fs['xi'] = np.arange(1, n_tot+1) / n_tot * 100
                fs['yi'] = fs['n_usuarios_rec'].cumsum() / fs['n_usuarios_rec'].sum() * 100
                n50 = int((fs['yi']<=50).sum()); n80 = int((fs['yi']<=80).sum())
                fig_l = go.Figure()
                fig_l.add_trace(go.Scatter(x=fs['xi'],y=fs['yi'],mode='lines',name='Distribución real',
                                            line=dict(color=COLORS['primary'],width=2)))
                fig_l.add_trace(go.Scatter(x=[0,100],y=[0,100],mode='lines',name='Distribución perfecta',
                                            line=dict(color=COLORS['neutral'],width=1,dash='dash')))
                fig_l.add_hline(y=50, line_color=COLORS['accent'], line_width=0.8, line_dash='dot')
                fig_l.add_hline(y=80, line_color=COLORS['danger'],  line_width=0.8, line_dash='dot')
                fig_l.add_annotation(x=n50/n_tot*100, y=50, text=f"{n50} ítems → 50% recs",
                                      showarrow=True, arrowcolor=COLORS['accent'],
                                      font=dict(color=COLORS['accent'],size=9), ax=40, ay=-20)
                fig_l.add_annotation(x=n80/n_tot*100, y=80, text=f"{n80} ítems → 80% recs",
                                      showarrow=True, arrowcolor=COLORS['danger'],
                                      font=dict(color=COLORS['danger'],size=9), ax=30, ay=-20)
                fig_l.update_layout(**pbase(), height=320, margin=dict(l=0,r=0,t=10,b=0),
                                     xaxis=dict(title='% del catálogo',gridcolor='rgba(255,255,255,0.05)'),
                                     yaxis=dict(title='% de recomendaciones',gridcolor='rgba(255,255,255,0.05)'),
                                     legend=dict(orientation='h',y=1.1,font=dict(color='#8A8880',size=10)))
                st.plotly_chart(fig_l, use_container_width=True)
            with col_f2:
                if 'cuartil_freq' in fair_df.columns and 'hit_rate' in fair_df.columns:
                    hr_q = fair_df.groupby('cuartil_freq', observed=True)['hit_rate'].mean() * 100
                    fig_q = go.Figure(go.Bar(x=[str(l) for l in hr_q.index], y=hr_q.values,
                                             marker_color=[COLORS['neutral'],COLORS['secondary'],
                                                           COLORS['accent'],COLORS['primary']],
                                             marker_line_width=0,
                                             text=[f'{v:.1f}%' for v in hr_q.values],
                                             textposition='outside', textfont=dict(color='#8A8880',size=10)))
                    fig_q.update_layout(**pbase(), height=320, margin=dict(l=0,r=0,t=10,b=40),
                                         yaxis=dict(title='Hit rate (%)',gridcolor='rgba(255,255,255,0.05)'),
                                         xaxis=dict(title='Cuartil de frecuencia',gridcolor='rgba(0,0,0,0)',tickangle=-15))
                    st.plotly_chart(fig_q, use_container_width=True)
            st.caption("ρ = −0.233 entre frecuencia de recomendación y hit rate. Q4 (muy recomendados, 57 usuarios/ítem) tiene hit rate 41.2% vs 60.4% en Q1. Sesgo de popularidad estructural del grafo de co-compra.")

            st.markdown("**Top 10 ítems más recomendados**")
            top10 = fair_df.sort_values('n_usuarios_rec', ascending=False).head(10)
            show_cols = [c for c in ['title','category','n_usuarios_rec','pct_usuarios','avg_score','hit_rate'] if c in top10.columns]
            top10_s = top10[show_cols].copy()
            top10_s['title'] = top10_s['title'].str[:45]
            top10_s['pct_usuarios'] = top10_s['pct_usuarios'].map('{:.1f}%'.format)
            top10_s['avg_score']    = top10_s['avg_score'].map('{:.3f}'.format)
            if 'hit_rate' in top10_s.columns:
                top10_s['hit_rate'] = top10_s['hit_rate'].map('{:.1%}'.format)
            st.dataframe(top10_s, hide_index=True, use_container_width=True)

    with t16:
        st.markdown("**Cobertura del sistema: ¿a quién no llega?**")
        st.caption("**Cómo leer:** Las barras comparan el perfil promedio de usuarios con y sin recomendaciones. Si las diferencias son grandes y estadísticamente significativas, el sistema no es neutral — favorece a usuarios con mayor volumen y diversidad de compras.")
        if cov_df is None:
            st.info("Corré el bloque de mejoras para generar cobertura_sistema.csv.")
        else:
            con_df2 = cov_df[cov_df['tiene_recs']==True]
            sin_df2 = cov_df[cov_df['tiene_recs']==False]
            k1,k2,k3,k4 = st.columns(4)
            dp = (con_df2['total_products'].mean()/max(sin_df2['total_products'].mean(),1)-1)*100 if 'total_products' in cov_df.columns else 0
            k1.markdown(f'<div class="kpi-box"><div class="kpi-value">{len(con_df2):,}</div><div class="kpi-label">Con cobertura (64%)</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-box"><div class="kpi-value" style="color:#D85A30">{len(sin_df2):,}</div><div class="kpi-label">Sin cobertura (36%)</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-box"><div class="kpi-value">+{dp:.0f}%</div><div class="kpi-label">Más productos (con vs sin)</div></div>', unsafe_allow_html=True)
            k4.markdown(f'<div class="kpi-box"><div class="kpi-value" style="color:#EF9F27">23.9%</div><div class="kpi-label">Sin cobertura = cold-start</div></div>', unsafe_allow_html=True)
            st.write("")
            metrics = [c for c in ['total_products','total_spent','num_orders','category_diversity'] if c in cov_df.columns]
            labels  = ['Productos comprados','Gasto total ($)','Órdenes únicas','Div. categorías'][:len(metrics)]
            fig_cv = go.Figure()
            fig_cv.add_trace(go.Bar(name='Con cobertura', x=labels,
                                    y=[con_df2[m].mean() for m in metrics],
                                    marker_color=COLORS['primary'], marker_line_width=0))
            fig_cv.add_trace(go.Bar(name='Sin cobertura', x=labels,
                                    y=[sin_df2[m].mean() for m in metrics],
                                    marker_color=COLORS['danger'], marker_line_width=0))
            fig_cv.update_layout(**pbase(), barmode='group', height=300,
                                  margin=dict(l=0,r=0,t=10,b=0),
                                  legend=dict(orientation='h',y=1.1,font=dict(color='#8A8880',size=10)),
                                  yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                                  xaxis=dict(gridcolor='rgba(0,0,0,0)'))
            st.plotly_chart(fig_cv, use_container_width=True)
            st.caption("Diferencias todas significativas (p<0.001) excepto ticket promedio (p=0.26). El sistema no discrimina por capacidad de pago — discrimina por volumen y diversidad de compras. El cold-start extremo explica solo el 23.9%: el 76% restante son usuarios especializados en nichos con grafos de co-compra poco densos.")

elif "Hallazgos 14" in pagina:
    st.markdown('<div class="main-header">Hallazgos 14 · 15 · 16</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">HTE · Fairness del catálogo · Cobertura del sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Tres análisis nuevos: HTE (efecto heterogéneo del consentimiento), fairness del catálogo (rho=-0.233) y cobertura del sistema (36% sin recomendaciones).")
    t14, t15, t16 = st.tabs(["HTE del Experimento","Fairness del Catálogo","Cobertura del Sistema"])
    with t14:
        st.caption("Historial rico +0.064 (p<0.001) vs cold-start +0.026 (p=0.60 no sig.). El consentimiento solo funciona si hay historial que desbloquear.")
        if hte_df is None:
            st.info("Corré el bloque de mejoras para generar hte_experimento.csv.")
        else:
            tab_h1, tab_h2, tab_h3 = st.tabs(["Por historial","Por tipo","Por categoría"])
            for tab_sub, dim in [(tab_h1,"Volumen historial"),(tab_h2,"Tipo de comprador"),(tab_h3,"Categoría top")]:
                with tab_sub:
                    sub = hte_df[hte_df["dimension"]==dim].sort_values("efecto_hte", ascending=True)
                    if sub.empty:
                        st.info("Sin datos.")
                        continue
                    clrs = [COLORS["primary"] if e>0.04 else COLORS["accent"] if e>=0 else COLORS["danger"] for e in sub["efecto_hte"]]
                    fig = go.Figure(go.Bar(y=sub["segmento"].str[:30], x=sub["efecto_hte"],
                                          orientation="h", marker_color=clrs, marker_line_width=0,
                                          text=[f"p={p:.3f}" for p in sub["pval"]],
                                          textposition="outside", textfont=dict(color="#8A8880",size=9)))
                    fig.add_vline(x=0.04, line_dash="dash", line_color=COLORS["neutral"])
                    fig.update_layout(**pbase(), height=max(220,len(sub)*65),
                                      margin=dict(l=0,r=100,t=10,b=0),
                                      xaxis=dict(title="Efecto HTE",gridcolor="rgba(255,255,255,0.05)"),
                                      yaxis=dict(gridcolor="rgba(0,0,0,0)"))
                    st.plotly_chart(fig, use_container_width=True)
    with t15:
        st.caption("rho=-0.233. Q4=41.2% vs Q1=60.4% hit rate. Sesgo de popularidad estructural.")
        if fair_df is None:
            st.info("Corré el bloque de mejoras para generar fairness_catalogo.csv.")
        else:
            col_f1, col_f2 = st.columns([3,2])
            with col_f1:
                fs = fair_df.sort_values("n_usuarios_rec", ascending=False).copy()
                n_tot = len(fs)
                fs["xi"] = np.arange(1, n_tot+1) / n_tot * 100
                fs["yi"] = fs["n_usuarios_rec"].cumsum() / fs["n_usuarios_rec"].sum() * 100
                fig_l = go.Figure()
                fig_l.add_trace(go.Scatter(x=fs["xi"],y=fs["yi"],mode="lines",name="Real",line=dict(color=COLORS["primary"],width=2)))
                fig_l.add_trace(go.Scatter(x=[0,100],y=[0,100],mode="lines",name="Perfecta",line=dict(color=COLORS["neutral"],width=1,dash="dash")))
                fig_l.add_hline(y=50, line_color=COLORS["accent"], line_width=0.8, line_dash="dot")
                fig_l.add_hline(y=80, line_color=COLORS["danger"], line_width=0.8, line_dash="dot")
                fig_l.update_layout(**pbase(), height=280, margin=dict(l=0,r=0,t=10,b=0),
                                    xaxis=dict(title="% catalogo",gridcolor="rgba(255,255,255,0.05)"),
                                    yaxis=dict(title="% recs",gridcolor="rgba(255,255,255,0.05)"),
                                    legend=dict(orientation="h",y=1.1,font=dict(color="#8A8880",size=10)))
                st.plotly_chart(fig_l, use_container_width=True)
            with col_f2:
                if "cuartil_freq" in fair_df.columns and "hit_rate" in fair_df.columns:
                    hr_q = fair_df.groupby("cuartil_freq", observed=True)["hit_rate"].mean()*100
                    fig_q = go.Figure(go.Bar(x=[str(l) for l in hr_q.index], y=hr_q.values,
                                            marker_color=[COLORS["neutral"],COLORS["secondary"],COLORS["accent"],COLORS["primary"]],
                                            marker_line_width=0,
                                            text=[f"{v:.1f}%" for v in hr_q.values],
                                            textposition="outside",textfont=dict(color="#8A8880",size=10)))
                    fig_q.update_layout(**pbase(), height=280, margin=dict(l=0,r=0,t=10,b=40),
                                        yaxis=dict(title="Hit rate (%)",gridcolor="rgba(255,255,255,0.05)"),
                                        xaxis=dict(gridcolor="rgba(0,0,0,0)",tickangle=-15))
                    st.plotly_chart(fig_q, use_container_width=True)
    with t16:
        st.caption("3,217/5,027 usuarios cubiertos (64%). Cold-start extremo = 23.9% del total sin cobertura.")
        if cov_df is None:
            st.info("Corré el bloque de mejoras para generar cobertura_sistema.csv.")
        else:
            con_df2 = cov_df[cov_df["tiene_recs"]==True]
            sin_df2 = cov_df[cov_df["tiene_recs"]==False]
            k1,k2,k3,k4 = st.columns(4)
            k1.markdown('<div class="kpi-box"><div class="kpi-value">' + str(len(con_df2)) + '</div><div class="kpi-label">Con cobertura (64%)</div></div>', unsafe_allow_html=True)
            k2.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#D85A30">' + str(len(sin_df2)) + '</div><div class="kpi-label">Sin cobertura (36%)</div></div>', unsafe_allow_html=True)
            k3.markdown('<div class="kpi-box"><div class="kpi-value">+226%</div><div class="kpi-label">Más productos</div></div>', unsafe_allow_html=True)
            k4.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#EF9F27">23.9%</div><div class="kpi-label">Cold-start</div></div>', unsafe_allow_html=True)
            st.write("")
            metrics = [c for c in ["total_products","total_spent","num_orders","category_diversity"] if c in cov_df.columns]
            labels = ["Productos","Gasto ($)","Ordenes","Div. cat."][:len(metrics)]
            fig_cv = go.Figure()
            fig_cv.add_trace(go.Bar(name="Con cobertura",x=labels,y=[con_df2[m].mean() for m in metrics],marker_color=COLORS["primary"],marker_line_width=0))
            fig_cv.add_trace(go.Bar(name="Sin cobertura",x=labels,y=[sin_df2[m].mean() for m in metrics],marker_color=COLORS["danger"],marker_line_width=0))
            fig_cv.update_layout(**pbase(), barmode="group", height=280, margin=dict(l=0,r=0,t=10,b=0),
                                 legend=dict(orientation="h",y=1.1,font=dict(color="#8A8880",size=10)),
                                 yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),xaxis=dict(gridcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig_cv, use_container_width=True)
            st.caption("Diferencias significativas (p<0.001) excepto ticket promedio. El sistema discrimina por volumen, no por capacidad de pago.")

elif "Hallazgos 17" in pagina:
    st.markdown('<div class="main-header">Hallazgos 17 · 18</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Diversidad · Razones XAI por categoría</div>', unsafe_allow_html=True)
    st.write("")
    st.info("H17: ILD mide diversidad de categorías en recomendaciones (rho=-0.562 con hit rate). H18: razón XAI dominante por tipo de ítem — propiedad emergente del grafo.")
    t17, t18 = st.tabs(["H17 ILD","H18 Razones por Categoría"])
    with t17:
        st.caption("ILD = número de categorías distintas en las recomendaciones. rho(ILD, hit_rate)=-0.562: especialización predice mejor la compra real.")
        if ild_df is None:
            st.info("Corré el bloque ILD para generar ild_analisis.csv.")
        else:
            k1,k2,k3,k4 = st.columns(4)
            k1.markdown('<div class="kpi-box"><div class="kpi-value">' + f'{ild_df["ild_category"].mean():.1f}' + '</div><div class="kpi-label">ILD media</div></div>', unsafe_allow_html=True)
            k2.markdown('<div class="kpi-box"><div class="kpi-value">' + f'{ild_df["ild_category"].median():.0f}' + '</div><div class="kpi-label">ILD mediana</div></div>', unsafe_allow_html=True)
            k3.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#D85A30">' + f'{(ild_df["ild_category"]==1).mean():.1%}' + '</div><div class="kpi-label">Mono-categoría</div></div>', unsafe_allow_html=True)
            k4.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#1D9E75">' + f'{(ild_df["ild_category"]>=5).mean():.1%}' + '</div><div class="kpi-label">Muy diversos</div></div>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                ild_hist = ild_df["ild_category"].value_counts().sort_index()
                fig_h = px.bar(x=ild_hist.index, y=ild_hist.values,
                               color_discrete_sequence=[COLORS["primary"]],
                               labels={"x":"N categorias","y":"N usuarios"}, template="plotly_dark")
                fig_h.add_vline(x=ild_df["ild_category"].mean(), line_dash="dash", line_color=COLORS["accent"])
                fig_h.update_layout(**pbase(), height=240, showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig_h, use_container_width=True)
                st.caption("Pico en 1-2 (especializados) y cola larga hasta 20 (generalistas).")
            with col_b:
                if "cuartil_hist" in ild_df.columns:
                    ild_q = ild_df.groupby("cuartil_hist", observed=True)["ild_category"].median().reset_index()
                    fig_q2 = px.bar(ild_q, x="cuartil_hist", y="ild_category",
                                   color_discrete_sequence=[COLORS["secondary"]],
                                   labels={"cuartil_hist":"Cuartil","ild_category":"ILD mediana"},
                                   template="plotly_dark", text="ild_category")
                    fig_q2.update_traces(texttemplate="%{text:.0f}", textposition="outside")
                    fig_q2.update_layout(**pbase(), height=240, showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
                    st.plotly_chart(fig_q2, use_container_width=True)
                    st.caption("Q1=3.0 a Q4=10.0. Más historial = más diversidad = menor precisión.")
    with t18:
        st.caption("Repeat domina en 8/10 categorías. Gift Card no usa Popularidad sino Repeat (30.7%). Propiedad emergente del grafo de co-compra.")
        if raz_df is None:
            st.info("Corré el bloque de análisis para generar razones_por_categoria.csv.")
        else:
            REASON_COLORS = {"Co-compra":COLORS["primary"],"Afinidad categoria":COLORS["secondary"],
                             "Repeat":COLORS["accent"],"Popularidad":"#9B59B6","Estacionalidad":"#5DCAA5",
                             "Afinidad marca":"#E74C3C","Importancia categoria":"#F39C12",
                             "Recencia":COLORS["neutral"],"Importancia marca":"#1ABC9C","Sin razon":"#444","Otra":"#666"}
            top_cats = raz_df["category"].value_counts().head(10).index.tolist()
            cat_r = raz_df[raz_df["category"].isin(top_cats)].groupby(["category","reason_type"]).size().reset_index(name="n")
            totals = cat_r.groupby("category")["n"].transform("sum")
            cat_r["pct"] = cat_r["n"] / totals * 100
            reason_order = ["Co-compra","Repeat","Afinidad categoria","Importancia categoria","Popularidad","Estacionalidad","Afinidad marca","Importancia marca","Recencia","Sin razon","Otra"]
            fig_st = go.Figure()
            for reason in reason_order:
                sub = cat_r[cat_r["reason_type"]==reason]
                if sub.empty: continue
                cat_vals = {row["category"]: row["pct"] for _,row in sub.iterrows()}
                fig_st.add_trace(go.Bar(name=reason, x=[cat_vals.get(c,0) for c in top_cats], y=top_cats,
                                        orientation="h", marker_color=REASON_COLORS.get(reason,COLORS["neutral"]), marker_line_width=0))
            fig_st.update_layout(**pbase(), barmode="stack", height=360, margin=dict(l=0,r=0,t=10,b=0),
                                 legend=dict(orientation="h",y=1.12,font=dict(color="#8A8880",size=9)),
                                 xaxis=dict(title="% de razones",gridcolor="rgba(255,255,255,0.05)"),
                                 yaxis=dict(gridcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig_st, use_container_width=True)

elif "Hallazgos 19" in pagina:
    st.markdown('<div class="main-header">Hallazgo 19 - Contrafactual</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Delta minimo para entrar al Top-5 - GDPR art. 22</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Para cada usuario: que tiene que cambiar para que un item NO recomendado entre al Top-5. Conecta con GDPR art. 22.")
    if cf_df is None:
        st.info("Corre bloque_contrafactual.py para generar contrafactual_analisis.csv.")
    else:
        k1,k2,k3,k4 = st.columns(4)
        v1 = f'{cf_df["gap_score"].median():.4f}'
        v2 = f'{cf_df["delta_s1_needed"].median():.4f}'
        v3 = f'{cf_df["factible_s1"].mean():.1%}'
        v4 = f'{(cf_df["gap_score"] < 0.05).mean():.1%}'
        k1.markdown('<div class="kpi-box"><div class="kpi-value">'+v1+'</div><div class="kpi-label">Gap mediano</div></div>', unsafe_allow_html=True)
        k2.markdown('<div class="kpi-box"><div class="kpi-value">'+v2+'</div><div class="kpi-label">Delta S1 mediano</div></div>', unsafe_allow_html=True)
        k3.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#1D9E75">'+v3+'</div><div class="kpi-label">Casos factibles</div></div>', unsafe_allow_html=True)
        k4.markdown('<div class="kpi-box"><div class="kpi-value" style="color:#EF9F27">'+v4+'</div><div class="kpi-label">Gap muy bajo</div></div>', unsafe_allow_html=True)
        st.write("")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Distribucion del gap de score**")
            st.caption("72.3% de usuarios tiene gap < 0.05. El item #6 esta muy cerca del Top-5.")
            gap_clip = cf_df["gap_score"].clip(upper=cf_df["gap_score"].quantile(0.95))
            fig_gap = px.histogram(gap_clip, nbins=40, color_discrete_sequence=[COLORS["primary"]],
                                   labels={"value":"Gap de score","count":"N usuarios"}, template="plotly_dark")
            fig_gap.add_vline(x=cf_df["gap_score"].median(), line_dash="dash", line_color=COLORS["accent"])
            fig_gap.update_layout(**pbase(), height=260, showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_gap, use_container_width=True)
        with col2:
            st.markdown("**Dificultad del contrafactual**")
            st.caption("42.7% muy facil - 35.2% facil - 14.4% moderado - 7.8% dificil.")
            if "dificultad" in cf_df.columns:
                dc = cf_df["dificultad"].value_counts()
                fig_pie = px.pie(values=dc.values, names=dc.index,
                                 color_discrete_sequence=[COLORS["primary"],COLORS["accent"],COLORS["secondary"],COLORS["danger"]],
                                 hole=0.4, template="plotly_dark")
                fig_pie.update_layout(**pbase(), height=260, margin=dict(l=0,r=0,t=10,b=0),
                                      legend=dict(font=dict(color="#8A8880",size=9)))
                st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("**Delta necesario por senal para entrar al Top-5**")
        st.caption("Menor delta = via mas eficiente. S1 co-compra requiere el menor cambio.")
        senales = ["S1 Co-compra (W=0.40)","S2 Afinidad (W=0.25)","S5 Popularidad (W=0.10)"]
        d1 = cf_df["delta_s1_needed"].median()
        d2 = cf_df["delta_s2_needed"].median() if "delta_s2_needed" in cf_df.columns else 0
        d5 = cf_df["delta_s5_needed"].median() if "delta_s5_needed" in cf_df.columns else 0
        fig_bar = go.Figure(go.Bar(x=senales, y=[d1,d2,d5],
                                   marker_color=[COLORS["primary"],COLORS["secondary"],"#9B59B6"],
                                   marker_line_width=0, text=[f"{d:.4f}" for d in [d1,d2,d5]],
                                   textposition="outside", textfont=dict(color="#8A8880",size=10)))
        fig_bar.add_hline(y=0.3, line_dash="dash", line_color=COLORS["neutral"])
        fig_bar.update_layout(**pbase(), height=260, showlegend=False, margin=dict(l=0,r=0,t=10,b=0),
                              yaxis=dict(title="Delta necesario",gridcolor="rgba(255,255,255,0.05)"),
                              xaxis=dict(gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig_bar, use_container_width=True)
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.success("92.2% de casos tienen contrafactual factible — GDPR art. 22 implementado.")
        with col_g2:
            st.info("Neutral a privacidad: No privada d=0.065, Moderada d=0.069, Sensible d=0.061.")

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)

elif "Legal-by-Design" in pagina:
    st.markdown('<div class="main-header">Legal-by-Design Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-sub">Como cada principio regulatorio se implementa en el sistema</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Esta pantalla traduce principios juridicos abstractos (GDPR, AI Act) en mecanismos tecnicos concretos del sistema. Cada fila muestra un principio regulatorio, el riesgo que mitiga, la implementacion tecnica especifica, y la evidencia empirica de los hallazgos.")

    # Matriz Legal-by-Design
    import pandas as pd
    matrix_data = [
        {
            "Principio": "Transparencia",
            "Marco": "GDPR art. 13-14 / AI Act art. 13",
            "Riesgo mitigado": "Caja negra — usuario no entiende por que recibe recomendaciones",
            "Implementacion tecnica": "SHAP + LIME generan razones visibles por recomendacion (pills verdes). explain_type registra el tipo de senal usada.",
            "Evidencia empirica": "H1: Co-compra SHAP=64.8% vs peso teorico 40%. H3: SHAP-LIME rho=1.00. H4: Calibracion score D10 27x D1."
        },
        {
            "Principio": "Consentimiento granular",
            "Marco": "GDPR art. 7 / ePrivacy",
            "Riesgo mitigado": "Consentimiento binario — aceptar todo o nada, sin control real",
            "Implementacion tecnica": "privacy_level con 3 niveles (No_privada / Privada_moderada / Privada_sensible). share_history configurable. Experimento de consentimiento aleatorio.",
            "Evidencia empirica": "H5: Neutralidad SHAP entre grupos (0.9% variacion). H6: Confianza local estable (0.807 media). H14: HTE +0.064 historial rico vs +0.026 cold-start."
        },
        {
            "Principio": "Minimizacion de datos",
            "Marco": "GDPR art. 5(1)(c) / AI Act art. 10",
            "Riesgo mitigado": "Uso excesivo de datos personales mas alla de lo necesario",
            "Implementacion tecnica": "Exclusion configurable de senales segun privacy_level. Historial oculto en Privada_sensible. Solo se usan datos anonimizados del dataset.",
            "Evidencia empirica": "H5: El modelo no discrimina por privacidad en SHAP. H17: ILD neutral a privacidad (ANOVA p=0.16). Simulador muestra impacto en tiempo real."
        },
        {
            "Principio": "Explicacion accionable",
            "Marco": "GDPR art. 22 / AI Act art. 86",
            "Riesgo mitigado": "Derecho a explicacion meramente descriptiva, no util para el usuario",
            "Implementacion tecnica": "Analisis contrafactual: delta minimo en S1 para entrar al Top-5. Mensaje accionable: que tiene que cambiar para mejorar el ranking.",
            "Evidencia empirica": "H19: 92.2% de casos con contrafactual factible (delta<=0.30). Gap mediano=0.0251. Via mas eficiente: co-compra (delta=0.063 mediano)."
        },
        {
            "Principio": "No discriminacion / Fairness",
            "Marco": "AI Act art. 10 / Directiva 2000/43/CE",
            "Riesgo mitigado": "El sistema favorece sistematicamente a ciertos perfiles de usuario o producto",
            "Implementacion tecnica": "Analisis de fairness por cuartil de frecuencia. MMR para diversificacion. Cobertura del sistema documentada.",
            "Evidencia empirica": "H15: rho(frecuencia, hit_rate)=-0.233 — sesgo de popularidad documentado. H16: 36% sin cobertura, diferencia por volumen no por capacidad de pago (p=0.26 ticket)."
        },
        {
            "Principio": "Trazabilidad y auditabilidad",
            "Marco": "AI Act art. 12 / GDPR art. 30",
            "Riesgo mitigado": "Imposibilidad de auditar o verificar decisiones automatizadas",
            "Implementacion tecnica": "explain_type registra la senal dominante por recomendacion. xai_master_findings_table.csv consolida 19 hallazgos auditables. Pipeline reproducible en Colab.",
            "Evidencia empirica": "H7: Senales independientes (rho<0.09 en 9/10 pares). H18: Razones coherentes por categoria sin programacion explicita — auditabilidad emergente."
        },
        {
            "Principio": "Supervision humana",
            "Marco": "AI Act art. 14 / GDPR art. 22(3)",
            "Riesgo mitigado": "Automatizacion cerrada sin posibilidad de intervencion o correccion",
            "Implementacion tecnica": "Simulador de privacidad configurable en tiempo real. Buscador inverso para ver a quien se recomienda cada item. Comparacion de usuarios para detectar inconsistencias.",
            "Evidencia empirica": "App interactiva con 9 pantallas. 3,217 usuarios explorables individualmente. Simulador muestra impacto de cambios de privacidad en tiempo real."
        },
        {
            "Principio": "Robustez y precision",
            "Marco": "AI Act art. 15 / ISO/IEC 42001",
            "Riesgo mitigado": "Sistema impreciso o no robusto ante variaciones de perfil",
            "Implementacion tecnica": "Modelo hibrido: co-compra item-item + ALS + BPR + ensamble. Evaluacion offline con NDCG@10. Analisis de robustez por segmento de historial.",
            "Evidencia empirica": "H4: Calibracion perfecta rho=1.00. H10: Cold-start vs historial rico diferencia <1pp en S1. H14: HTE significativo en 5/11 segmentos."
        },
    ]

    df_matrix = pd.DataFrame(matrix_data)

    # Tabs por marco regulatorio
    tab_gdpr, tab_ai, tab_all = st.tabs(["GDPR","AI Act","Matriz completa"])

    with tab_gdpr:
        st.markdown("**Implementacion de principios GDPR en el sistema**")
        st.caption("Cada fila muestra como un articulo del GDPR se traduce en una decision de arquitectura o interfaz concreta, con evidencia empirica de los hallazgos.")
        gdpr_items = ["Transparencia","Consentimiento granular","Minimizacion de datos","Explicacion accionable","Trazabilidad y auditabilidad","Supervision humana"]
        df_gdpr = df_matrix[df_matrix["Principio"].isin(gdpr_items)].copy()
        for _, row in df_gdpr.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_ai:
        st.markdown("**Implementacion de principios del AI Act en el sistema**")
        st.caption("El AI Act (2024) clasifica los sistemas de recomendacion como IA de alto riesgo en contextos criticos. Esta matriz muestra como el sistema anticipa sus requisitos.")
        ai_items = ["Transparencia","Minimizacion de datos","No discriminacion / Fairness","Trazabilidad y auditabilidad","Supervision humana","Robustez y precision"]
        df_ai = df_matrix[df_matrix["Principio"].isin(ai_items)].copy()
        for _, row in df_ai.iterrows():
            with st.expander(f"**{row['Principio']}** — {row['Marco']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Riesgo mitigado**")
                    st.warning(row["Riesgo mitigado"])
                    st.markdown("**Implementacion tecnica**")
                    st.info(row["Implementacion tecnica"])
                with col_b:
                    st.markdown("**Evidencia empirica**")
                    st.success(row["Evidencia empirica"])

    with tab_all:
        st.markdown("**Matriz completa — 8 principios regulatorios**")
        st.caption("Vision consolidada de todos los principios implementados. Cada fila puede usarse como referencia para el capitulo de metodologia y discusion de la tesis.")
        st.dataframe(
            df_matrix[["Principio","Marco","Implementacion tecnica","Evidencia empirica"]],
            hide_index=True, use_container_width=True
        )
        st.write("")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.markdown('<div class="kpi-box"><div class="kpi-value">8</div><div class="kpi-label">Principios implementados</div></div>', unsafe_allow_html=True)
        col_s2.markdown('<div class="kpi-box"><div class="kpi-value">19</div><div class="kpi-label">Hallazgos como evidencia</div></div>', unsafe_allow_html=True)
        col_s3.markdown('<div class="kpi-box"><div class="kpi-value">2</div><div class="kpi-label">Marcos regulatorios (GDPR + AI Act)</div></div>', unsafe_allow_html=True)
        col_s4.markdown('<div class="kpi-box"><div class="kpi-value">9</div><div class="kpi-label">Pantallas de la app como evidencia</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown("""
        <div class="rec-card" style="border-color:#1D9E75">
          <div style="font-size:0.85rem;font-weight:600;color:#E8E6E0;margin-bottom:6px">Contribucion diferencial de esta tesis</div>
          <div style="font-size:0.82rem;color:#8A8880;line-height:1.7">
            La mayoria de la literatura describe principios regulatorios pero no los implementa en sistemas reales.<br>
            Esta tesis demuestra que <b style="color:#1D9E75">regulacion y ML no son mundos separados</b>: cada principio del GDPR y el AI Act
            tiene un correlato tecnico concreto, medible empiricamente con los 19 hallazgos del estudio.<br><br>
            Referentes mas cercanos: Wachter et al. (contrafactual), IBM FactSheets, NIST AI RMF.<br>
            Diferencial: sistema experimental completo con evaluacion empirica integrada.
          </div>
        </div>
        """, unsafe_allow_html=True)
