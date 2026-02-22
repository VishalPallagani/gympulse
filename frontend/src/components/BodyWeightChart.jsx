import { Area, AreaChart, CartesianGrid, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

function formatDate(dateValue) {
  return new Date(dateValue).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function metricTone(value) {
  if (value === null || value === undefined) {
    return 'text-zinc-300';
  }
  if (Number(value) > 0) {
    return 'text-blaze';
  }
  if (Number(value) < 0) {
    return 'text-mint';
  }
  return 'text-zinc-300';
}

function MetricPill({ label, value, tone = 'text-white' }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.18em] text-zinc-400">{label}</p>
      <p className={`mt-1 font-display text-xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

export default function BodyWeightChart({ bodyWeight, coachInsights }) {
  const series = bodyWeight?.series || [];
  const latest = bodyWeight?.latest_weight_kg;
  const deltaLast = bodyWeight?.delta_vs_last_log_kg;
  const delta7d = bodyWeight?.delta_7d_kg;
  const avg7d = bodyWeight?.avg_7d_kg;
  const adherence = bodyWeight?.adherence_30d_pct ?? 0;
  const logs30d = bodyWeight?.logs_30d ?? 0;

  if (!series.length) {
    return (
      <section id="bodyweight" className="apple-card p-6">
        <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Bodyweight Trend</h2>
        <p className="mt-2 text-sm text-zinc-400">
          Send a daily check-in like <span className="text-white">'weight 78.4kg'</span> to unlock trend, adherence, and cut/bulk signal.
        </p>
        <div className="mt-5 rounded-2xl border border-dashed border-white/20 bg-black/25 p-5">
          <p className="text-zinc-300">No bodyweight logs yet.</p>
          <p className="mt-2 text-sm text-zinc-400">
            Coach tip: morning, post-bathroom, pre-meal weigh-ins produce the cleanest trendline.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section id="bodyweight" className="apple-card p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Bodyweight Trend</h2>
          <p className="mt-1 text-sm text-zinc-400">Daily scale trend from WhatsApp check-ins.</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/25 px-4 py-2">
          <p className="text-[10px] uppercase tracking-[0.18em] text-zinc-400">Coach Signal</p>
          <p className="mt-1 text-sm text-zinc-200">
            {coachInsights?.body_weight_adherence_30d_pct >= 70
              ? 'Excellent weigh-in consistency'
              : 'Log daily to improve coaching accuracy'}
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 xl:grid-cols-5">
        <MetricPill label="Latest" value={`${Number(latest).toFixed(1)}kg`} tone="text-accent" />
        <MetricPill
          label="Vs Last Log"
          value={deltaLast === null || deltaLast === undefined ? 'N/A' : `${deltaLast > 0 ? '+' : ''}${Number(deltaLast).toFixed(1)}kg`}
          tone={metricTone(deltaLast)}
        />
        <MetricPill
          label="7-Day"
          value={delta7d === null || delta7d === undefined ? 'N/A' : `${delta7d > 0 ? '+' : ''}${Number(delta7d).toFixed(1)}kg`}
          tone={metricTone(delta7d)}
        />
        <MetricPill label="Avg 7-Day" value={avg7d ? `${Number(avg7d).toFixed(1)}kg` : 'N/A'} tone="text-violet" />
        <MetricPill label="30-Day Adherence" value={`${Math.round(Number(adherence) || 0)}%`} tone="text-mint" />
      </div>

      <div className="mt-6 h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series} margin={{ top: 8, right: 16, left: -12, bottom: 4 }}>
            <defs>
              <linearGradient id="weightFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#A78BFA" stopOpacity={0.42} />
                <stop offset="95%" stopColor="#A78BFA" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="date" tickFormatter={formatDate} stroke="#A1A1AA" tick={{ fontSize: 12 }} />
            <YAxis stroke="#A1A1AA" tick={{ fontSize: 12 }} unit="kg" domain={['dataMin - 1', 'dataMax + 1']} />
            <Tooltip
              contentStyle={{
                background: 'rgba(7,10,16,0.96)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '14px'
              }}
              labelFormatter={(value) => formatDate(value)}
              formatter={(value) => [`${Number(value).toFixed(1)} kg`, 'Bodyweight']}
            />
            {avg7d ? <ReferenceLine y={avg7d} stroke="rgba(52,211,153,0.8)" strokeDasharray="5 5" /> : null}
            <Area type="monotone" dataKey="weight_kg" fill="url(#weightFill)" stroke="transparent" />
            <Line
              type="monotone"
              dataKey="weight_kg"
              stroke="#A78BFA"
              strokeWidth={3}
              dot={{ r: 2, fill: '#A78BFA' }}
              activeDot={{ r: 5, fill: '#5AC8FA' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-2 text-xs uppercase tracking-[0.14em] text-zinc-500">
        {logs30d} check-ins recorded in the last 30 days
      </p>
    </section>
  );
}
