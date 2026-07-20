import React from 'react'
import { Award, Code, Globe, Shield, Users, Cpu, Database, Layers } from 'lucide-react'
import './APropos.css'

export default function APropos() {
    return (
        <div className="page-container apropos-page">
            <div className="apropos-hero">
                <h1 className="page-title">Notre Mission</h1>
                <p className="page-subtitle">
                    KATARA (Kéran-Assoli-Tchamba-Amou-Rivière-Alima) est né d'une volonté simple :
                    <strong> ne plus subir les inondations au Togo, mais les anticiper.</strong>
                </p>
            </div>

            <div className="apropos-grid">
                <div className="glass-card apropos-content-card">
                    <h2>L'Équipe</h2>
                    <p>
                        Nous sommes une équipe d'ingénieurs et de data scientists passionnés par l'impact
                        technologique sur le continent africain. Notre expertise croise l'intelligence
                        artificielle, l'analyse géospatiale et le développement logiciel.
                    </p>
                    <div className="team-icons">
                        <div className="team-item"><Code size={32} color="#60A5FA" /><span>Développement</span></div>
                        <div className="team-item"><Globe size={32} color="#10B981" /><span>Data Géospatiale</span></div>
                        <div className="team-item"><Shield size={32} color="#F59E0B" /><span>Prévention</span></div>
                    </div>
                </div>

                <div className="glass-card apropos-content-card">
                    <h2>Reconnaissance</h2>
                    <p>
                        KATARA a été primé lors de plusieurs compétitions d'innovation au Togo.
                    </p>
                    <ul className="awards-list">
                        <li>
                            <Award size={20} color="#8B5CF6" />
                            <span><strong>1er Prix</strong> - Hackathon "Tech for Climate" 2024</span>
                        </li>
                        <li>
                            <Award size={20} color="#8B5CF6" />
                            <span><strong>Finaliste</strong> - Togo Innovation Challenge</span>
                        </li>
                        <li>
                            <Award size={20} color="#8B5CF6" />
                            <span><strong>Coup de Cœur</strong> - Salon de l'Eau et de l'Assainissement</span>
                        </li>
                    </ul>
                </div>
            </div>


            <div className="glass-card apropos-content-card" style={{gridColumn:'1/-1'}}>
                <h2>Stack Technologique</h2>
                <div className="team-icons" style={{flexWrap:'wrap',gap:'2rem',marginTop:'1rem'}}>
                    <div className="team-item">
                        <Cpu size={32} color="#8B5CF6" />
                        <span>RandomForest ML</span>
                    </div>
                    <div className="team-item">
                        <Layers size={32} color="#60A5FA" />
                        <span>React + Vite</span>
                    </div>
                    <div className="team-item">
                        <Globe size={32} color="#F59E0B" />
                        <span>Flask REST API</span>
                    </div>
                    <div className="team-item">
                        <Database size={32} color="#10B981" />
                        <span>SQLite / DB</span>
                    </div>
                    <div className="team-item">
                        <Code size={32} color="#EF4444" />
                        <span>Sentinel-1 SAR</span>
                    </div>
                    <div className="team-item">
                        <Shield size={32} color="#EC4899" />
                        <span>OpenStreetMap</span>
                    </div>
                </div>
            </div>

            <div className="glass-card contact-section">
                <Users size={48} color="#3B82F6" />
                <h2>Prêt à soutenir KATARA ?</h2>
                <p>
                    Que vous soyez un investisseur, une institution publique, ou une organisation
                    communautaire, nous sommes ouverts aux collaborations pour étendre notre système
                    à tout le territoire togolais.
                </p>
                <a href="mailto:contact@katara.tg" className="btn-primary">contact@katara.tg</a>
            </div>
        </div>
    )
}
