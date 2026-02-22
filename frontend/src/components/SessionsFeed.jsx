import { useState } from 'react';
import dayjs from 'dayjs';

function formatExercise(exercise) {
  const weight = exercise.weight_kg ? `${exercise.weight_kg}kg` : 'Bodyweight';
  const reps = exercise.reps ? `${exercise.reps} reps` : '-';
  const sets = exercise.sets_count ? `${exercise.sets_count} sets` : '-';
  return `${weight} | ${sets} | ${reps}`;
}

export default function SessionsFeed({ sessions }) {
  const [openSessionId, setOpenSessionId] = useState(null);

  if (!sessions?.length) {
    return (
      <section id="sessions" className="apple-card p-4 sm:p-6">
        <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Recent Sessions</h2>
        <p className="mt-4 text-zinc-400">No sessions logged yet.</p>
      </section>
    );
  }

  return (
    <section id="sessions" className="apple-card p-4 sm:p-6">
      <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Recent Sessions</h2>
      <p className="mt-1 text-sm text-zinc-400">Latest 10 sessions with expandable exercise detail.</p>

      <div className="mt-6 space-y-3">
        {sessions.map((session) => {
          const isOpen = openSessionId === session.id;
          return (
            <article key={session.id} className="rounded-xl border border-white/10 bg-black/20 p-3 transition hover:border-accent/40 sm:p-4">
              <button
                type="button"
                onClick={() => setOpenSessionId(isOpen ? null : session.id)}
                className="flex w-full flex-col gap-2 text-left sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-zinc-400">
                    {dayjs(session.logged_at).format('ddd, MMM D YYYY')}
                  </p>
                  <p className="mt-1 text-base font-semibold text-white sm:text-lg">
                    {session.muscle_groups?.join(', ') || 'Mixed Session'}
                  </p>
                </div>
                <div className="text-left sm:text-right">
                  <p className="font-display text-2xl font-bold text-accent sm:text-3xl">{Math.round(session.total_volume || 0)}kg</p>
                  <p className="text-xs text-zinc-400">{session.exercises?.length || 0} sets logged</p>
                </div>
              </button>

              {isOpen ? (
                <div className="mt-4 space-y-2 border-t border-white/10 pt-4">
                  {session.notes ? (
                    <div className="rounded-lg border border-accent/25 bg-accent/8 px-3 py-2 text-sm text-zinc-200">
                      Notes: {session.notes}
                    </div>
                  ) : null}
                  {session.exercises?.map((exercise, index) => (
                    <div key={`${session.id}-${exercise.exercise_name}-${index}`} className="rounded-lg border border-white/10 bg-surface/60 px-3 py-2">
                      <p className="font-medium text-white">{exercise.exercise_name}</p>
                      <p className="text-sm text-zinc-400">{formatExercise(exercise)}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
