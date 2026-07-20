"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA — Générateur de rapport PDF                  ║
║         Lance avec : python katara_rapport_pdf.py           ║
╚══════════════════════════════════════════════════════════════╝

Génère un rapport mensuel professionnel au format PDF.
Utilisable pour : UNDP, Xylem, DID Summit, bailleurs de fonds.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF

# ── Couleurs KATARA ──
BLEU       = colors.HexColor("#1A3A5C")
BLEU_CLR   = colors.HexColor("#2E6DA4")
OR         = colors.HexColor("#E8A020")
VERT       = colors.HexColor("#2E7D32")
ROUGE      = colors.HexColor("#C62828")
ORANGE     = colors.HexColor("#E65100")
GRIS_CLR   = colors.HexColor("#F5F7FA")
GRIS       = colors.HexColor("#90A4AE")
BLANC      = colors.white
NOIR       = colors.HexColor("#1A1A2E")

PAGE_W, PAGE_H = A4
MARGE = 2*cm


# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
def creer_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["titre_principal"] = ParagraphStyle(
        "titre_principal", parent=base["Normal"],
        fontSize=22, textColor=BLANC, fontName="Helvetica-Bold",
        alignment=TA_CENTER, leading=28
    )
    styles["sous_titre"] = ParagraphStyle(
        "sous_titre", parent=base["Normal"],
        fontSize=11, textColor=colors.HexColor("#B0C4DE"),
        fontName="Helvetica", alignment=TA_CENTER, leading=16
    )
    styles["section"] = ParagraphStyle(
        "section", parent=base["Normal"],
        fontSize=13, textColor=BLEU, fontName="Helvetica-Bold",
        spaceBefore=16, spaceAfter=8, leading=18
    )
    styles["corps"] = ParagraphStyle(
        "corps", parent=base["Normal"],
        fontSize=9.5, textColor=NOIR, fontName="Helvetica",
        alignment=TA_JUSTIFY, leading=15, spaceAfter=6
    )
    styles["legende"] = ParagraphStyle(
        "legende", parent=base["Normal"],
        fontSize=8, textColor=GRIS, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=4
    )
    styles["stat_chiffre"] = ParagraphStyle(
        "stat_chiffre", parent=base["Normal"],
        fontSize=26, textColor=BLEU, fontName="Helvetica-Bold",
        alignment=TA_CENTER, leading=30
    )
    styles["stat_label"] = ParagraphStyle(
        "stat_label", parent=base["Normal"],
        fontSize=8, textColor=GRIS, fontName="Helvetica",
        alignment=TA_CENTER, leading=12
    )
    styles["pied"] = ParagraphStyle(
        "pied", parent=base["Normal"],
        fontSize=7.5, textColor=GRIS, fontName="Helvetica",
        alignment=TA_CENTER
    )
    return styles


# ─────────────────────────────────────────────
# ENTÊTE DE PAGE (callback)
# ─────────────────────────────────────────────
def entete_page(canvas, doc):
    canvas.saveState()
    # Bande bleue en haut
    canvas.setFillColor(BLEU)
    canvas.rect(0, PAGE_H - 1.2*cm, PAGE_W, 1.2*cm, fill=1, stroke=0)
    # Logo texte
    canvas.setFillColor(BLANC)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGE, PAGE_H - 0.85*cm, "KATARA — Système de Prédiction d'Inondations")
    # Numéro de page
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGE, PAGE_H - 0.85*cm, f"Page {doc.page}")
    # Ligne dorée
    canvas.setStrokeColor(OR)
    canvas.setLineWidth(2)
    canvas.line(0, PAGE_H - 1.2*cm, PAGE_W, PAGE_H - 1.2*cm)
    # Pied de page
    canvas.setStrokeColor(colors.HexColor("#E0E0E0"))
    canvas.setLineWidth(0.5)
    canvas.line(MARGE, 1.4*cm, PAGE_W - MARGE, 1.4*cm)
    canvas.setFillColor(GRIS)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(PAGE_W/2, 0.9*cm,
        "KATARA © 2025 · Lomé, Togo · contact@katara.tg · Confidentiel")
    canvas.restoreState()


# ─────────────────────────────────────────────
# PAGE DE COUVERTURE
# ─────────────────────────────────────────────
def page_couverture(story, styles, donnees):
    # Fond bleu haut
    d = Drawing(PAGE_W - 2*MARGE, 7*cm)
    fond = Rect(0, 0, PAGE_W - 2*MARGE, 7*cm, fillColor=BLEU, strokeColor=None)
    d.add(fond)
    accent = Rect(0, 0, 0.5*cm, 7*cm, fillColor=OR, strokeColor=None)
    d.add(accent)
    story.append(d)
    story.append(Spacer(1, -7*cm))

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("🌊 KATARA", styles["titre_principal"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Système de Prédiction d'Inondations — Afrique de l'Ouest", styles["sous_titre"]))
    story.append(Paragraph(f"Rapport Mensuel — {donnees['periode']}", styles["sous_titre"]))
    story.append(Spacer(1, 6*cm))

    # Infos couverture
    infos = [
        ["Préparé par", "Ruth Ameyo Gliglo — CEO & Fondatrice"],
        ["Organisation", "KATARA · Lomé, Togo"],
        ["Date du rapport", datetime.now().strftime("%d %B %Y")],
        ["Région couverte", "Togo — Région Maritime (5 zones actives)"],
        ["Version", "v1.0 · Confidentiel"],
    ]
    t = Table(infos, colWidths=[4.5*cm, 11*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,0), (0,-1), BLEU),
        ("TEXTCOLOR", (1,0), (1,-1), NOIR),
        ("LINEBELOW", (0,0), (-1,-2), 0.3, colors.HexColor("#E0E0E0")),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(t)
    story.append(PageBreak())


# ─────────────────────────────────────────────
# SECTION STATISTIQUES (cartes)
# ─────────────────────────────────────────────
def section_stats(story, styles, donnees):
    story.append(Paragraph("Résumé Exécutif", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLEU_CLR, spaceAfter=12))

    resume = donnees.get("resume", "")
    if resume:
        story.append(Paragraph(resume, styles["corps"]))
        story.append(Spacer(1, 0.4*cm))

    # 4 cartes de stats
    stats = donnees["stats"]

    def carte(chiffre, label, couleur=BLEU):
        return [
            Paragraph(f'<font color="#{couleur.hexval()[2:]}">{chiffre}</font>', styles["stat_chiffre"]),
            Paragraph(label, styles["stat_label"]),
        ]

    data_stats = [[
        carte(stats["total_analyses"], "Analyses effectuées", BLEU),
        carte(stats["alertes_critiques"], "Alertes critiques", ROUGE),
        carte(stats["sms_envoyes"], "SMS envoyés", VERT),
        carte(f"{stats['precision_modele']}%", "Précision du modèle", OR),
    ]]

    t = Table(data_stats, colWidths=[4*cm]*4, rowHeights=[2.5*cm])
    t.setStyle(TableStyle([
        ("BOX",        (0,0), (0,0), 1, colors.HexColor("#E3F2FD")),
        ("BOX",        (1,0), (1,0), 1, colors.HexColor("#FFEBEE")),
        ("BOX",        (2,0), (2,0), 1, colors.HexColor("#E8F5E9")),
        ("BOX",        (3,0), (3,0), 1, colors.HexColor("#FFF8E1")),
        ("BACKGROUND", (0,0), (0,0), colors.HexColor("#E3F2FD")),
        ("BACKGROUND", (1,0), (1,0), colors.HexColor("#FFEBEE")),
        ("BACKGROUND", (2,0), (2,0), colors.HexColor("#E8F5E9")),
        ("BACKGROUND", (3,0), (3,0), colors.HexColor("#FFF8E1")),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", [6]),
        ("LEFTPADDING",  (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("COLPADDING",   (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.6*cm))


# ─────────────────────────────────────────────
# TABLEAU ZONES
# ─────────────────────────────────────────────
def section_zones(story, styles, donnees):
    story.append(Paragraph("État des Zones Surveillées", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLEU_CLR, spaceAfter=12))

    entetes = ["Zone", "Localité", "Prob. inond.", "Niveau", "Pop. exposée", "Dernière alerte"]
    data = [entetes] + [
        [
            z["id"],
            z["nom"],
            f"{z['probabilite']*100:.0f}%",
            z["niveau"],
            f"{z['population']:,}",
            z.get("derniere_alerte", "—"),
        ]
        for z in donnees["zones"]
    ]

    couleur_niveau = {
        "normal":   colors.HexColor("#E8F5E9"),
        "faible":   colors.HexColor("#FFF8E1"),
        "moyen":    colors.HexColor("#FFF3E0"),
        "critique": colors.HexColor("#FFEBEE"),
    }
    couleur_texte = {
        "normal":   VERT,
        "faible":   OR,
        "moyen":    ORANGE,
        "critique": ROUGE,
    }

    col_w = [2.5*cm, 4*cm, 2.5*cm, 2.5*cm, 2.8*cm, 3.2*cm]
    t = Table(data, colWidths=col_w, repeatRows=1)

    style_base = [
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0), 8),
        ("BACKGROUND",  (0,0), (-1,0), BLEU),
        ("TEXTCOLOR",   (0,0), (-1,0), BLANC),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 8.5),
        ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#CFD8DC")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [BLANC, GRIS_CLR]),
        ("ALIGN",       (2,0), (3,-1), "CENTER"),
        ("ALIGN",       (4,0), (4,-1), "RIGHT"),
        ("TOPPADDING",  (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",(0,0), (-1,-1), 7),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
    ]
    # Couleurs par niveau
    for i, z in enumerate(donnees["zones"], 1):
        niv = z["niveau"]
        bg  = couleur_niveau.get(niv, BLANC)
        tc  = couleur_texte.get(niv, NOIR)
        style_base.append(("BACKGROUND", (3,i), (3,i), bg))
        style_base.append(("TEXTCOLOR",  (3,i), (3,i), tc))
        style_base.append(("FONTNAME",   (3,i), (3,i), "Helvetica-Bold"))

    t.setStyle(TableStyle(style_base))
    story.append(t)
    story.append(Spacer(1, 0.6*cm))


# ─────────────────────────────────────────────
# GRAPHIQUE BARRES (reportlab natif)
# ─────────────────────────────────────────────
def section_graphique(story, styles, donnees):
    story.append(Paragraph("Évolution des Probabilités — 7 derniers jours", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLEU_CLR, spaceAfter=12))

    graphique_w = 14*cm
    graphique_h = 5*cm
    d = Drawing(graphique_w, graphique_h)

    bc = VerticalBarChart()
    bc.x = 1.5*cm
    bc.y = 0.8*cm
    bc.width  = graphique_w - 2.5*cm
    bc.height = graphique_h - 1.2*cm

    # Données : probabilités des 7 derniers jours pour 3 zones
    historique = donnees.get("historique_7j", {})
    series = list(historique.values())[:3] if historique else [
        [0.3, 0.4, 0.55, 0.6, 0.45, 0.35, 0.5],
        [0.2, 0.25, 0.3, 0.4, 0.35, 0.28, 0.32],
        [0.5, 0.6, 0.75, 0.85, 0.7, 0.6, 0.65],
    ]
    bc.data = [[round(v*100) for v in s] for s in series]

    jours = [(datetime.now().replace(day=max(1, datetime.now().day-6+i))).strftime("%d/%m")
             for i in range(7)]
    bc.categoryAxis.categoryNames = jours
    bc.categoryAxis.labels.fontName  = "Helvetica"
    bc.categoryAxis.labels.fontSize  = 7
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.labels.fontName  = "Helvetica"
    bc.valueAxis.labels.fontSize  = 7
    bc.valueAxis.labelTextFormat = "%d%%"

    couleurs_barres = [BLEU_CLR, OR, ROUGE]
    for i, c in enumerate(couleurs_barres):
        bc.bars[i].fillColor = c

    bc.barWidth = 0.15*cm
    bc.groupSpacing = 0.4*cm
    d.add(bc)

    # Légende manuelle
    noms_zones = list(historique.keys())[:3] if historique else ["LOM-001", "LOM-003", "LOM-005"]
    for i, (nom, coul) in enumerate(zip(noms_zones, couleurs_barres)):
        x_leg = 1.5*cm + i * 4.5*cm
        rect = Rect(x_leg, 0, 0.3*cm, 0.2*cm, fillColor=coul, strokeColor=None)
        d.add(rect)
        lbl = String(x_leg + 0.4*cm, 0.03*cm, nom, fontSize=7, fontName="Helvetica")
        d.add(lbl)

    story.append(d)
    story.append(Paragraph("Figure 1 — Probabilités d'inondation (%) par zone et par jour", styles["legende"]))
    story.append(Spacer(1, 0.4*cm))


# ─────────────────────────────────────────────
# SECTION ALERTES SMS
# ─────────────────────────────────────────────
def section_alertes(story, styles, donnees):
    story.append(Paragraph("Journal des Alertes SMS", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLEU_CLR, spaceAfter=12))

    alertes = donnees.get("alertes", [])
    if not alertes:
        story.append(Paragraph("Aucune alerte émise durant cette période.", styles["corps"]))
        return

    data = [["Date/Heure", "Zone", "Niveau", "SMS envoyés", "Destinataires", "Statut"]]
    for a in alertes:
        data.append([
            a.get("datetime", "—"),
            a.get("zone", "—"),
            a.get("niveau", "—"),
            str(a.get("sms_envoyes", 0)),
            str(a.get("destinataires", 0)),
            a.get("statut", "—"),
        ])

    col_w = [3.5*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm]
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 8.5),
        ("BACKGROUND",   (0,0), (-1,0), BLEU),
        ("TEXTCOLOR",    (0,0), (-1,0), BLANC),
        ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#CFD8DC")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [BLANC, GRIS_CLR]),
        ("ALIGN",        (3,0), (4,-1), "CENTER"),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))


# ─────────────────────────────────────────────
# RECOMMANDATIONS
# ─────────────────────────────────────────────
def section_recommandations(story, styles, donnees):
    story.append(Paragraph("Recommandations & Prochaines Étapes", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLEU_CLR, spaceAfter=12))

    recs = donnees.get("recommandations", [])
    for i, rec in enumerate(recs, 1):
        priorite_couleur = {"haute": ROUGE, "moyenne": ORANGE, "basse": VERT}.get(rec.get("priorite", "basse"), GRIS)
        badge_txt = rec.get("priorite", "basse").upper()

        data_rec = [[
            Paragraph(f"<b>{i}. {rec['titre']}</b>", styles["corps"]),
            Paragraph(f'<font color="#{priorite_couleur.hexval()[2:]}">{badge_txt}</font>',
                      ParagraphStyle("badge", parent=styles["legende"], fontName="Helvetica-Bold", fontSize=8)),
        ]]
        t = Table(data_rec, colWidths=[13*cm, 3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), GRIS_CLR),
            ("TOPPADDING",   (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 0),
            ("LEFTPADDING",  (0,0), (0,-1), 10),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN",        (1,0), (1,-1), "CENTER"),
        ]))
        story.append(KeepTogether([
            t,
            Table([[Paragraph(rec["description"], styles["corps"])]], colWidths=[16*cm],
                  style=TableStyle([
                      ("BACKGROUND", (0,0), (-1,-1), GRIS_CLR),
                      ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                      ("LEFTPADDING", (0,0), (-1,-1), 10),
                      ("TOPPADDING", (0,0), (-1,-1), 2),
                  ])),
            Spacer(1, 0.3*cm),
        ]))


# ─────────────────────────────────────────────
# DONNÉES SIMULÉES (remplace par vraies données)
# ─────────────────────────────────────────────
def generer_donnees_demo():
    mois = datetime.now().strftime("%B %Y")
    return {
        "periode": mois,
        "resume": (
            f"Durant le mois de {mois}, KATARA a surveillé 5 zones à risque d'inondation "
            "dans la région Maritime du Togo. Le système a émis 3 alertes critiques, "
            "permettant l'évacuation préventive de 2 400 personnes dans la zone de Lomé-Sud. "
            "La précision du modèle de prédiction a atteint 89%, en amélioration de 4 points "
            "par rapport au mois précédent grâce à l'intégration de nouvelles données "
            "satellitaires Sentinel-1. Le réseau d'alertes SMS a couvert 100% des téléphones "
            "enregistrés dans les zones à risque."
        ),
        "stats": {
            "total_analyses":   744,
            "alertes_critiques": 3,
            "sms_envoyes":      1_240,
            "precision_modele": 89,
        },
        "zones": [
            {"id":"LOM-001","nom":"Lomé Centre","probabilite":0.35,"niveau":"faible",  "population":45_000,"derniere_alerte":"14/02/2025"},
            {"id":"LOM-002","nom":"Bè Kpota",   "probabilite":0.78,"niveau":"critique","population":28_000,"derniere_alerte":"21/02/2025"},
            {"id":"LOM-003","nom":"Agbalépédogan","probabilite":0.55,"niveau":"moyen","population":62_000,"derniere_alerte":"18/02/2025"},
            {"id":"LOM-004","nom":"Agoè",        "probabilite":0.18,"niveau":"normal", "population":89_000,"derniere_alerte":"—"},
            {"id":"LOM-005","nom":"Légbassito",  "probabilite":0.82,"niveau":"critique","population":12_000,"derniere_alerte":"22/02/2025"},
        ],
        "historique_7j": {
            "LOM-002": [0.45, 0.52, 0.60, 0.72, 0.78, 0.71, 0.78],
            "LOM-003": [0.30, 0.38, 0.45, 0.50, 0.48, 0.52, 0.55],
            "LOM-005": [0.50, 0.60, 0.68, 0.75, 0.80, 0.78, 0.82],
        },
        "alertes": [
            {"datetime":"14/02/2025 06:30","zone":"LOM-001","niveau":"moyen",   "sms_envoyes":320,"destinataires":320,"statut":"Envoyé ✓"},
            {"datetime":"18/02/2025 03:15","zone":"LOM-003","niveau":"moyen",   "sms_envoyes":580,"destinataires":580,"statut":"Envoyé ✓"},
            {"datetime":"21/02/2025 11:45","zone":"LOM-002","niveau":"critique","sms_envoyes":210,"destinataires":210,"statut":"Envoyé ✓"},
            {"datetime":"22/02/2025 08:00","zone":"LOM-005","niveau":"critique","sms_envoyes":130,"destinataires":130,"statut":"Envoyé ✓"},
        ],
        "recommandations": [
            {
                "titre":       "Déploiement de 3 pluviomètres supplémentaires — Zone Bè Kpota",
                "description": ("La zone LOM-002 présente des pics de risque récurrents non corrélés "
                                "aux données météo disponibles. L'installation de capteurs locaux "
                                "permettrait d'améliorer la précision de +8 à +12 points."),
                "priorite":    "haute",
            },
            {
                "titre":       "Entraînement du modèle sur données historiques ORSTOM 1985-2010",
                "description": ("L'intégration des archives d'inondations historiques permettrait "
                                "d'identifier les patterns saisonniers et d'anticiper les crues "
                                "avec un délai d'alerte de 48h au lieu de 6h actuellement."),
                "priorite":    "haute",
            },
            {
                "titre":       "Extension à la zone de Tsévié (Région Maritime Nord)",
                "description": ("Tsévié est identifiée comme zone secondaire à risque. "
                                "L'extension du système nécessite l'intégration de 200 points "
                                "GIS supplémentaires et un partenariat avec la mairie locale."),
                "priorite":    "moyenne",
            },
            {
                "titre":       "Intégration d'une application mobile pour les agents de terrain",
                "description": ("Une app légère (Flutter) permettrait aux agents ANPC d'envoyer "
                                "des observations terrain en temps réel, enrichissant le modèle ML."),
                "priorite":    "basse",
            },
        ],
    }


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def generer_rapport(donnees=None, fichier_sortie=None):
    if donnees is None:
        donnees = generer_donnees_demo()

    if fichier_sortie is None:
        mois_str = datetime.now().strftime("%Y-%m")
        fichier_sortie = f"katara_rapport_{mois_str}.pdf"

    doc = SimpleDocTemplate(
        fichier_sortie,
        pagesize=A4,
        leftMargin=MARGE, rightMargin=MARGE,
        topMargin=1.8*cm, bottomMargin=1.8*cm,
        title=f"KATARA — Rapport {donnees['periode']}",
        author="Ruth Ameyo Gliglo — KATARA",
        subject="Rapport mensuel prédiction inondations",
    )

    styles = creer_styles()
    story  = []

    # ── Page de couverture ──
    page_couverture(story, styles, donnees)

    # ── Stats ──
    section_stats(story, styles, donnees)
    story.append(Spacer(1, 0.3*cm))

    # ── Zones ──
    section_zones(story, styles, donnees)
    story.append(Spacer(1, 0.3*cm))

    # ── Graphique ──
    section_graphique(story, styles, donnees)
    story.append(PageBreak())

    # ── Alertes ──
    section_alertes(story, styles, donnees)
    story.append(Spacer(1, 0.4*cm))

    # ── Recommandations ──
    section_recommandations(story, styles, donnees)

    # ── Build ──
    doc.build(story, onFirstPage=entete_page, onLaterPages=entete_page)
    return fichier_sortie


# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  📄 KATARA — Génération du rapport PDF")
    print("=" * 55)

    # Essayer de charger les vraies données depuis l'API
    donnees = None
    try:
        import requests
        r = requests.get("http://localhost:5000/api/dashboard", timeout=3)
        if r.ok:
            api_data = r.json()
            print("  ✅ Données récupérées depuis l'API KATARA")
            # Adapter le format API → format rapport
            donnees = generer_donnees_demo()
            donnees["zones"] = [
                {
                    "id":              z["zone_id"],
                    "nom":             z["nom"],
                    "probabilite":     z.get("probabilite", 0),
                    "niveau":          z.get("niveau_alerte", "normal"),
                    "population":      z.get("population", 0),
                    "derniere_alerte": z.get("derniere_alerte", "—"),
                }
                for z in api_data.get("zones", [])
            ]
    except Exception:
        print("  ℹ️  API non disponible — utilisation des données de démonstration")

    fichier = generer_rapport(donnees)
    taille  = os.path.getsize(fichier) // 1024

    print(f"\n  ✅ Rapport généré : {fichier}")
    print(f"  📦 Taille : {taille} Ko")
    print(f"  📄 Prêt pour : UNDP, Xylem Challenge, DID Summit 2026")
    print("=" * 55)
