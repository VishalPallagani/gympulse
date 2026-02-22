function scoreTone(score) {
  if (score >= 75) {
    return 'text-mint';
  }
  if (score >= 50) {
    return 'text-accent';
  }
  return 'text-blaze';
}

function formatPercent(value) {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return 'N/A';
  }
  return `${parsed > 0 ? '+' : ''}${parsed.toFixed(1)}%`;
}

function ScoreCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
      <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">{label}</p>
      <p className={`mt-2 font-display text-4xl font-bold ${scoreTone(Number(value) || 0)}`}>{value}</p>
      <div className="mt-3 h-1.5 rounded-full bg-white/10">
        <div
          className="h-1.5 rounded-full bg-gradient-to-r from-cyan via-accent to-violet"
          style={{ width: `${Math.min(Math.max(Number(value) || 0, 0), 100)}%` }}
        />
      </div>
    </div>
  );
}

function MetaRow({ label, value, tone = 'text-zinc-100' }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm">
      <span className="text-zinc-400">{label}</span>
      <span className={`font-medium ${tone}`}>{value}</span>
    </div>
  );
}

export default function InsightsPanel({ coachInsights, bodyWeight }) {
  const insights = coachInsights || {};
  const undertrained = insights.undertrained_groups || [];
  const recommendation = insights.recommendation || 'Log more sessions to unlock personalized recommendations.';

  return (
    <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_1fr]" id="insights">
      <article className="apple-card p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">Coach Dashboard</p>
            <h2 className="mt-1 font-display text-3xl font-semibold text-white md:text-4xl">Performance Signals</h2>
          </div>
          <p className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs uppercase tracking-[0.16em] text-zinc-400">
            Last 30 days
          </p>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
          <ScoreCard label="Consistency" value={insights.consistency_score || 0} />
          <ScoreCard label="Progression" value={insights.progression_score || 0} />
          <ScoreCard label="Balance" value={insights.balance_score || 0} />
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
          <MetaRow label="Sessions this week" value={insights.sessions_7d ?? 0} />
          <MetaRow label="Volume vs last week" value={formatPercent(insights.weekly_volume_trend_pct)} />
          <MetaRow label="Push/Pull ratio (30d)" value={insights.push_pull_ratio_30d ?? 'N/A'} />
          <MetaRow label="Leg volume share (30d)" value={`${Number(insights.leg_share_pct_30d || 0).toFixed(1)}%`} />
          <MetaRow label="Weight adherence (30d)" value={`${Math.round(Number(insights.body_weight_adherence_30d_pct || 0))}%`} />
          <MetaRow label="Top muscle focus" value={insights.top_muscle_group_30d || 'N/A'} />
        </div>
      </article>

      <article className="apple-card p-6">
        <p className="text-xs uppercase tracking-[0.22em] text-zinc-400">Action Plan</p>
        <p className="mt-3 rounded-2xl border border-accent/30 bg-accent/10 px-4 py-3 text-sm leading-relaxed text-zinc-100">
          {recommendation}
        </p>

        <div className="mt-4 space-y-3">
          <MetaRow label="Exercises tracked" value={insights.tracked_exercises ?? 0} />
          <MetaRow label="Exercises improving" value={insights.improving_exercises ?? 0} tone="text-mint" />
          <MetaRow
            label="Best progression"
            value={
              insights.best_progression_exercise
                ? `${insights.best_progression_exercise} (+${Number(insights.best_progression_delta_kg || 0).toFixed(1)}kg)`
                : 'N/A'
            }
            tone="text-accent"
          />
          <MetaRow
            label="Latest bodyweight"
            value={bodyWeight?.latest_weight_kg ? `${Number(bodyWeight.latest_weight_kg).toFixed(1)}kg` : 'Not logged'}
          />
        </div>

        <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Undertrained Groups</p>
          {undertrained.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {undertrained.map((group) => (
                <span key={group} className="rounded-full border border-blaze/40 bg-blaze/10 px-3 py-1 text-xs text-blaze">
                  {group}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-zinc-400">Coverage is solid across all groups.</p>
          )}
        </div>
      </article>
    </section>
  );
}
