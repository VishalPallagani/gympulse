import dayjs from 'dayjs';

export default function MedalsGrid({ medals }) {
  if (!medals?.length) {
    return (
      <section id="medals" className="apple-card p-4 sm:p-6">
        <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Achievement Medals</h2>
        <p className="mt-4 text-zinc-400">No medal data yet.</p>
      </section>
    );
  }

  return (
    <section id="medals" className="apple-card p-4 sm:p-6">
      <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Achievement Medals</h2>
      <p className="mt-1 text-sm text-zinc-400">Earned milestones and next unlock targets.</p>
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {medals.map((medal) => {
          const earned = Boolean(medal.earned);
          return (
            <article
              key={medal.medal_key}
              className={`rounded-2xl border p-4 transition ${
                earned
                  ? 'border-accent/45 bg-accent/10 shadow-glow'
                  : 'border-white/10 bg-black/20 opacity-75 grayscale'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="text-3xl sm:text-4xl">{earned ? medal.medal_emoji || '\ud83c\udfc6' : '\ud83d\udd12'}</span>
                {earned ? (
                  <span className="rounded-full border border-mint/40 bg-mint/10 px-2 py-1 text-xs text-mint">Unlocked</span>
                ) : (
                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-xs text-zinc-400">Locked</span>
                )}
              </div>
              <h3 className="mt-3 text-base font-semibold text-white sm:text-lg">{medal.medal_name}</h3>
              <p className="mt-1 text-sm text-zinc-300">{medal.description}</p>
              {earned && medal.awarded_at ? (
                <p className="mt-3 text-xs uppercase tracking-[0.14em] text-zinc-400">
                  Earned {dayjs(medal.awarded_at).format('MMM D, YYYY')}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
