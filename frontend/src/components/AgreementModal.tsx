import { useState, useEffect } from 'react'
import type { AgreementState } from '../types/auth'

interface Props {
  onConfirm: (state: Omit<AgreementState, 'all'>) => void
  onClose: () => void
}

const TERMS = [
  {
    key: 'terms_of_service' as const,
    label: '이용약관 동의',
    required: true,
    content: `제1조 (목적)\n본 약관은 도닥톡 서비스 이용에 관한 조건 및 절차, 회사와 이용자의 권리·의무 및 책임사항을 규정함을 목적으로 합니다.\n\n제2조 (정의)\n"서비스"란 회사가 제공하는 정신 건강 상담 및 위로 서비스를 의미합니다.\n\n제3조 (약관의 효력)\n본 약관은 서비스 화면에 게시하거나 기타 방법으로 이용자에게 공지함으로써 효력이 발생합니다.`,
  },
  {
    key: 'privacy_policy' as const,
    label: '개인정보 수집 및 이용 동의',
    required: true,
    content: `수집 항목: 닉네임, 이메일, 전화번호, 성별, 생년월일\n\n수집 목적: 회원 식별, 서비스 제공, 고객 지원\n\n보유 기간: 회원 탈퇴 시까지 (단, 관련 법령에 따라 일정 기간 보관)\n\n귀하는 개인정보 수집·이용에 동의하지 않을 권리가 있으나, 거부 시 서비스 이용이 제한될 수 있습니다.`,
  },
  {
    key: 'sensitive_policy' as const,
    label: '민감정보 수집 및 이용 동의',
    required: true,
    sensitive: true,
    content: `수집 항목: 정신 건강 관련 상담 내용\n\n수집 목적: 맞춤형 정신 건강 서비스 제공\n\n보유 기간: 회원 탈퇴 후 즉시 파기\n\n민감정보는 암호화되어 저장되며, 제3자에게 제공되지 않습니다.\n귀하는 민감정보 수집·이용에 동의하지 않을 권리가 있으나, 거부 시 핵심 서비스 이용이 제한됩니다.`,
  },
  {
    key: 'sms_agreed' as const,
    label: '문자 알림 수신 동의',
    required: false,
    content: '수신 항목: 복약 알림\n\n발송 목적: 복약 시간 안내 문자 발송\n\n보유 기간: 동의 철회 시까지\n\n본 동의는 선택사항으로, 동의하지 않으셔도 서비스 이용에는 제한이 없습니다.\n\n동의 여부 및 알림 설정은 마이페이지에서 언제든지 변경 또는 철회하실 수 있습니다.',
  },
  {
    key: 'terms_of_marketing' as const,
    label: '마케팅 및 이벤트 정보 수신 동의',
    required: false,
    content: `수집 항목: 이메일, 전화번호\n\n활용 목적: 신규 서비스 안내, 이벤트 및 프로모션 정보 발송\n\n보유 기간: 동의 철회 시까지\n\n본 동의는 선택사항으로, 동의하지 않아도 서비스 이용에 제한이 없습니다.`,
  },
]

const INITIAL: AgreementState = {
  terms_of_service: false,
  privacy_policy: false,
  sensitive_policy: false,
  sms_agreed: false,
  terms_of_marketing: false,
  all: false,
}

export default function AgreementModal({ onConfirm, onClose }: Props) {
  const [state, setState] = useState<AgreementState>(INITIAL)
  const [detailKey, setDetailKey] = useState<string | null>(null)
  const [error, setError] = useState('')

  const requiredDone = state.terms_of_service && state.privacy_policy && state.sensitive_policy

  useEffect(() => {
    const all = requiredDone && state.sms_agreed && state.terms_of_marketing
    setState((s) => ({ ...s, all }))
  }, [state.terms_of_service, state.privacy_policy, state.sensitive_policy, state.sms_agreed, state.terms_of_marketing])

  const toggleAll = (checked: boolean) =>
    setState({
      terms_of_service: checked,
      privacy_policy: checked,
      sensitive_policy: checked,
      sms_agreed: checked,
      terms_of_marketing: checked,
      all: checked,
    })

  const toggle = (key: keyof Omit<AgreementState, 'all'>, checked: boolean) => {
    setState((s) => ({ ...s, [key]: checked }))
    setError('')
  }

  const handleConfirm = () => {
    if (!requiredDone) { setError('필수 약관에 모두 동의해주세요.'); return }
    const { all: _, ...rest } = state
    onConfirm(rest)
  }

  const detailTerm = TERMS.find((t) => t.key === detailKey)

  return (
    <>
      {/* 약관 동의 모달 */}
      <div style={overlay} onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-label="약관 동의" style={modal}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 700 }}>약관 동의</h2>
          <button onClick={onClose} style={{ background: 'none', fontSize: '20px', color: 'var(--placeholder)', padding: '4px 8px' }}>✕</button>
        </div>

        {/* 전체 동의 */}
        <label style={rowStyle}>
          <input type="checkbox" checked={state.all} onChange={(e) => toggleAll(e.target.checked)} style={{ width: 'auto', accentColor: 'var(--btn-bg)' }} />
          <span style={{ fontWeight: 700, fontSize: '15px' }}>전체 동의</span>
        </label>

        <hr style={{ borderColor: 'var(--border)', margin: '12px 0' }} />

        {/* 스크롤 영역 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '280px', overflowY: 'auto', paddingRight: '4px' }}>
          {TERMS.map(({ key, label, required, sensitive }) => (
            <div key={key} style={rowStyle}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={state[key]}
                  onChange={(e) => toggle(key, e.target.checked)}
                  style={{ width: 'auto', accentColor: 'var(--btn-bg)' }}
                />
                <span style={{ fontSize: '14px' }}>
                  {label}
                  {sensitive && <span style={{ color: 'var(--error)', fontSize: '12px', marginLeft: '4px' }}>⚠</span>}
                  <span style={{ color: required ? 'var(--error)' : 'var(--placeholder)', fontSize: '12px', marginLeft: '4px' }}>
                    ({required ? '필수' : '선택'})
                  </span>
                </span>
              </label>
              <button
                onClick={() => setDetailKey(key)}
                style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '4px', padding: '2px 8px', fontSize: '12px', color: 'var(--placeholder)', flexShrink: 0 }}
              >
                보기
              </button>
            </div>
          ))}
        </div>

        {error && <p className="error-msg" style={{ marginTop: '12px' }}>{error}</p>}

        <button
          onClick={handleConfirm}
          disabled={!requiredDone}
          className="btn-primary"
          style={{ marginTop: '20px' }}
        >
          동의하고 계속하기
        </button>
      </div>

      {/* 약관 상세 모달 */}
      {detailTerm && (
        <>
          <div style={{ ...overlay, zIndex: 1100 }} onClick={() => setDetailKey(null)} aria-hidden="true" />
          <div role="dialog" aria-modal="true" aria-label={detailTerm.label} style={{ ...modal, zIndex: 1101, maxHeight: '70vh' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700 }}>{detailTerm.label}</h3>
              <button onClick={() => setDetailKey(null)} style={{ background: 'none', fontSize: '20px', color: 'var(--placeholder)', padding: '4px 8px' }}>✕</button>
            </div>
            <div style={{ overflowY: 'auto', flex: 1, fontSize: '14px', lineHeight: 1.8, color: 'var(--text)', whiteSpace: 'pre-wrap', maxHeight: '50vh' }}>
              {detailTerm.content}
            </div>
            <button onClick={() => setDetailKey(null)} className="btn-primary" style={{ marginTop: '16px' }}>확인</button>
          </div>
        </>
      )}
    </>
  )
}

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 1000,
}

const modal: React.CSSProperties = {
  position: 'fixed',
  top: '50%', left: '50%',
  transform: 'translate(-50%, -50%)',
  background: '#fff',
  borderRadius: '16px',
  padding: '28px 24px',
  width: 'min(480px, calc(100vw - 32px))',
  zIndex: 1001,
  display: 'flex',
  flexDirection: 'column',
}

const rowStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px',
}
