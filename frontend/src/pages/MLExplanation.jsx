import { useState } from 'react'
import {
  BrainCircuit,
  Cpu,
  Award,
  TrendingUp,
  Activity,
  Layers,
  Database,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Check,
  Sparkles,
  Sliders
} from 'lucide-react'
import Card from '../components/Card'
import Disclaimer from '../components/Disclaimer'
import Metric from '../components/Metric'
import { EmptyState, ErrorState, Loading } from '../components/States'
import useApi from '../hooks/useApi'
import { api } from '../services/api'

const pretty = (s) => (s || '').replace(/_/g, ' ')

const PIPELINE_STEPS = [
  {
    step: '01',
    title: 'User Profile & Biometrics',
    desc: 'Age, gender, BMI, dietary preference, allergens, and metabolic parameters are ingested.',
    icon: Database,
  },
  {
    step: '02',
    title: 'Data Preprocessing',
    desc: 'Inputs are checked against application bounds; missing log entries use documented defaults.',
    icon: Sliders,
  },
  {
    step: '03',
    title: 'Feature Engineering',
    desc: '14 numeric features describe the profile, including ratios, indicators and category codes.',
    icon: Activity,
  },
  {
    step: '04',
    title: 'ML Focus Classification',
    desc: 'The configured model predicts a synthetic wellness focus category and model probabilities.',
    icon: Cpu,
  },
  {
    step: '05',
    title: 'Deterministic Safety Filter',
    desc: 'Configured rules filter recorded preferences and exclusions; clinical safety is not established.',
    icon: ShieldCheck,
  },
  {
    step: '06',
    title: 'Personalised Ranking',
    desc: 'Approved meals, workouts, and wellness habits are scored and ranked for your daily plan.',
    icon: Sparkles,
  },
]

export default function MLExplanation() {
  const { data, error, loading, reload } = useApi(() => api.mlExplanation(), [])

  if (loading) return <Loading label="Retrieving model parameters and evaluation results…" />
  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={reload}
        title="Unable to load model information"
        description="Please try again. If the machine learning service was recently restarted, it may take a few moments to re-synchronise."
      />
    )
  }

  // Model status checks
  const isOnline = Boolean(data?.service_online)
  const isLoaded = Boolean(data?.model_loaded || data?.model_type)
  const isModelActive = Boolean(data?.model_available)
  const isFallbackActive = !isModelActive

  // Feature importances
  const importances = Array.isArray(data?.feature_importances) ? data.feature_importances : []
  const maxImportance = importances.length > 0 ? Math.max(...importances.map((f) => f.importance || 0)) : 1

  // Format metric helpers (truthful fallbacks - never fake numerical zeros or raw undefined)
  const formatAccuracy = () => {
    if (data?.metrics?.accuracy != null && typeof data.metrics.accuracy === 'number') {
      return `${(data.metrics.accuracy * 100).toFixed(1)}%`
    }
    return 'Not available'
  }

  const formatF1 = () => {
    if (data?.metrics?.f1 != null && typeof data.metrics.f1 === 'number') {
      return data.metrics.f1.toFixed(2)
    }
    return 'Not available'
  }

  const formatPrecisionRecall = () => {
    if (
      data?.metrics?.precision != null &&
      data?.metrics?.recall != null &&
      typeof data.metrics.precision === 'number' &&
      typeof data.metrics.recall === 'number'
    ) {
      return `${(data.metrics.precision * 100).toFixed(0)}% / ${(data.metrics.recall * 100).toFixed(0)}%`
    }
    return 'Not available'
  }

  const modelArchitectureDisplay = data?.model_architecture || data?.model_type || 'Not available'
  const trainingSamplesNote = data?.n_samples != null || data?.training_samples != null
    ? `${(data.n_samples || data.training_samples).toLocaleString()} training samples`
    : 'Not available'

  return (
    <div className="ml-page-wrapper">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">How the Model Decides</h1>
          <p className="page-subtitle">
            See how your general wellness recommendations are generated. Synthetic-data results do not establish clinical validity.
          </p>
        </div>

        {/* Truthful Model Status Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {isModelActive ? (
            <span className="pill ok" style={{ padding: '6px 14px', fontSize: '0.82rem', fontWeight: 600 }}>
              <span className="pill-dot" style={{ background: '#10b981' }} />
              <span>Model Ready</span>
            </span>
          ) : (
            <span className="pill warn" style={{ padding: '6px 14px', fontSize: '0.82rem', fontWeight: 600 }}>
              <span className="pill-dot" style={{ background: '#f59e0b' }} />
              <span>Model Unavailable (Rules Active)</span>
            </span>
          )}
        </div>
      </div>

      {/* Fallback Notice when ML is unavailable */}
      {isFallbackActive && (
        <div
          className="card"
          style={{
            marginBottom: 24,
            borderColor: 'rgba(245, 158, 11, 0.4)',
            background: 'rgba(245, 158, 11, 0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
            <AlertTriangle size={22} style={{ color: '#f59e0b', flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.98rem', color: '#f59e0b', marginBottom: 4 }}>
                Rule-Based Recommendations Active
              </div>
              <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--ink-soft)', lineHeight: 1.5 }}>
                {data?.fallback_reason || 'The recommendation engine is currently using the configured fallback rules.'}{' '}
                Configured rules remain active. Check recommendations against your needs; they do not replace professional advice.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 4 Premium Metric Cards */}
      <div className="grid cols-4">
        <Metric
          label="Model Architecture"
          value={modelArchitectureDisplay}
          note={trainingSamplesNote}
          icon={Cpu}
          variant="teal"
        />
        <Metric
          label="Test Accuracy"
          value={formatAccuracy()}
          note="Held-out synthetic test split"
          icon={Award}
          variant="emerald"
        />
        <Metric
          label="F1 Score"
          value={formatF1()}
          note="Weighted average across classes"
          icon={TrendingUp}
          variant="indigo"
        />
        <Metric
          label="Precision / Recall"
          value={formatPrecisionRecall()}
          note="Weighted precision and recall"
          icon={Activity}
          variant="blue"
        />
      </div>

      <div style={{ height: 28 }} />

      {/* Visual Recommendation Pipeline Architecture */}
      <Card
        title="Recommendation Pipeline Architecture"
        sub="The flow combining machine learning with configured wellness rules"
        icon={BrainCircuit}
      >
        <div className="ml-pipeline-grid">
          {PIPELINE_STEPS.map((step, idx) => {
            const Icon = step.icon
            return (
              <div key={step.step} className="ml-pipeline-step">
                <div className="ml-pipeline-step-header">
                  <div className="ml-pipeline-step-badge">{step.step}</div>
                  <div className="ml-pipeline-step-icon-wrap">
                    <Icon size={16} />
                  </div>
                </div>
                <div className="ml-pipeline-step-title">{step.title}</div>
                <div className="ml-pipeline-step-desc">{step.desc}</div>
                {idx < PIPELINE_STEPS.length - 1 && (
                  <div className="ml-pipeline-connector">
                    <ArrowRight size={14} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </Card>

      <div style={{ height: 28 }} />

      {/* Feature Importance Hierarchy */}
      <Card
        title="Feature Importance Hierarchy"
        sub="Global importance, when supported by the model; not an individual causal explanation"
        icon={Layers}
      >
        {importances.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {importances.map((f, index) => {
              const rawPct = (f.importance || 0) * 100
              const barWidth = maxImportance > 0 ? Math.min(100, Math.max(4, (f.importance / maxImportance) * 100)) : 0

              return (
                <div className="imp-row-modern" key={f.feature || index}>
                  <div className="imp-name-col">
                    <span className="imp-name-text" title={f.description}>
                      {pretty(f.feature)}
                    </span>
                    {f.description && <span className="imp-sub-desc">{f.description}</span>}
                  </div>

                  <div className="imp-bar-container">
                    <div
                      className="imp-bar-fill"
                      style={{
                        width: `${barWidth}%`,
                        background: 'linear-gradient(90deg, rgba(5, 150, 105, 0.85) 0%, rgba(16, 185, 129, 1) 100%)',
                      }}
                    />
                  </div>

                  <div className="imp-value-col">
                    <span className="imp-val-badge">
                      {rawPct.toFixed(1)}%
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <EmptyState
            icon={Layers}
            title="Feature importance is currently unavailable for this model"
            description="Some models do not expose impurity-based feature importances. Their absence does not mean prediction is unavailable."
          />
        )}
      </Card>

      <div style={{ height: 28 }} />

      {/* Current User Prediction & Inference */}
      <Card
        title="Your Wellness Focus Prediction"
        sub="Inferred primary focus category based on your 14 personal biometric parameters"
        icon={BrainCircuit}
      >
        {data?.prediction?.available ? (
          <>
            <div className="why-box" style={{ marginTop: 0, marginBottom: 20 }}>
              <BrainCircuit size={20} className="why-icon" />
              <div className="why-content">
                <div>
                  Primary focus predicted:{' '}
                  <span className="pill ok" style={{ textTransform: 'capitalize', margin: '0 6px', fontWeight: 700 }}>
                    {pretty(data.prediction.category_label || data.prediction.category)}
                  </span>{' '}
                  with <strong>{Math.round((data.prediction.confidence || 0) * 100)}% model probability</strong> (not clinical confidence).
                </div>
                {data.prediction.explanation && (
                  <div style={{ marginTop: 6, fontSize: '0.84rem', color: 'var(--ink-soft)' }}>
                    {data.prediction.explanation}
                  </div>
                )}
              </div>
            </div>

            <h3 style={{ fontSize: '0.94rem', marginBottom: 12, fontWeight: 700 }}>
              Model probability distribution across wellness categories
            </h3>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Category</th>
                    <th style={{ width: '45%' }}>Probability Distribution</th>
                    <th className="num">Model Probability</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.prediction.probabilities || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([name, p]) => (
                      <tr key={name}>
                        <td style={{ textTransform: 'capitalize', fontWeight: 600 }}>{pretty(name)}</td>
                        <td>
                          <div className="modern-progress-track" style={{ height: 8 }}>
                            <div
                              className="modern-progress-fill"
                              style={{
                                width: `${Math.round(p * 100)}%`,
                                background: 'linear-gradient(90deg, #059669, #10b981)',
                              }}
                            />
                          </div>
                        </td>
                        <td className="num" style={{ fontWeight: 700, color: '#10b981' }}>
                          {(p * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <EmptyState
            icon={BrainCircuit}
            title="Deterministic Safety Mode Active"
            description={
              data?.prediction?.reason ||
              'Recommendations are currently guided by configured wellness rules and profile targets.'
            }
          />
        )}
      </Card>

      <div style={{ height: 28 }} />

      {/* Profile Features Input Vector */}
      <Card
        title="Features Derived from Your Profile"
        sub="The 14 engineered values supplied to the classifier; these use different units and scales"
        icon={Cpu}
      >
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Feature Name</th>
                <th className="num">Feature Value</th>
                <th>Feature Description</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data?.your_features || {}).map(([name, value]) => (
                <tr key={name}>
                  <td style={{ textTransform: 'capitalize', fontWeight: 600 }}>{pretty(name)}</td>
                  <td className="num" style={{ fontWeight: 700, color: 'var(--teal)' }}>
                    {typeof value === 'number' ? value.toFixed(2) : (value ?? '—')}
                  </td>
                  <td style={{ color: 'var(--ink-soft)', fontSize: '0.82rem' }}>
                    {data?.feature_descriptions?.[name] || 'Derived health feature'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Dataset & Training Provenance */}
      <div style={{ height: 28 }} />
      <Card
        title="Training Dataset & Provenance"
        sub="Audit trail and hyperparameters for model validation"
        icon={Database}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--ink)' }}>
            <strong>Data Source:</strong> {data?.data_source || 'Data source unavailable'}
          </p>
          <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--ink-soft)' }}>
            <strong>Last Trained:</strong>{' '}
            {data?.trained_at ? new Date(data.trained_at).toLocaleString() : 'System default release'}
          </p>
          <div
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--r-md)',
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              fontSize: '0.82rem',
              color: 'var(--ink-soft)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <ShieldCheck size={18} style={{ color: '#10b981', flexShrink: 0 }} />
            <span>
              <strong>General wellness only:</strong> Model categories support ranking alongside configured filters. They are not diagnoses, and these filters do not establish medical safety.
            </span>
          </div>
        </div>
      </Card>

      <Disclaimer />
    </div>
  )
}
