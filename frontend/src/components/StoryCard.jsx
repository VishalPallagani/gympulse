import { useRef, useState } from 'react';
import dayjs from 'dayjs';
import html2canvas from 'html2canvas';

function getWeekNumber() {
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), 0, 1);
  const dayOffset = Math.floor((now - firstDay) / 86400000);
  return Math.ceil((dayOffset + firstDay.getDay() + 1) / 7);
}

function triggerDownload(url, filename) {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

async function captureElementAsBlob(element) {
  const canvas = await html2canvas(element, {
    backgroundColor: '#06070D',
    scale: 2,
    useCORS: true,
  });
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/png');
  });
}

export default function StoryCard({ summary, quickStats }) {
  const previewRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const fileName = `gympulse-drop-${dayjs().format('YYYYMMDD')}.png`;

  const handleSave = async () => {
    if (!previewRef.current || busy) {
      return;
    }
    setBusy(true);
    setError('');
    try {
      const blob = await captureElementAsBlob(previewRef.current);
      if (!blob) {
        throw new Error('Could not generate image');
      }
      const objectUrl = URL.createObjectURL(blob);
      triggerDownload(objectUrl, fileName);
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save snapshot');
    } finally {
      setBusy(false);
    }
  };

  const handleShare = async () => {
    if (!previewRef.current || busy) {
      return;
    }
    setBusy(true);
    setError('');
    try {
      const blob = await captureElementAsBlob(previewRef.current);
      if (!blob) {
        throw new Error('Could not generate image');
      }

      const file = new File([blob], fileName, { type: 'image/png' });
      const canNativeShare = typeof navigator !== 'undefined' && navigator.share && navigator.canShare?.({ files: [file] });

      if (canNativeShare) {
        await navigator.share({
          files: [file],
          title: 'GymPulse Weekly Drop',
          text: 'Training update from GymPulse.',
        });
      } else {
        const objectUrl = URL.createObjectURL(blob);
        triggerDownload(objectUrl, fileName);
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not share snapshot');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section id="story" className="apple-card p-4 sm:p-6">
      <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl md:text-4xl">Share Drop Studio</h2>
      <p className="mt-2 text-zinc-400">Create a clean weekly flex snapshot and share it anywhere.</p>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <div
          ref={previewRef}
          className="relative overflow-hidden rounded-2xl border border-white/10 bg-ink p-5 sm:p-6"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,79,216,0.28),transparent_58%)]" />
          <div className="absolute -right-20 top-20 h-64 w-64 rounded-full bg-cyan/20 blur-3xl" />
          <div className="relative z-10">
            <p className="font-display text-3xl font-bold text-accent sm:text-4xl">GYMPULSE</p>
            <p className="mt-4 font-display text-4xl font-bold text-white sm:text-5xl">WEEK {getWeekNumber()}</p>
            <div className="mt-6 space-y-2 text-sm text-white sm:text-base">
              <p>{Math.round(quickStats?.total_volume || 0).toLocaleString()} KG MOVED</p>
              <p>{quickStats?.sessions || 0} SESSIONS</p>
              <p>{summary?.current_streak || 0} DAY STREAK</p>
              <p>{summary?.latest_weight_kg ? `${Number(summary.latest_weight_kg).toFixed(1)} KG BODYWEIGHT` : 'BODYWEIGHT: LOG DAILY'}</p>
              <p className="text-accent">TOP GROUP: {summary?.top_muscle_group || 'N/A'}</p>
            </div>
            <p className="mt-6 text-xs uppercase tracking-[0.2em] text-zinc-400">Track yours on WhatsApp</p>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
          <p className="text-sm text-zinc-300">
            Pro tip: post this after your top session each week. It makes your progress obvious and keeps consistency high.
          </p>
          <button
            type="button"
            onClick={handleShare}
            disabled={busy}
            className="mt-4 w-full rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white shadow-glow transition hover:bg-accentStrong disabled:cursor-not-allowed disabled:opacity-70 sm:text-base"
          >
            {busy ? 'Preparing...' : 'Share Weekly Drop'}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={busy}
            className="mt-3 w-full rounded-xl border border-white/15 bg-black/20 px-4 py-2 text-sm font-medium text-zinc-100 transition hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-70 sm:text-base"
          >
            Save to Gallery
          </button>
          {error ? <p className="mt-3 text-sm text-rose">{error}</p> : null}
          <p className="mt-4 text-xs text-zinc-500">If native share is unavailable, we will download the image instead.</p>
        </div>
      </div>
    </section>
  );
}
