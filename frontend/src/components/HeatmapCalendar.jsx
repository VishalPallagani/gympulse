import dayjs from 'dayjs';

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const INTENSITY_CLASSES = ['bg-zinc-800/70', 'bg-fuchsia-950/80', 'bg-fuchsia-700/80', 'bg-cyan-400/85'];

function buildMonthGrid(now) {
  const monthStart = now.startOf('month');
  const monthEnd = now.endOf('month');
  const leadingSlots = monthStart.day();
  const daysInMonth = monthEnd.date();

  const grid = [];
  for (let index = 0; index < leadingSlots; index += 1) {
    grid.push(null);
  }
  for (let dayNumber = 1; dayNumber <= daysInMonth; dayNumber += 1) {
    grid.push(monthStart.date(dayNumber));
  }

  while (grid.length % 7 !== 0) {
    grid.push(null);
  }
  return { grid, monthStart, monthEnd, daysInMonth };
}

export default function HeatmapCalendar({ heatmapData }) {
  const byDate = new Map((heatmapData || []).map((item) => [item.date, item]));
  const today = dayjs().startOf('day');
  const { grid, monthStart, daysInMonth } = buildMonthGrid(today);

  const monthKeyPrefix = `${monthStart.year()}-${String(monthStart.month() + 1).padStart(2, '0')}-`;
  const monthRows = (heatmapData || []).filter((row) => String(row.date || '').startsWith(monthKeyPrefix));
  const trainedDays = monthRows.filter((row) => Number(row.volume || 0) > 0).length;
  const monthVolume = monthRows.reduce((sum, row) => sum + Number(row.volume || 0), 0);

  return (
    <section id="heatmap" className="apple-card p-4 sm:p-6">
      <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Consistency Map</h2>
      <p className="mt-2 text-sm text-zinc-400">
        {monthStart.format('MMMM YYYY')} training load ({daysInMonth} days in month).
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-zinc-300">
        <span className="rounded-full border border-white/10 bg-black/25 px-3 py-1">
          Days trained: {trainedDays}/{daysInMonth}
        </span>
        <span className="rounded-full border border-white/10 bg-black/25 px-3 py-1">
          Month volume: {Math.round(monthVolume).toLocaleString()} kg
        </span>
      </div>

      <div className="mt-5">
        <div className="grid grid-cols-7 gap-1.5 text-[10px] uppercase tracking-[0.16em] text-zinc-500 sm:gap-2">
          {DAY_LABELS.map((label) => (
            <div key={label} className="text-center">
              {label}
            </div>
          ))}
        </div>

        <div className="mt-2 grid grid-cols-7 gap-1.5 sm:gap-2">
          {grid.map((day, index) => {
            if (!day) {
              return <div key={`empty-${index}`} className="h-7 w-full rounded-md border border-transparent sm:h-8" />;
            }

            const dateKey = day.format('YYYY-MM-DD');
            const activity = byDate.get(dateKey);
            const isFuture = day.isAfter(today);
            const intensity = Math.min(Math.max(activity?.intensity || 0, 0), 3);
            const bgClass = isFuture ? 'bg-zinc-900/40' : INTENSITY_CLASSES[intensity];

            return (
              <div
                key={dateKey}
                title={`${dateKey}: ${Math.round(activity?.volume || 0)} kg`}
                className={`group relative h-7 w-full rounded-md border border-black/40 ${bgClass} ${isFuture ? 'opacity-45' : ''} transition hover:scale-[1.05] sm:h-8`}
              >
                <span className="absolute inset-x-0 bottom-1 text-center text-[10px] font-medium text-zinc-200/90">
                  {day.date()}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-zinc-400">
        <span>Low</span>
        {INTENSITY_CLASSES.map((bgClass) => (
          <span key={bgClass} className={`inline-block h-3 w-3 rounded-[4px] border border-black/40 ${bgClass}`} />
        ))}
        <span>High</span>
      </div>
    </section>
  );
}
