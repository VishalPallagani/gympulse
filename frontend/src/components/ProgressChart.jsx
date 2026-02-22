import { useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

function formatDate(date) {
  return new Date(date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function ProgressChart({ progress }) {
  const exerciseNames = useMemo(() => Object.keys(progress || {}), [progress]);
  const [selectedExercise, setSelectedExercise] = useState(exerciseNames[0] ?? '');

  const activeExercise = selectedExercise || exerciseNames[0] || '';
  const lineData = progress?.[activeExercise] || [];

  const delta = useMemo(() => {
    if (lineData.length < 2) {
      return null;
    }
    const latest = Number(lineData[lineData.length - 1]?.max_weight || 0);
    const previous = Number(lineData[lineData.length - 2]?.max_weight || 0);
    const diff = Number((latest - previous).toFixed(2));
    return diff;
  }, [lineData]);

  if (!exerciseNames.length) {
    return (
      <section id="progress" className="apple-card p-4 sm:p-6">
        <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Progressive Overload</h2>
        <p className="mt-4 text-zinc-400">Log weighted exercises to unlock your strength trendline.</p>
      </section>
    );
  }

  return (
    <section id="progress" className="apple-card p-4 sm:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Progressive Overload</h2>
          <p className="mt-1 text-sm text-zinc-400">Smoothed max load curve for each exercise.</p>
        </div>
        <select
          value={activeExercise}
          onChange={(event) => setSelectedExercise(event.target.value)}
          className="w-full rounded-xl border border-white/10 bg-panel px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none md:w-auto"
        >
          {exerciseNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {delta !== null ? (
        <p
          className={`mt-3 inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${
            delta > 0
              ? 'border-mint/40 bg-mint/10 text-mint'
              : delta < 0
              ? 'border-rose/40 bg-rose/10 text-rose'
              : 'border-white/20 bg-white/5 text-zinc-300'
          }`}
        >
          {delta > 0 ? '+' : ''}
          {delta}kg vs previous session
        </p>
      ) : null}

      <div className="mt-6 h-64 w-full sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={lineData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="progressFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#FF4FD8" stopOpacity={0.42} />
                <stop offset="95%" stopColor="#FF4FD8" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
            <XAxis dataKey="date" tickFormatter={formatDate} stroke="#A1A1AA" tick={{ fontSize: 11 }} minTickGap={22} />
            <YAxis stroke="#A1A1AA" tick={{ fontSize: 12 }} unit="kg" />
            <Tooltip
              cursor={{ stroke: '#FF4FD8', strokeWidth: 1 }}
              contentStyle={{
                background: 'rgba(7,10,16,0.96)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '14px'
              }}
              labelFormatter={(value) => formatDate(value)}
              formatter={(value) => [`${value} kg`, 'Max Weight']}
            />
            <Area
              type="monotone"
              dataKey="max_weight"
              stroke="#FF4FD8"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#progressFill)"
              dot={{ fill: '#FF4FD8', strokeWidth: 0, r: 3 }}
              activeDot={{ r: 5, fill: '#22D3EE' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
