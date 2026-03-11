import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { kakaoLogin } from '../apis/authApi'
import { useAuthStore } from '../store/authStore'

export default function KakaoCallbackPage() {
  const navigate = useNavigate()
  const called = useRef(false)

  useEffect(() => {
    if (called.current) return
    called.current = true

    const code = new URLSearchParams(window.location.search).get('code')
    if (!code) {
      navigate('/')
      return
    }

    kakaoLogin(code)
      .then(async (data) => {
        if (!data.is_new_user && data.access_token) {
          useAuthStore.getState().setAccessToken(data.access_token)
          // onboarding_completed 확인
          const meRes = await fetch('/api/v1/users/me', {
            headers: { Authorization: `Bearer ${data.access_token}` },
            credentials: 'include',
          })
          if (meRes.ok) {
            const me = await meRes.json()
            if (me.user_id) useAuthStore.getState().setUserId(me.user_id)
            navigate(me.onboarding_completed ? '/main' : '/character-select', { replace: true })
          } else {
            navigate('/main', { replace: true })
          }
        } else if (data.is_new_user && data.temp_token) {
          sessionStorage.setItem('temp_token', data.temp_token)
          navigate('/signup', {
            replace: true,
            state: { nickname: data.kakao_info?.nickname ?? '' },
          })
        }
      })
      .catch((err) => {
        console.error('[KakaoCallback] 로그인 처리 실패:', err)
        const msg = typeof err.detail === 'string' ? err.detail : '로그인 중 오류가 발생했습니다.'
        navigate('/', { state: { error: msg } })
      })
  }, [navigate])

  return (
    <div className="page">
      <p style={{ color: 'var(--placeholder)' }}>카카오 로그인 처리 중...</p>
    </div>
  )
}
