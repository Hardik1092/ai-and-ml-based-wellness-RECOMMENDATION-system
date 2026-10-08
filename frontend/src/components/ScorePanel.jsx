import { Link } from 'react-router-dom'
import {
  Sparkles,
  Salad,
  Flame,
  Droplets,
  Moon,
  PlusCircle,
  HelpCircle
} from 'lucide-react'

const CATEGORY_ICONS = {
  nutrition: Salad,
  activity: Flame,
  hydration: Droplets,
  sleep: Moon,
}

export default function ScorePanel({ score }) {
  if (!score?.available) {
    return (
      <div className="state-container" style={{ padding: '32px 20px', background: 'transparent' }}>
        <div className="state-icon-bubble" style={{ background: 'var(--teal-soft)', color: 'var(--teal)' }}>
          <Sparkles size={26} strokeWidth={2} />
        </div>
        <div className="state-title">No wellness activity yet</div>
        <p className="state-description">
          {score?.message || 'Start logging your daily nutrition, water, sleep and activity to calculate your weekly engagement score.'}
        </p>
        <Link to="/logs" className="topbar-cta-btn" style={{ padding: '8px 18px', fontSize: '0.86rem' }}>
          <PlusCircle size={16} />
          <span>Start logging</span>
        </Link>
      </div>
    )
  }

  const rows = Object.entries(score.categories || {})

  return (
    <div className="score-panel-wrap">
      <div className="score-panel-container">
        {/* Modern Circular Score Badge */}
        <div className="score-ring-wrap">
          <div className="score-circular-badge">
            <span className="score-number">{score.overall}</span>
            <span className="score-total">out of 100</span>
          </div>
          <div className="score-logged-days">
            {score.days_logged} {score.days_logged === 1 ? 'day' : 'days'} logged
          </div>
        </div>

        {/* Categories Breakdown */}
        <div className="score-bars-container">
          {rows.map(([name, item]) => {
            const Icon = CATEGORY_ICONS[name.toLowerCase()] || Sparkles
            const hasVal = item.score !== null && item.score !== undefined
            const val = hasVal ? item.score : 0
            const isWarn = hasVal && val < 60

            return (
              <div className="score-category-row" key={name}>
                <div className="category-name-wrap" title={item.note || ''}>
                  <Icon size={15} style={{ color: isWarn ? 'var(--amber)' : (hasVal ? 'var(--teal)' : 'var(--ink-faint)') }} />
                  <span>{name}</span>
                </div>

                <div className="modern-progress-track">
                  <div
                    className={`modern-progress-fill ${isWarn ? 'warn' : ''}`}
                    style={{ width: hasVal ? `${Math.min(100, Math.max(0, val))}%` : '0%' }}
                  />
                </div>

                <div className="category-score-val" style={{ color: hasVal ? undefined : 'var(--ink-faint)', fontSize: hasVal ? undefined : '0.76rem' }}>
                  {hasVal ? `${val}%` : 'Not logged'}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {score.disclaimer && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 14, fontSize: '0.76rem', color: 'var(--ink-faint)' }}>
          <HelpCircle size={14} />
          <span>{score.disclaimer}</span>
        </div>
      )}
    </div>
  )
}
