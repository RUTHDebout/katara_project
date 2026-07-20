import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import './Navbar.css'

export default function Navbar() {
    const loc = useLocation()
    const [open, setOpen] = useState(false)

    const links = [
        { to: '/',          label: 'Accueil' },
        { to: '/alertes',   label: 'Alertes' },
        { to: '/dashboard', label: 'Dashboard' },
        { to: '/carte',     label: 'Carte' },
        { to: '/a-propos',  label: 'A propos' },
    ]

    const isActive = (to) =>
        loc.pathname === to ||
        (to === '/dashboard' && loc.pathname.startsWith('/historique'))

    const close = () => setOpen(false)

    return (
        <nav className="navbar">
            <Link to="/" className="nav-logo" onClick={close}>
                <span className="nav-wave">&#127754;</span>
                <span className="nav-brand">KATARA</span>
            </Link>

            <ul className={`nav-links${open ? ' open' : ''}`}>
                {links.map(l => (
                    <li key={l.to}>
                        <Link
                            to={l.to}
                            className={isActive(l.to) ? 'active' : ''}
                            onClick={close}
                        >
                            {l.label}
                        </Link>
                    </li>
                ))}
                <li className="nav-cta-mobile">
                    <Link to="/alertes" className="btn-primary" onClick={close}>
                        Voir les alertes
                    </Link>
                </li>
            </ul>

            <Link to="/alertes" className="nav-cta" onClick={close}>
                Voir les alertes
            </Link>

            <button
                className="nav-hamburger"
                onClick={() => setOpen(o => !o)}
                aria-label={open ? 'Fermer le menu' : 'Ouvrir le menu'}
            >
                {open ? <X size={22} /> : <Menu size={22} />}
            </button>
        </nav>
    )
}