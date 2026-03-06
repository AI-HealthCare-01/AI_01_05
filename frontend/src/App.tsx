import { useEffect, useRef } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import KakaoCallbackPage from './pages/KakaoCallbackPage'
import SignupPage from './pages/SignupPage'
import MainPage from './pages/MainPage'
import { AuthRequired, SignupRequired } from './components/ProtectedRoute'
import { refreshToken } from './apis/authApi'
import { useAuthStore } from './store/authStore'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/auth/kakao/callback" element={<KakaoCallbackPage />} />
      <Route path="/signup" element={<SignupRequired><SignupPage /></SignupRequired>} />
      <Route path="/main" element={<AuthRequired><MainPage /></AuthRequired>} />
    </Routes>
  )
}

export default function App() {
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    const hasToken = Boolean(useAuthStore.getState().accessToken)
    if (!hasToken) refreshToken()
  }, [])

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
