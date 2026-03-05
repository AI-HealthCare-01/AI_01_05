import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function MainPage() {
  const navigate = useNavigate()
  const clearAuth = useAuthStore((s) => s.clearAuth)

  const handleLogout = () => {
    clearAuth()
    navigate('/', { replace: true })
  }

  return (
    <div className="page">
      <div className="card" style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <div className="service-title">도닥톡</div>
          <div className="service-subtitle">마음이 힘들 때, 조용히 곁에 있을게요</div>
        </div>
        <p style={{ color: 'var(--placeholder)', fontSize: '15px', lineHeight: 1.7 }}>
          로그인되었습니다.<br />
          서비스 준비 중입니다. 🌿
        </p>
        <button
          onClick={handleLogout}
          style={{ padding: '12px', background: 'var(--border)', color: 'var(--text)', borderRadius: '8px' }}
        >
          로그아웃
        </button>
      </div>
    </div>
  )
}
