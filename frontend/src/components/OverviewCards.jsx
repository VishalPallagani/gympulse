function formatTonnes(value) {
  const numeric = Number(value || 0);
  return `${numeric.toFixed(1)}T`;
}

function StatCard({ label, value, footnote, tone = 'accent' }) {
  const toneMap = {
    accent: 'text-accent',
    mint: 'text-mint',
    violet: 'text-violet',
    blaze: 'text-blaze'
  };

  return (
    <article className="soft-ring apple-card p-4 transition hover:-translate-y-1 sm:p-5">
      <p className={`font-display text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl ${toneMap[tone] || 'text-accent'}`}>{value}</p>
      <p className="mt-2 text-[10px] uppercase tracking-[0.16em] text-zinc-400 sm:text-xs sm:tracking-[0.18em]">{label}</p>
      <p className="mt-3 text-xs text-zinc-300 sm:text-sm">{footnote}</p>
    </article>
  );
}

export default function OverviewCards({ summary, quickStats }) {
  const totalSessions = summary?.total_sessions ?? 0;
  const totalTonnes = summary?.total_volume_tonnes ?? 0;
  const currentStreak = summary?.current_streak ?? 0;
  const longestStreak = summary?.longest_streak ?? 0;
  const strongestDay = quickStats?.strongest_day || 'N/A';
  const mostTrained = quickStats?.most_trained || 'N/A';
  const latestWeight = summary?.latest_weight_kg;
  const weightNote = latestWeight ? `${Number(latestWeight).toFixed(1)}kg latest bodyweight.` : 'No bodyweight logs yet.';

  return (
    <section id="overview" className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
      <StatCard label="Total Sessions" value={totalSessions} tone="accent" footnote={`Strongest day: ${strongestDay}`} />
      <StatCard label="Total Volume Lifted" value={formatTonnes(totalTonnes)} tone="mint" footnote="Cumulative tonnage moved." />
      <StatCard label="Current Streak" value={`${currentStreak}d`} tone="violet" footnote={`Current focus: ${mostTrained}`} />
      <StatCard label="Longest Streak" value={`${longestStreak}d`} tone="blaze" footnote={weightNote} />
    </section>
  );
}
