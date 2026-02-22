import { useEffect, useRef, useState } from 'react';
import dayjs from 'dayjs';
import html2canvas from 'html2canvas';

function downloadBlob(url, filename) {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function getWeekNumber() {
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), 0, 1);
  const dayOffset = Math.floor((now - firstDay) / 86400000);
  return Math.ceil((dayOffset + firstDay.getDay() + 1) / 7);
}

export default function StoryCard({ token, apiBase, summary, quickStats }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [storyImageUrl, setStoryImageUrl] = useState('');
  const [error, setError] = useState('');
  const previewRef = useRef(null);

  useEffect(() => {
    return () => {
      if (storyImageUrl) {
        URL.revokeObjectURL(storyImageUrl);
      }
    };
  }, [storyImageUrl]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError('');

    try {
      const response = await fetch(`${apiBase}/api/story/${token}`);
      if (!response.ok) {
        throw new Error('Failed to generate story card');
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      if (storyImageUrl) {
        URL.revokeObjectURL(storyImageUrl);
      }
      setStoryImageUrl(objectUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate story card');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCaptureLocal = async () => {
    if (!previewRef.current) {
      return;
    }

    const canvas = await html2canvas(previewRef.current, {
      backgroundColor: '#070A10',
      scale: 2
    });
    const localUrl = canvas.toDataURL('image/png');
    downloadBlob(localUrl, `gympulse-local-story-${dayjs().format('YYYYMMDD')}.png`);
  };

  return (
    <section id="story" className="apple-card p-6">
      <h2 className="font-display text-3xl font-semibold text-white md:text-4xl">Story Card Studio</h2>
      <p className="mt-2 text-zinc-400">Generate and share your weekly highlight card.</p>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div>
          <div ref={previewRef} className="relative overflow-hidden rounded-2xl border border-white/10 bg-ink p-6">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(90,200,250,0.22),transparent_58%)]" />
            <div className="relative z-10">
              <p className="font-display text-4xl font-bold text-accent">GYMPULSE</p>
              <p className="mt-4 font-display text-5xl font-bold text-white">WEEK {getWeekNumber()}</p>
              <div className="mt-6 space-y-2 text-white">
                <p>{Math.round(quickStats?.total_volume || 0).toLocaleString()} KG MOVED</p>
                <p>{quickStats?.sessions || 0} SESSIONS</p>
                <p>{summary?.current_streak || 0} DAY STREAK</p>
                <p>{summary?.latest_weight_kg ? `${Number(summary.latest_weight_kg).toFixed(1)} KG BODYWEIGHT` : 'BODYWEIGHT: LOG DAILY'}</p>
                <p className="text-accent">TOP GROUP: {summary?.top_muscle_group || 'N/A'}</p>
              </div>
              <p className="mt-6 text-xs uppercase tracking-[0.2em] text-zinc-400">Track yours on WhatsApp</p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleCaptureLocal}
            className="mt-3 w-full rounded-xl border border-white/15 bg-black/20 px-4 py-2 font-medium text-zinc-100 transition hover:border-accent hover:text-accent"
          >
            Capture Local Card
          </button>
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={isGenerating}
            className="w-full rounded-xl bg-accent px-4 py-3 font-semibold text-white shadow-glow transition hover:bg-accentStrong disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isGenerating ? 'Generating...' : 'Generate Server Story Card'}
          </button>

          {error ? <p className="mt-3 text-sm text-rose">{error}</p> : null}

          {storyImageUrl ? (
            <div className="mt-4">
              <img src={storyImageUrl} alt="Generated story card" className="w-full rounded-xl border border-white/10" />
              <button
                type="button"
                onClick={() => downloadBlob(storyImageUrl, `gympulse-story-${dayjs().format('YYYYMMDD')}.png`)}
                className="mt-3 w-full rounded-xl border border-accent px-4 py-2 font-semibold text-accent transition hover:bg-accent hover:text-white"
              >
                Download
              </button>
            </div>
          ) : (
            <p className="mt-4 text-sm text-zinc-400">Server-side Pillow image appears here.</p>
          )}
        </div>
      </div>
    </section>
  );
}
