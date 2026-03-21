import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { changeCharacter, getMyCharacter, selectCharacter } from '../apis/characterApi'
import { useAuthStore } from '../store/authStore'

import chamkkaeImg from '../assets/images/chatbots/chamkkae-removebg.png'
import deulkkaeImg from '../assets/images/chatbots/deulkkae-removebg.png'
import heukkkaeImg from '../assets/images/chatbots/heukkkae-removebg.png'
import tongkkaeImg from '../assets/images/chatbots/tongkkae-removebg.png'

const CHARACTERS = [
  { id: 1, name: '참깨', description: '걱정을 먼저 알아채고\n한없이 보살펴주는 친구', image: chamkkaeImg },
  { id: 2, name: '들깨', description: '하나부터 열까지\n차근차근 알려주는 친구', image: deulkkaeImg },
  { id: 3, name: '흑깨', description: '밝고 긍정적이면서\n웃음을 건네는 친구', image: heukkkaeImg },
  { id: 4, name: '통깨', description: '귀엽고 공감 리액션으로\n기분을 밝혀주는 친구', image: tongkkaeImg },
]

export default function CharacterSelectPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  const setSelectedCharacter = useAuthStore((s) => s.setSelectedCharacter)

  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [initialId, setInitialId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getMyCharacter()
      .then((data) => {
        setSelectedId(data.character_id)
        setInitialId(data.character_id)
      })
      .catch(() => {})
  }, [])

  const selectedChar = CHARACTERS.find((c) => c.id === selectedId)

  const handleConfirm = async () => {
    if (!selectedId || !selectedChar) return
    setLoading(true)
    setError('')
    try {
      const isNew = initialId === null
      const result = isNew
        ? await selectCharacter(selectedId)
        : await changeCharacter(selectedId)
      setSelectedCharacter({ id: result.character_id, name: result.name, imageUrl: selectedChar.image })
      navigate(from === 'mypage' ? '/mypage' : '/main', { replace: true })
    } catch (e: unknown) {
      const err = e as { detail?: string }
      setError(err.detail ?? '오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="character-select-page">
      <header className="cs-header" style={{ position: 'relative' }}>
        {from === 'mypage' && (
          <button
            type="button"
            onClick={() => navigate('/mypage')}
            style={{ position: 'absolute', top: 16, left: 16, zIndex: 1 }}
          >
            ← 뒤로
          </button>
        )}
        <p className="cs-main-copy">
          오늘부터 마음을 나눌<br />다정한 친구를 골라주세요
        </p>
        <p className="cs-sub-copy">
          하루를 함께 기록하고 기분을<br />다정하게 들어줄 단 한 명의 친구
        </p>
        {selectedChar && (
          <span className="cs-badge">현재 함께하는 친구: {selectedChar.name}</span>
        )}
      </header>

      <main className="cs-grid">
        {CHARACTERS.map((char, i) => (
          <div
            key={char.id}
            className={`cs-card${selectedId === char.id ? ' selected' : ''}`}
            style={{ animationDelay: `${0.05 + i * 0.05}s` }}
            role="radio"
            aria-checked={selectedId === char.id}
            tabIndex={0}
            onClick={() => setSelectedId(char.id)}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setSelectedId(char.id)}
          >
            <img src={char.image} alt={`${char.name} 캐릭터`} width={96} height={96} />
            <span className="cs-card-name">{char.name}</span>
            <span className="cs-card-desc">{char.description}</span>
            {selectedId === char.id && <span className="cs-card-check">✓ 선택됨</span>}
          </div>
        ))}
      </main>

      <footer className="cs-footer">
        {error && <p className="error-msg" style={{ textAlign: 'center', marginBottom: 8 }}>{error}</p>}
        <button
          className="cs-confirm-btn"
          onClick={handleConfirm}
          disabled={!selectedId || loading}
          aria-disabled={!selectedId}
        >
          {loading ? '처리 중...' : selectedChar ? `${selectedChar.name}와 함께하기` : '친구를 선택해주세요'}
        </button>
      </footer>
    </div>
  )
}
