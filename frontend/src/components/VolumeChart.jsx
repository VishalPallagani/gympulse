import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const COLORS = {
  Chest: '#5AC8FA',
  Back: '#34D399',
  Shoulders: '#A78BFA',
  Biceps: '#F59E0B',
  Triceps: '#FB7185',
  Legs: '#22D3EE',
  Core: '#C4B5FD',
  Cardio: '#60A5FA',
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
      <section id="volume" className="apple-card p-6">
        <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Weekly Volume</h2>
        <p className="mt-4 text-zinc-400">Log sessions to see your stacked muscle-group volume profile.</p>
      </section>
    );
  }

  return (
    <section id="volume" className="apple-card p-6">
      <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Weekly Volume Intelligence</h2>
      <p className="mt-1 text-sm text-zinc-400">Stacked muscle contribution with total weekly trend overlay.</p>
      <div className="mt-6 h-[24rem] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={weeklyVolume} margin={{ top: 8, right: 18, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="week_start" stroke="#A1A1AA" tickFormatter={formatWeek} tick={{ fontSize: 12 }} />
            <YAxis stroke="#A1A1AA" tick={{ fontSize: 12 }} unit="kg" />
            <Tooltip
              contentStyle={{
                background: 'rgba(7,10,16,0.96)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '14px'
              }}
              labelFormatter={(value) => `Week of ${formatWeek(value)}`}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
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
    </section>
  );
}
