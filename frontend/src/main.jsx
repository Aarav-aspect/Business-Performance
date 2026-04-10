import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import TradePerformance from './TradePerformance.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter basename="/business-performance">
      <Routes>
        <Route path="/sectorperformance" element={<App />} />
        <Route path="/tradeperformance" element={<TradePerformance />} />
        <Route path="*" element={<Navigate to="/sectorperformance" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
