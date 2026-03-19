const API_BASE = import.meta.env.VITE_API_BASE_URL as string
const KAKAO_CALLBACK_URI = `${API_BASE.replace('/api/v1', '')}/api/v1/auth/kakao/callback`

const KAKAO_AUTH_URL =
  `https://kauth.kakao.com/oauth/authorize?response_type=code` +
  `&client_id=${import.meta.env.VITE_KAKAO_REST_API_KEY}` +
  `&redirect_uri=${encodeURIComponent(KAKAO_CALLBACK_URI)}`

export default function LoginPage() {
  return (
    <div className="page">
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
        <div>
          <div className="service-title">도닥톡</div>
          <div className="service-subtitle">마음이 힘들 때, 조용히 곁에 있을게요</div>
        </div>

        <a
          href={KAKAO_AUTH_URL}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            width: '100%',
            padding: '14px',
            background: '#FEE500',
            color: '#191919',
            borderRadius: '8px',
            fontSize: '16px',
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M10 2C5.582 2 2 4.91 2 8.5c0 2.26 1.37 4.25 3.44 5.44L4.6 17.1a.3.3 0 0 0 .44.33l4.1-2.72c.28.03.57.04.86.04 4.418 0 8-2.91 8-6.5S14.418 2 10 2Z"
              fill="#191919"
            />
          </svg>
          카카오로 시작하기
        </a>
      </div>
    </div>
  )
}
