import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import LobbyApp from './LobbyApp'
import ScannerPage from './ScannerPage'
import './styles.css'

const isScanner = window.location.pathname.replace(/\/+$/, '') === '/scanner'

createRoot(document.getElementById('root')!).render(
    <StrictMode>{isScanner ? <ScannerPage /> : <LobbyApp />}</StrictMode>,
)
