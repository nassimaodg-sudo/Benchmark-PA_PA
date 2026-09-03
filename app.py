"""
PA Selection & Market Intelligence Tool — France 2026
Thylios & Associés — Conseil & Stratégie Financière

Port Streamlit du POC HTML autonome. Mêmes données réelles, même moteur
de scoring, même principe : jamais de donnée inventée, chaque score
porte son niveau de preuve.
"""

import json
import os
from datetime import date

import streamlit as st

# ============================================================
# CONFIG & STYLE
# ============================================================
st.set_page_config(
    page_title="PA Selection & Market Intelligence Tool — Thylios & Associés",
    page_icon="🧭",
    layout="wide",
)

TEAL = "#1AB1AF"
PINK = "#F34C63"

st.markdown(
    f"""
    <style>
    .stApp {{ background: linear-gradient(160deg, #F4FBFA 0%, #FFFFFF 45%, #FDF2F4 100%); }}
    .thylios-badge {{
        display:inline-block; padding:3px 10px; border-radius:20px;
        font-size:12px; font-weight:600; margin-right:4px;
    }}
    .badge-g {{ background:#E4F7EE; color:#127A4C; }}
    .badge-o {{ background:#FFF3DE; color:#9A6300; }}
    .badge-r {{ background:#FDE7E9; color:#B0263A; }}
    .badge-grey {{ background:#EEEFF1; color:#5B6270; }}
    .badge-blue {{ background:#E7F0FE; color:#1D5FC9; }}
    .score-big {{
        font-size:38px; font-weight:800;
        background: linear-gradient(90deg, {TEAL}, {PINK});
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }}
    div[data-testid="stMetricValue"] {{ color: {TEAL}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

BLOC_LABELS = {
    "A": "Positionnement & cible", "B": "Couverture fonctionnelle", "C": "Conformité RFE",
    "D": "Formats & données", "E": "Interopérabilité", "F": "Intégration SI",
    "G": "Sécurité & conformité", "H": "Services & accompagnement",
    "I": "Pricing / modèle économique", "J": "Maturité & crédibilité",
}
BLOC_ORDER = list(BLOC_LABELS.keys())

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ============================================================
# CHARGEMENT DES DONNÉES (mise en cache — fichiers réels, jamais générés)
# ============================================================
@st.cache_data
def load_data():
    with open(os.path.join(DATA_DIR, "pa_master.json"), encoding="utf-8") as f:
        pa_master = json.load(f)
    with open(os.path.join(DATA_DIR, "pa_capabilities.json"), encoding="utf-8") as f:
        caps = json.load(f)
    with open(os.path.join(DATA_DIR, "cas_usage.json"), encoding="utf-8") as f:
        cas_usage = json.load(f)
    with open(os.path.join(DATA_DIR, "weights_by_profile.json"), encoding="utf-8") as f:
        weights_profiles = json.load(f)

    pa_by_id = {p["id"]: p for p in pa_master}
    caps_by_pa = {}
    for c in caps:
        caps_by_pa.setdefault(c["pa_id"], []).append(c)

    return pa_master, pa_by_id, caps, caps_by_pa, cas_usage, weights_profiles


PA_MASTER, PA_BY_ID, CAPS, CAPS_BY_PA, CAS_USAGE, WEIGHTS_PROFILES = load_data()

THYLIOS_PARTNERS = {
    "GENERIX Group": "Partenaire privilégié Thylios & Associés — expertise reconnue sur les intégrations SAP",
}


# ============================================================
# MOTEUR DE SCORING (port direct du moteur JS du POC HTML)
# ============================================================
def bloc_scores_for(pa_id):
    """Moyenne du Capability Score par bloc, uniquement sur les entrées notées (score numérique non nul)."""
    scores = {}
    for c in CAPS_BY_PA.get(pa_id, []):
        if c["capability_score"] is None:
            continue
        scores.setdefault(c["bloc"], []).append(c["capability_score"])
    return {b: sum(v) / len(v) for b, v in scores.items()}


def bloc_has_any_data(pa_id, bloc):
    return any(c["bloc"] == bloc for c in CAPS_BY_PA.get(pa_id, []))


def completeness_for(pa_id):
    """Nombre de blocs (sur 10) documentés — au moins une donnée collectée,
    notée ou descriptive (ex. Bloc A 'Segment stratégique' est souvent
    descriptif sans score chiffré). Distinct de bloc_scores_for, qui ne
    sert qu'au calcul du Fit Score et ne peut logiquement faire la moyenne
    que d'entrées notées."""
    return sum(1 for b in BLOC_ORDER if bloc_has_any_data(pa_id, b))


def confidence_for(pa_id):
    n = completeness_for(pa_id)
    if n <= 2:
        return "Faible", "badge-r"
    if n <= 6:
        return "Moyenne", "badge-o"
    return "Élevée", "badge-g"


def size_eligible(pa_id, taille_code):
    """taille_code: 'TPE'|'PME'|'ETI'|'GC'. Retourne True/False/None (inconnu -> gardé par défaut)."""
    p = PA_BY_ID.get(pa_id, {})
    flags = p.get("taille")
    if not flags:
        return None
    return bool(flags.get(taille_code))


def weights_from_answers(answers):
    w = {"A": 5, "B": 12, "C": 16, "D": 10, "E": 10, "F": 10, "G": 10, "H": 8, "I": 10, "J": 9}
    for p in answers.get("priorites", []):
        w[p] = w.get(p, 0) + 12
    if answers.get("erp") and answers["erp"] != "Autre":
        w["F"] += 8
    if answers.get("erp_integration"):
        w["F"] += 5
    if answers.get("international"):
        w["E"] += 10
        w["J"] += 3
    if answers.get("edi"):
        w["E"] += 6
    if answers.get("securite"):
        w["G"] += 12
    if answers.get("accompagnement") == "accompagne":
        w["H"] += 10
    if answers.get("volume") == "high":
        w["B"] += 5
        w["F"] += 5
    return w


def fit_score_for(pa_id, weights):
    scores = bloc_scores_for(pa_id)
    if not scores:
        return None
    num = sum(scores[b] * weights.get(b, 0) for b in scores)
    den = sum(weights.get(b, 0) for b in scores)
    if den == 0:
        return None
    return (num / den) * 20  # échelle 0-5 -> 0-100


def why_text(pa_id):
    scores = bloc_scores_for(pa_id)
    top = sorted(scores.items(), key=lambda kv: -kv[1])
    strengths = [BLOC_LABELS[b] for b, v in top if v >= 3.5][:2]
    if not strengths:
        return "Profil éligible sur les critères de base ; données encore limitées sur ses points forts spécifiques."
    return "Se distingue sur : " + " et ".join(strengths) + "."


def candidates_for(answers):
    cands = list(PA_MASTER)
    taille = answers.get("taille")
    if taille:
        cands = [p for p in cands if size_eligible(p["id"], taille) in (None, True)]
    return cands


def top_matches(answers, weights, n=3):
    cands = candidates_for(answers)
    scored = []
    for p in cands:
        s = fit_score_for(p["id"], weights)
        if s is not None:
            scored.append((p, s))
    scored.sort(key=lambda x: -x[1])
    return scored[:n]


def partner_badge(nom):
    return THYLIOS_PARTNERS.get(nom)


# ============================================================
# SESSION STATE INIT
# ============================================================
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "custom_weights" not in st.session_state:
    st.session_state.custom_weights = None
if "page" not in st.session_state:
    st.session_state.page = "accueil"

TAILLE_LABELS = {"TPE": "TPE (< 10 salariés)", "PME": "PME (10-250)", "ETI": "ETI (250-5000)", "GC": "Grand compte (> 5000)"}
SECTEURS = [
    "Retail / distribution", "Industrie", "Banque & finance", "Santé & pharma", "Secteur public",
    "Assurance", "IT & SaaS", "Logistique & transport", "Startups & TPE", "Services professionnels",
    "Énergie", "Agroalimentaire", "Immobilier", "E-commerce", "Autre",
]
PRIORITES_LABELS = {
    "C": "Conformité réglementaire", "I": "Coût / transparence tarifaire",
    "F": "Intégration à mon SI", "G": "Sécurité des données", "H": "Accompagnement / support",
}


# ============================================================
# SIDEBAR — NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown("### Thylios & Associés")
    st.caption("Market Intelligence · PA Selection")
    st.markdown("---")
    nav = st.radio(
        "Navigation",
        ["🏠 Accueil / Diagnostic", "🔍 Explorer les 166 PA", "⚖️ Comparateur", "📋 Cas d'usage"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.metric("PA au registre DGFiP", len(PA_MASTER))
    n_full = sum(1 for p in PA_MASTER if completeness_for(p["id"]) == 10)
    st.metric("PA qualifiées à 100%", n_full)
    st.metric("Points de données réels", len(CAPS))
    st.caption("Registre officiel DGFiP, relevé du 30/08/2026. Aucune donnée inventée — chaque score porte sa source et son niveau de preuve.")


# ============================================================
# PAGE — ACCUEIL / DIAGNOSTIC
# ============================================================
def render_accueil():
    st.title("Quelle Plateforme Agréée pour votre entreprise ?")
    st.caption("8 questions, 2 minutes. Construit sur le registre officiel DGFiP et des données vérifiées, sourcées au 30/08/2026 — pas sur un partenariat commercial.")

    with st.form("diagnostic_form"):
        st.subheader("1. Votre profil")
        c1, c2 = st.columns(2)
        with c1:
            taille = st.radio("Taille de l'entreprise", list(TAILLE_LABELS.keys()), format_func=lambda k: TAILLE_LABELS[k], horizontal=True)
        with c2:
            secteur = st.selectbox("Secteur d'activité", SECTEURS)

        st.subheader("2. Vos flux")
        c3, c4 = st.columns(2)
        with c3:
            international = st.radio("Flux de facturation à l'international ?", ["Non", "Oui"], horizontal=True) == "Oui"
        with c4:
            volume = st.select_slider("Volume annuel de factures", options=["low", "mid", "high"],
                                       format_func=lambda v: {"low": "< 10 000", "mid": "10 000 à 100 000", "high": "> 100 000"}[v])

        st.subheader("3. Votre SI")
        c5, c6 = st.columns(2)
        with c5:
            erp = st.selectbox("ERP / logiciel de gestion principal", ["SAP", "Oracle", "Sage", "Cegid", "Autre"])
            erp_integration = False
            if erp != "Autre":
                erp_integration = st.checkbox(f"Un connecteur PA ↔ {erp} est-il déjà envisagé ou en place ?")
        with c6:
            edi = st.checkbox("Utilisez-vous déjà des échanges EDI structurés ?")

        st.subheader("4. Vos priorités")
        priorites = st.multiselect(
            "Sélectionnez une ou plusieurs priorités",
            list(PRIORITES_LABELS.keys()),
            format_func=lambda k: PRIORITES_LABELS[k],
        )
        c7, c8 = st.columns(2)
        with c7:
            securite = st.checkbox("Sécurité renforcée obligatoire (certification, hébergement souverain) ?")
        with c8:
            accompagnement = None
            if "H" not in priorites:
                accompagnement = st.radio("Autonomie ou accompagnement humain fort ?", ["auto", "accompagne"],
                                           format_func=lambda v: "Autonomie / self-service" if v == "auto" else "Accompagnement humain dédié",
                                           horizontal=True)

        submitted = st.form_submit_button("Voir mes recommandations →", type="primary", use_container_width=True)

    if submitted:
        st.session_state.answers = {
            "taille": taille, "secteur": secteur, "international": international, "volume": volume,
            "erp": erp, "erp_integration": erp_integration, "edi": edi,
            "priorites": priorites, "securite": securite, "accompagnement": accompagnement,
        }
        st.session_state.custom_weights = None
        st.session_state.page = "resultats"
        st.rerun()


# ============================================================
# PAGE — RÉSULTATS
# ============================================================
def render_resultats():
    answers = st.session_state.answers
    if not answers:
        st.info("Répondez d'abord au diagnostic depuis l'accueil.")
        return

    if st.session_state.custom_weights is None:
        st.session_state.custom_weights = weights_from_answers(answers)
    weights = st.session_state.custom_weights

    chip = []
    if answers.get("taille"):
        chip.append(TAILLE_LABELS[answers["taille"]].split(" (")[0])
    if answers.get("erp") and answers["erp"] != "Autre":
        chip.append(answers["erp"])
    if answers.get("international"):
        chip.append("international")
    st.title("Votre shortlist personnalisée")
    if chip:
        st.markdown(f"👤 **{' · '.join(chip)}**")

    with st.expander("🎚️ Ajuster mes priorités (What-If) — le classement se recalcule en direct"):
        new_weights = dict(weights)
        rows_of_blocs = [BLOC_ORDER[i:i + 5] for i in range(0, len(BLOC_ORDER), 5)]
        for row in rows_of_blocs:
            row_cols = st.columns(len(row))
            for col, b in zip(row_cols, row):
                with col:
                    new_weights[b] = st.slider(BLOC_LABELS[b], 0, 40, weights.get(b, 0), key=f"w_{b}")
        c1, c2 = st.columns(2)
        if c1.button("Appliquer", use_container_width=True):
            st.session_state.custom_weights = new_weights
            st.rerun()
        if c2.button("Réinitialiser à mon profil", use_container_width=True):
            st.session_state.custom_weights = weights_from_answers(answers)
            st.rerun()

    matches = top_matches(answers, weights, n=3)
    if not matches:
        st.warning("Aucune PA de notre base qualifiée ne correspond à ce profil précis — élargissez vos critères ou consultez l'Explorateur.")
        return

    for i, (pa, score) in enumerate(matches, start=1):
        conf_label, conf_cls = confidence_for(pa["id"])
        badge = partner_badge(pa["nom"])
        st.markdown("---")
        st.markdown(f"**#{i} recommandation**")
        title = f"### {pa['nom']}" + (" 🤝 *Partenaire Thylios*" if badge else "")
        st.markdown(title)
        if badge:
            st.caption(badge)
        st.markdown(
            f'<div class="score-big">{round(score)}</div><span style="color:#8992A3">/100</span> '
            f'&nbsp; <span class="thylios-badge {conf_cls}">Confiance {conf_label}</span>',
            unsafe_allow_html=True,
        )
        st.write(why_text(pa["id"]))
        bcol1, bcol2 = st.columns(2)
        if bcol1.button("Voir le détail", key=f"detail_{pa['id']}", use_container_width=True):
            st.session_state.detail_id = pa["id"]
            st.session_state.page = "detail"
            st.rerun()
        if bcol2.button("Comparer", key=f"cmp_{pa['id']}", use_container_width=True):
            st.session_state.compare_a = pa["id"]
            st.session_state.page = "comparateur"
            st.rerun()

    st.caption(
        f"Ce résultat s'appuie sur {sum(1 for p in PA_MASTER if completeness_for(p['id'])==10)} PA qualifiées en profondeur "
        f"parmi les {len(PA_MASTER)} immatriculées au registre DGFiP (relevé du 30/08/2026). Le badge de confiance indique "
        "combien de blocs (sur 10) ont pu être vérifiés avec une source identifiable. Diagnostic de premier niveau — "
        "à confirmer par RFI avant toute décision."
    )


# ============================================================
# PAGE — FICHE DÉTAIL PA
# ============================================================
def render_detail(pa_id):
    pa = PA_BY_ID.get(pa_id)
    if not pa:
        st.error("PA introuvable.")
        return
    conf_label, conf_cls = confidence_for(pa_id)
    badge = partner_badge(pa["nom"])

    st.title(pa["nom"] + (" 🤝" if badge else ""))
    if badge:
        st.caption(badge)
    st.markdown(
        f'<span class="thylios-badge {conf_cls}">Confiance {conf_label}</span> '
        f'&nbsp;{completeness_for(pa_id)}/10 blocs qualifiés &nbsp;·&nbsp; statut : {pa["statut"]} &nbsp;·&nbsp; pays : {pa["pays"]}',
        unsafe_allow_html=True,
    )

    # Budget
    pricing_items = [c for c in CAPS_BY_PA.get(pa_id, []) if c["bloc"] == "I"]
    st.markdown("#### 💰 Budget estimé")
    if not pricing_items:
        st.info("Non documenté — nécessite un devis direct auprès de l'éditeur.")
    else:
        for c in pricing_items:
            st.write(f"**{c['reponse']}**")
            st.caption(f"Preuve {c['evidence_level']} · {c['source']}")

    st.markdown("---")
    for b in BLOC_ORDER:
        items = [c for c in CAPS_BY_PA.get(pa_id, []) if c["bloc"] == b]
        with st.expander(f"{BLOC_LABELS[b]}" + (f" ({len(items)})" if items else " — non renseigné")):
            if not items:
                st.caption("Non renseigné à ce jour.")
            for c in items:
                score_txt = f" — **{c['capability_score']}/5**" if c["capability_score"] is not None else ""
                st.markdown(f"**{c['sous_critere']}**{score_txt}  \n{c['reponse']}")
                st.caption(f"Preuve {c['evidence_level']} · {c['source']}")

    st.caption('"Non renseigné" signifie une donnée manquante, jamais une note de 0.')

    if st.button("← Retour aux résultats"):
        st.session_state.page = "resultats"
        st.rerun()


# ============================================================
# PAGE — EXPLORATEUR
# ============================================================
def render_explorer():
    st.title(f"Explorer les {len(PA_MASTER)} PA")
    st.caption("Registre officiel DGFiP, relevé du 30/08/2026. La confiance indique combien de blocs sont vérifiés — pas la qualité de la PA elle-même.")
    q = st.text_input("Rechercher un éditeur...")
    rows = [p for p in PA_MASTER if q.lower() in p["nom"].lower()] if q else PA_MASTER

    import pandas as pd
    table = []
    for p in rows[:200]:
        conf_label, _ = confidence_for(p["id"])
        table.append({
            "Éditeur": p["nom"], "Statut": p["statut"].replace("Immatriculation ", ""),
            "Pays": p["pays"], "Complétude": f"{completeness_for(p['id'])}/10", "Confiance": conf_label,
        })
    df = pd.DataFrame(table)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### Voir une fiche")
    sel = st.selectbox("Choisir une PA", [p["nom"] for p in rows], index=None, placeholder="Rechercher...")
    if sel:
        pa = next(p for p in rows if p["nom"] == sel)
        if st.button("Ouvrir la fiche détaillée"):
            st.session_state.detail_id = pa["id"]
            st.session_state.page = "detail"
            st.rerun()


# ============================================================
# PAGE — COMPARATEUR
# ============================================================
def render_comparateur():
    st.title("Comparer deux PA")
    documented = [p for p in PA_MASTER if completeness_for(p["id"]) >= 6]
    names = [p["nom"] for p in documented]
    if not names:
        st.warning("Aucune PA suffisamment documentée pour une comparaison significative.")
        return

    default_a = PA_BY_ID.get(st.session_state.get("compare_a", ""), {}).get("nom", names[0])
    c1, c2 = st.columns(2)
    with c1:
        nom_a = st.selectbox("PA A", names, index=names.index(default_a) if default_a in names else 0)
    with c2:
        nom_b = st.selectbox("PA B", names, index=1 if len(names) > 1 else 0)

    pa_a = next(p for p in documented if p["nom"] == nom_a)
    pa_b = next(p for p in documented if p["nom"] == nom_b)
    sa, sb = bloc_scores_for(pa_a["id"]), bloc_scores_for(pa_b["id"])

    import pandas as pd
    rows = []
    for b in BLOC_ORDER:
        rows.append({
            "Bloc": BLOC_LABELS[b],
            nom_a: f"{sa[b]:.1f}/5" if b in sa else "—",
            nom_b: f"{sb[b]:.1f}/5" if b in sb else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption('"—" signifie donnée non renseignée, pas une note de 0.')


# ============================================================
# PAGE — CAS D'USAGE
# ============================================================
def render_cas_usage():
    st.title("Cas d'usage — XP Z12-014 V1.4")
    st.caption(
        "44 cas d'usage réglementaires (49 lignes avec sous-cas), source AFNOR XP Z12-014 V1.4 du 30/06/2026. "
        "La couverture par PA n'est pas affichée : aucune source disponible à ce jour ne documente quelle PA "
        "gère quel cas — l'inventer serait contraire à la règle de ce projet."
    )
    q = st.text_input("Rechercher un cas d'usage...")
    familles = {}
    for cu_id, label, famille in CAS_USAGE:
        if q and q.lower() not in label.lower() and q.lower() not in (famille or "").lower():
            continue
        familles.setdefault(famille or "Autre", []).append((cu_id, label))

    for famille, items in familles.items():
        with st.expander(f"{famille} ({len(items)})", expanded=True):
            for cu_id, label in items:
                st.markdown(f"**CU {cu_id}** — {label}")

    st.caption("Source : AFNOR XP Z12-014, édition juin 2026, version 1.4 du 30/06/2026.")


# ============================================================
# ROUTAGE
# ============================================================
if nav == "🏠 Accueil / Diagnostic":
    st.session_state.page = "accueil" if not st.session_state.answers else st.session_state.page
    if st.session_state.page not in ("resultats", "detail"):
        st.session_state.page = "accueil"
elif nav == "🔍 Explorer les 166 PA":
    st.session_state.page = "explorer"
elif nav == "⚖️ Comparateur":
    st.session_state.page = "comparateur"
elif nav == "📋 Cas d'usage":
    st.session_state.page = "cas_usage"

page = st.session_state.page
if page == "accueil":
    render_accueil()
elif page == "resultats":
    render_resultats()
elif page == "detail":
    render_detail(st.session_state.get("detail_id"))
elif page == "explorer":
    render_explorer()
elif page == "comparateur":
    render_comparateur()
elif page == "cas_usage":
    render_cas_usage()
else:
    render_accueil()

st.markdown("---")
st.caption(f"Outil propriétaire de Market Intelligence — Thylios & Associés, Conseil & Stratégie Financière · {date.today().strftime('%d/%m/%Y')}")
