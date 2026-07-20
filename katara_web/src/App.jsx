import React, { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import ErrorBoundary from './components/ErrorBoundary'

const Home       = lazy(() => import('./pages/Home'))
const Alertes    = lazy(() => import('./pages/Alertes'))
const Dashboard  = lazy(() => import('./pages/Dashboard'))
const APropos    = lazy(() => import('./pages/APropos'))
const Carte      = lazy(() => import('./pages/Carte'))
const Historique = lazy(() => import('./pages/Historique'))
const NotFound   = lazy(() => import('./pages/NotFound'))

function Loader() {
  return (
    <div style={{ display:'flex', justifyContent:'center', alignItems:'center', minHeight:'60vh' }}>
      <div className="loader">Chargement...</div>
    </div>
  )
}

function App() {
  return (
    <>
      <Navbar />
      <main>
        <ErrorBoundary>
        <Suspense fallback={<Loader />}>
          <Routes>
            <Route path="/"                   element={<Home />} />
            <Route path="/alertes"            element={<Alertes />} />
            <Route path="/dashboard"          element={<Dashboard />} />
            <Route path="/a-propos"           element={<APropos />} />
            <Route path="/carte"              element={<Carte />} />
            <Route path="/historique/:zoneId" element={<Historique />} />
            <Route path="*"                   element={<NotFound />} />
          </Routes>
        </Suspense>
        </ErrorBoundary>
      </main>
      <Footer />
    </>
  )
}

export default App
