import React from 'react'
import { Link } from 'react-router-dom'
import './Footer.css'

export default function Footer() {
    return (
        <footer className="footer">
            <div className="footer-logo">🌊 <span>KATARA</span></div>
            <div className="footer-links">
                <Link to="/">Accueil</Link>
                <Link to="/alertes">Alertes</Link>
                <Link to="/dashboard">Dashboard</Link>
                <Link to="/carte">Carte</Link>
                <Link to="/a-propos">À propos</Link>
            </div>
            <div className="footer-copy">© 2026 KATARA · Lomé, Togo · contact@katara.tg</div>
        </footer>
    )
}
