import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart as RechartsRadarChart,
  ResponsiveContainer,
  Tooltip
} from 'recharts';

function toChartData(radarData) {
  return (radarData || []).map((row) => ({
    muscle_group: row.muscle_group,
    volume: Number(row.volume || 0)
  }));
}

function topAndBottomGroups(data) {
  const sorted = [...data].sort((a, b) => b.volume - a.volume);
  return {
    top: sorted.filter((item) => item.volume > 0).slice(0, 3),
    bottom: [...sorted].reverse().slice(0, 3)
  };
}

export default function RadarChart({ radarData }) {
  const data = toChartData(radarData);
  const hasVolume = data.some((item) => item.volume > 0);

  if (!hasVolume) {
    return (
      <section id="radar" className="apple-card p-6">
        <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Muscle Balance</h2>
        <p className="mt-4 text-zinc-400">Train more groups to reveal your 30-day balance profile.</p>
      </section>
    );
  }

  const { top, bottom } = topAndBottomGroups(data);

  return (
    <section id="radar" className="apple-card p-6">
      <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Muscle Balance (30d)</h2>
      <p className="mt-1 text-sm text-zinc-400">Radar profile of volume distribution across major muscle groups.</p>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-[1.2fr_1fr]">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsRadarChart data={data}>
              <PolarGrid stroke="rgba(255,255,255,0.12)" />
              <PolarAngleAxis dataKey="muscle_group" tick={{ fill: '#CFCFD6', fontSize: 12 }} />
              <PolarRadiusAxis tick={{ fill: '#71717A', fontSize: 10 }} />
              <Tooltip
                formatter={(value) => [`${Math.round(Number(value)).toLocaleString()} kg`, 'Volume']}
                contentStyle={{
                  background: 'rgba(7,10,16,0.96)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '14px'
                }}
              />
              <Radar
                name="Volume"
                dataKey="volume"
                stroke="#5AC8FA"
                fill="#5AC8FA"
                fillOpacity={0.34}
                strokeWidth={2}
              />
            </RechartsRadarChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Most Trained</p>
            <div className="mt-3 space-y-2">
              {top.map((group) => (
                <div key={group.muscle_group} className="flex items-center justify-between gap-3">
                  <span className="text-sm text-zinc-200">{group.muscle_group}</span>
                  <span className="text-sm text-accent">{Math.round(group.volume).toLocaleString()}kg</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Needs Attention</p>
            <div className="mt-3 space-y-2">
              {bottom.map((group) => (
                <div key={group.muscle_group} className="flex items-center justify-between gap-3">
                  <span className="text-sm text-zinc-200">{group.muscle_group}</span>
                  <span className="text-sm text-blaze">{Math.round(group.volume).toLocaleString()}kg</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
