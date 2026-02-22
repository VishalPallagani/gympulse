import dayjs from 'dayjs';

const INTENSITY_CLASSES = ['bg-zinc-800/70', 'bg-sky-900/80', 'bg-cyan-700/80', 'bg-blaze'];

function monthMarkers(days) {
  const marks = [];
  for (let index = 0; index < days.length; index += 7) {
    const day = days[index];
    if (day.date() <= 7) {
      marks.push({ index: Math.floor(index / 7), label: day.format('MMM') });
    }
  }
  return marks;
}

export default function HeatmapCalendar({ heatmapData }) {
  const byDate = new Map((heatmapData || []).map((item) => [item.date, item]));

  const end = dayjs().startOf('day');
  const start = end.subtract(6, 'month').startOf('week');
  const totalDays = end.diff(start, 'day') + 1;
  const days = Array.from({ length: totalDays }, (_, index) => start.add(index, 'day'));
  const monthTicks = monthMarkers(days);
  const columns = Math.ceil(days.length / 7);

  return (
    <section id="heatmap" className="apple-card p-6">
      <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Consistency Heatmap</h2>
      <p className="mt-2 text-sm text-zinc-400">Daily training intensity over the last 6 months.</p>

      <div className="mt-5 overflow-x-auto pb-2 scrollbar-thin">
        <div className="relative min-w-max">
          <div className="relative mb-2 h-5">
            {monthTicks.map((mark) => (
              <span
                key={`${mark.label}-${mark.index}`}
                className="absolute text-[10px] uppercase tracking-[0.2em] text-zinc-500"
                style={{ left: `${mark.index * 18}px` }}
              >
                {mark.label}
              </span>
            ))}
          </div>

          <div
            className="grid gap-1"
            style={{
              gridAutoFlow: 'column',
              gridTemplateRows: 'repeat(7, minmax(0, 1fr))',
              width: `${columns * 18}px`
            }}
          >
            {days.map((day) => {
              const key = day.format('YYYY-MM-DD');
              const activity = byDate.get(key);
              const intensity = Math.min(Math.max(activity?.intensity || 0, 0), 3);
              const bgClass = INTENSITY_CLASSES[intensity];

              return (
                <div
                  key={key}
                  className={`h-4 w-4 rounded-[4px] border border-black/40 ${bgClass}`}
                  title={`${key}: ${Math.round(activity?.volume || 0)} kg`}
                />
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-zinc-400">
        <span>Less</span>
        {INTENSITY_CLASSES.map((bgClass) => (
          <span key={bgClass} className={`inline-block h-3 w-3 rounded-[4px] border border-black/40 ${bgClass}`} />
        ))}
        <span>More</span>
      </div>
    </section>
  );
}
