import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { sendPhoneCode, verifyPhoneCode, kakaoSignup } from '../apis/authApi'
import { useAuthStore } from '../store/authStore'
import AgreementModal from '../components/AgreementModal'
import type { AgreementState } from '../types/auth'

export default function SignupPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const initialNickname = (location.state as { nickname?: string })?.nickname ?? ''

  const [form, setForm] = useState({
    nickname: initialNickname,
    phone: '',
    verifyCode: '',
    email: '',
    gender: '',
    birthday: '',
  })
  const [agreements, setAgreements] = useState<Omit<AgreementState, 'all'> | null>(null)
  const [showAgreementModal, setShowAgreementModal] = useState(false)

  const [phoneTimer, setPhoneTimer] = useState(0)
  const [verificationToken, setVerificationToken] = useState('')
  const [phoneVerified, setPhoneVerified] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState('')
  const [loading, setLoading] = useState(false)

  // 타이머
  useEffect(() => {
    if (phoneTimer <= 0) return
    const id = setInterval(() => setPhoneTimer((t) => t - 1), 1000)
    return () => clearInterval(id)
  }, [phoneTimer])

  const set = (key: string, value: string) => {
    setForm((f) => ({ ...f, [key]: value }))
    setErrors((e) => ({ ...e, [key]: '' }))

    if (key === 'phone' && import.meta.env.DEV) {
      const testToken = import.meta.env.VITE_TEST_VERIFICATION_TOKEN
      const isValidPhone = /^(010\d{8}|01[16789]\d{7,8})$/.test(value.replace(/\D/g, ''))
      if (testToken && isValidPhone) {
        setVerificationToken(testToken)
        setPhoneVerified(true)
      } else {
        setVerificationToken('')
        setPhoneVerified(false)
      }
    }
  }

  const fmtTimer = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const handleSendCode = async () => {
    if (!form.phone) return setErrors((e) => ({ ...e, phone: '전화번호를 입력해주세요.' }))
    try {
      const res = await sendPhoneCode(form.phone)
      setPhoneTimer(res.ttl)
      setPhoneVerified(false)
      setVerificationToken('')
    } catch (err: unknown) {
      const e = err as { status?: number; detail?: string }
      setErrors((prev) => ({
        ...prev,
        phone: e.status === 429 ? '일일 발송 한도를 초과했습니다.' : (e.detail ?? 'SMS 발송 오류'),
      }))
    }
  }

  const handleVerifyCode = async () => {
    if (!form.verifyCode) return setErrors((e) => ({ ...e, verifyCode: '인증번호를 입력해주세요.' }))
    try {
      const res = await verifyPhoneCode(form.phone, form.verifyCode)
      setVerificationToken(res.verification_token)
      setPhoneVerified(true)
      setPhoneTimer(0)
      setErrors((e) => ({ ...e, verifyCode: '' }))
    } catch (err: unknown) {
      const e = err as { detail?: string }
      setErrors((prev) => ({ ...prev, verifyCode: e.detail ?? '인증 실패' }))
    }
  }

  const validate = () => {
    const errs: Record<string, string> = {}
    if (!form.nickname) errs.nickname = '닉네임을 입력해주세요.'
    if (form.nickname.length > 10) errs.nickname = '닉네임은 10자 이하여야 합니다.'
    if (!phoneVerified) errs.phone = '전화번호 인증을 완료해주세요.'
    if (!form.email) errs.email = '이메일을 입력해주세요.'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errs.email = '올바른 이메일 형식이 아닙니다.'
    if (!agreements || !agreements.terms_of_service || !agreements.privacy_policy || !agreements.sensitive_policy)
      errs.agreements = '필수 약관에 모두 동의해주세요.'
    return errs
  }

  const handleSubmit = async () => {
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }

    const tempToken = sessionStorage.getItem('temp_token')
    if (!tempToken) { setSubmitError('인증 정보가 만료되었습니다. 다시 로그인해주세요.'); return }

    setLoading(true)
    setSubmitError('')
    try {
      const res = await kakaoSignup(
        {
          nickname: form.nickname,
          phone_number: form.phone,
          phone_verification_token: verificationToken,
          email: form.email,
          gender: form.gender,
          birthday: form.birthday || null,
          agreements: agreements!,
        },
        tempToken,
      )
      sessionStorage.removeItem('temp_token')
      localStorage.setItem('access_token', res.access_token)
      useAuthStore.getState().setAccessToken(res.access_token)
      navigate('/main', { replace: true })
    } catch (err: unknown) {
      const e = err as { status?: number; detail?: string }
      setSubmitError(
        e.status === 409 ? '이미 가입된 계정입니다.' : (e.detail ?? '가입 중 오류가 발생했습니다.'),
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page" style={{ justifyContent: 'flex-start', paddingTop: '40px' }}>
      <div className="card">
        <div style={{ marginBottom: '28px' }}>
          <div className="service-title">도닥톡</div>
          <div className="service-subtitle">회원가입</div>
        </div>

        <div className="form-stack">
          {/* 닉네임 */}
          <div className="field">
            <label>닉네임 <span style={{ color: 'var(--error)' }}>*</span></label>
            <input
              value={form.nickname}
              onChange={(e) => set('nickname', e.target.value)}
              placeholder="닉네임 (최대 10자)"
              maxLength={10}
            />
            {errors.nickname && <span className="error-msg">{errors.nickname}</span>}
          </div>

          {/* 전화번호 */}
          <div className="field">
            <label>전화번호 <span style={{ color: 'var(--error)' }}>*</span></label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                value={form.phone}
                onChange={(e) => set('phone', e.target.value)}
                placeholder="010-0000-0000"
                style={{ flex: 1 }}
                disabled={phoneVerified}
              />
              <button
                onClick={handleSendCode}
                disabled={phoneTimer > 0 || phoneVerified}
                style={{ padding: '0 14px', background: 'var(--btn-bg)', color: 'var(--btn-text)', whiteSpace: 'nowrap', borderRadius: '8px' }}
              >
                {phoneTimer > 0 ? fmtTimer(phoneTimer) : phoneVerified ? '인증완료' : '인증번호 발송'}
              </button>
            </div>
            {errors.phone && <span className="error-msg">{errors.phone}</span>}
          </div>

          {/* 인증번호 */}
          {(phoneTimer > 0 || (form.verifyCode && !phoneVerified)) && (
            <div className="field">
              <label>인증번호</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  value={form.verifyCode}
                  onChange={(e) => set('verifyCode', e.target.value)}
                  placeholder="6자리 인증번호"
                  maxLength={6}
                  style={{ flex: 1 }}
                />
                <button
                  onClick={handleVerifyCode}
                  style={{ padding: '0 14px', background: 'var(--btn-bg)', color: 'var(--btn-text)', whiteSpace: 'nowrap', borderRadius: '8px' }}
                >
                  확인
                </button>
              </div>
              {errors.verifyCode && <span className="error-msg">{errors.verifyCode}</span>}
            </div>
          )}
          {phoneVerified && <p style={{ color: 'var(--btn-bg)', fontSize: '13px', marginTop: '-10px' }}>✓ 인증이 완료되었습니다.</p>}

          {/* 이메일 */}
          <div className="field">
            <label>이메일 <span style={{ color: 'var(--error)' }}>*</span></label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              placeholder="example@email.com"
            />
            {errors.email && <span className="error-msg">{errors.email}</span>}
          </div>

          {/* 성별 */}
          <div className="field">
            <label>성별</label>
            <select value={form.gender} onChange={(e) => set('gender', e.target.value)}>
              <option value="">선택 안함</option>
              <option value="male">남성</option>
              <option value="female">여성</option>
              <option value="other">기타</option>
            </select>
          </div>

          {/* 생년월일 */}
          <div className="field">
            <label>생년월일</label>
            <input
              type="date"
              value={form.birthday}
              onChange={(e) => set('birthday', e.target.value)}
            />
          </div>

          {/* 약관 */}
          <div className="field">
            <label>약관 동의 <span style={{ color: 'var(--error)' }}>*</span></label>
            <button
              type="button"
              onClick={() => setShowAgreementModal(true)}
              style={{
                padding: '12px 14px',
                background: agreements ? '#f0f4ee' : '#fff',
                border: `1px solid ${agreements ? 'var(--btn-bg)' : 'var(--border)'}`,
                borderRadius: '8px',
                textAlign: 'left',
                color: agreements ? 'var(--btn-bg)' : 'var(--placeholder)',
                fontSize: '14px',
                fontWeight: agreements ? 600 : 400,
              }}
            >
              {agreements ? '✓ 약관 동의 완료' : '약관 동의하기 →'}
            </button>
            {errors.agreements && <span className="error-msg">{errors.agreements}</span>}
          </div>

          {submitError && <p className="error-msg" style={{ textAlign: 'center' }}>{submitError}</p>}

          <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? '처리 중...' : '가입하기'}
          </button>
        </div>
      </div>

      {showAgreementModal && (
        <AgreementModal
          onConfirm={(agreed) => {
            setAgreements(agreed)
            setErrors((e) => ({ ...e, agreements: '' }))
            setShowAgreementModal(false)
          }}
          onClose={() => setShowAgreementModal(false)}
        />
      )}
    </div>
  )
}
