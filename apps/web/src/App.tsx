import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MarketingPage } from './components/MarketingPage'
import { PlannerApp } from './components/PlannerApp'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MarketingPage />} />
        <Route path="/plan" element={<PlannerApp />} />
      </Routes>
    </BrowserRouter>
  )
}
