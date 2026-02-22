import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const COLORS = {
  Chest: '#FF4FD8',
  Back: '#2EE6A6',
  Shoulders: '#8B5CF6',
  Biceps: '#FFB703',
  Triceps: '#FB7185',
  Legs: '#22D3EE',
  Core: '#C084FC',
  Cardio: '#38BDF8',
  'Full Body': '#F97316'
};

const MUSCLE_KEYS = Object.keys(COLORS);

function formatWeek(value) {
  const date = new Date(value);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function VolumeChart({ weeklyVolume }) {
  if (!weeklyVolume?.length) {
    return (
      <section id="volume" className="apple-card p-4 sm:p-6">
        <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Weekly Volume</h2>
        <p className="mt-4 text-zinc-400">Log sessions to see your stacked muscle-group volume profile.</p>
      </section>
    );
  }

  return (
    <section id="volume" className="apple-card p-4 sm:p-6">
      <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Weekly Volume Intelligence</h2>
      <p className="mt-1 text-sm text-zinc-400">Stacked muscle contribution with total weekly trend overlay.</p>
      <div className="mt-6 h-72 w-full sm:h-[24rem]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={weeklyVolume} margin={{ top: 8, right: 18, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="week_start" stroke="#A1A1AA" tickFormatter={formatWeek} tick={{ fontSize: 11 }} minTickGap={20} />
            <YAxis stroke="#A1A1AA" tick={{ fontSize: 11 }} unit="kg" />
            <Tooltip
              contentStyle={{
                background: 'rgba(7,10,16,0.96)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '14px'
              }}
              labelFormatter={(value) => `Week of ${formatWeek(value)}`}
            />
            {MUSCLE_KEYS.map((key) => (
              <Bar key={key} dataKey={key} stackId="weekly" fill={COLORS[key]} radius={[4, 4, 0, 0]} />
            ))}
            <Line
              type="monotone"
              dataKey="total"
              stroke="#F8FAFC"
              strokeWidth={2}
              dot={{ r: 2, fill: '#F8FAFC' }}
              activeDot={{ r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-zinc-300">
        {MUSCLE_KEYS.map((key) => (
          <span key={key} className="inline-flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[key] }} />
            {key}
          </span>
        ))}
      </div>
    </section>
  );
}
