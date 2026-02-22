import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import BodyWeightChart from '../components/BodyWeightChart';
import HeatmapCalendar from '../components/HeatmapCalendar';
import InsightsPanel from '../components/InsightsPanel';
import MedalsGrid from '../components/MedalsGrid';
import OverviewCards from '../components/OverviewCards';
import ProgressChart from '../components/ProgressChart';
import RadarChart from '../components/RadarChart';
import SessionsFeed from '../components/SessionsFeed';
import StoryCard from '../components/StoryCard';
import VolumeChart from '../components/VolumeChart';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview' },
  { id: 'insights', label: 'Insights' },
  { id: 'bodyweight', label: 'Bodyweight' },
  { id: 'progress', label: 'Strength' },
  { id: 'volume', label: 'Volume' },
  { id: 'radar', label: 'Balance' },
  { id: 'heatmap', label: 'Streak' },
  { id: 'medals', label: 'Medals' },
  { id: 'sessions', label: 'Sessions' },
  { id: 'story', label: 'Story' }
];

function ScrollNav({ mobile = false }) {
  return (
    <nav
      className={
        mobile
          ? 'fixed bottom-0 left-0 right-0 z-30 border-t border-white/10 bg-ink/88 px-2 py-2 backdrop-blur lg:hidden'
          : 'sticky top-6 hidden h-fit rounded-2xl apple-card p-4 lg:block'
      }
    >
      <ul className={mobile ? 'flex items-center gap-2 overflow-x-auto text-xs' : 'space-y-2'}>
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className={
                mobile
                  ? 'block whitespace-nowrap rounded-xl border border-white/10 px-3 py-2 text-zinc-300 transition hover:border-accent/60 hover:text-white'
                  : 'block rounded-xl px-3 py-2 text-sm font-medium text-zinc-300 transition hover:bg-white/5 hover:text-white'
              }
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function LoadingSkeleton() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-ink p-6 text-white">
      <div className="grid-noise absolute inset-0" />
      <div className="relative mx-auto max-w-7xl space-y-6">
        <div className="h-44 animate-pulse rounded-3xl bg-white/5" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-32 animate-pulse rounded-2xl bg-white/5" />
          ))}
        </div>
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-80 animate-pulse rounded-2xl bg-white/5" />
        ))}
      </div>
    </div>
  );
}

function LockedPaywall({ paymentUrl }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-ink px-6 py-10 text-white">
      <div className="absolute inset-0">
        <div className="absolute -left-16 top-12 h-80 w-80 rounded-full bg-accent/20 blur-3xl" />
        <div className="absolute right-0 top-6 h-72 w-72 rounded-full bg-violet/25 blur-3xl" />
        <div className="absolute bottom-0 right-8 h-72 w-72 rounded-full bg-mint/12 blur-3xl" />
        <div className="absolute inset-0 bg-black/45" />
      </div>

      <div className="absolute inset-0 flex items-center justify-center px-4">
        <div className="w-full max-w-5xl rounded-3xl border border-white/10 bg-white/5 p-8 blur-[1px]">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="h-44 rounded-2xl bg-white/10" />
            <div className="h-44 rounded-2xl bg-white/10" />
            <div className="h-44 rounded-2xl bg-white/10" />
            <div className="h-60 rounded-2xl bg-white/10 md:col-span-2" />
            <div className="h-60 rounded-2xl bg-white/10" />
          </div>
        </div>
      </div>

      <section className="relative z-10 w-full max-w-2xl rounded-3xl border border-white/15 bg-[#0C1018]/90 p-8 shadow-card backdrop-blur-xl">
        <p className="text-center font-display text-4xl font-bold tracking-tight text-accent">GymPulse</p>
        <h1 className="mt-5 text-center font-display text-4xl leading-tight text-white md:text-5xl">
          Your gains deserve better than a spreadsheet.
        </h1>
        <p className="mt-4 text-center text-zinc-300">
          Unlock your personal dashboard with advanced charts, story cards, medals and full workout history.
        </p>

        <ul className="mt-7 space-y-3 text-zinc-100">
          {[
            'Full dashboard and premium charts',
            'Progressive overload tracking',
            'Weekly story cards',
            'Achievement medals',
            'Full workout history'
          ].map((item) => (
            <li key={item} className="flex items-center gap-3">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20 text-accent">✓</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>

        <button
          type="button"
          className="mt-8 w-full rounded-2xl bg-accent px-6 py-4 text-lg font-bold text-white shadow-glow transition hover:bg-accentStrong disabled:cursor-not-allowed disabled:opacity-70"
          onClick={() => paymentUrl && window.open(paymentUrl, '_blank', 'noopener,noreferrer')}
          disabled={!paymentUrl}
        >
          Unlock Pro - INR 99/month
        </button>
        {!paymentUrl ? <p className="mt-3 text-center text-sm text-amber-300">Payment link unavailable. Try again shortly.</p> : null}
        <p className="mt-3 text-center text-sm text-zinc-400">Cancel anytime. Your workout logs are always safe.</p>
      </section>
    </div>
  );
}

export default function Dashboard() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dashboardData, setDashboardData] = useState(null);
  const [medalsData, setMedalsData] = useState(null);
  const [exerciseData, setExerciseData] = useState(null);
  const [lockedData, setLockedData] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setError('');
      setLockedData(null);

      try {
        const dashboardRes = await fetch(`${API_BASE}/api/dashboard/${token}`);
        if (!dashboardRes.ok) {
          const errorBody = await dashboardRes.json().catch(() => ({}));
          throw new Error(errorBody.detail || 'Failed to load dashboard');
        }

        const dashboardJson = await dashboardRes.json();
        if (dashboardJson?.status === 'locked') {
          if (!cancelled) {
            setLockedData(dashboardJson);
            setDashboardData(null);
            setMedalsData(null);
            setExerciseData(null);
          }
          return;
        }

        const [medalsRes, exercisesRes] = await Promise.all([
          fetch(`${API_BASE}/api/medals/${token}`),
          fetch(`${API_BASE}/api/exercises/${token}`)
        ]);

        if (!medalsRes.ok || !exercisesRes.ok) {
          throw new Error('Failed to load dashboard details');
        }

        const [medalsJson, exercisesJson] = await Promise.all([medalsRes.json(), exercisesRes.json()]);

        if (!cancelled) {
          setDashboardData(dashboardJson);
          setMedalsData(medalsJson);
          setExerciseData(exercisesJson);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load dashboard');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const stats = dashboardData?.stats;
  const summary = stats?.summary;
  const sessionCount = useMemo(() => exerciseData?.history?.length || 0, [exerciseData]);

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (lockedData) {
    return <LockedPaywall paymentUrl={lockedData.payment_url} />;
  }

  if (error || !dashboardData || !stats) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink px-6 text-white">
        <div className="w-full max-w-xl rounded-2xl border border-white/10 bg-surface p-8">
          <h1 className="font-display text-4xl font-bold tracking-tight text-accent">GymPulse</h1>
          <p className="mt-4 text-zinc-300">{error || 'Dashboard data unavailable.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-ink pb-24 text-white">
      <div className="grid-noise absolute inset-0" />
      <div className="pointer-events-none absolute -left-16 top-10 h-72 w-72 animate-float rounded-full bg-accent/18 blur-3xl" />
      <div className="pointer-events-none absolute bottom-8 right-4 h-72 w-72 animate-float rounded-full bg-violet/18 blur-3xl" />

      <div className="relative mx-auto grid w-full max-w-7xl gap-6 px-4 pb-10 pt-6 lg:grid-cols-[250px_1fr] lg:px-6">
        <ScrollNav />

        <main className="space-y-6 fade-seq">
          <header className="apple-card relative overflow-hidden p-6">
            <div className="absolute -right-8 top-1/2 h-40 w-40 -translate-y-1/2 rounded-full bg-accent/18 blur-2xl" />
            <div className="absolute -left-12 -top-10 h-44 w-44 rounded-full bg-violet/25 blur-3xl" />
            <p className="text-xs uppercase tracking-[0.28em] text-zinc-400">Athlete Intelligence</p>
            <h1 className="mt-2 max-w-3xl font-display text-4xl font-bold leading-tight text-white md:text-5xl">
              Performance Command Center
            </h1>
            <p className="mt-3 text-zinc-300">
              Athlete {dashboardData.user?.phone_number || 'Unknown'} | {sessionCount} total sets logged
            </p>
            <p className="mt-2 text-sm text-zinc-400">
              Coach-grade telemetry from simple WhatsApp messages: training stress, progression, bodyweight trend, and balance.
            </p>
          </header>

          <OverviewCards summary={summary} quickStats={stats.quick_stats} />
          <InsightsPanel coachInsights={stats.coach_insights} bodyWeight={stats.body_weight} />
          <BodyWeightChart bodyWeight={stats.body_weight} coachInsights={stats.coach_insights} />
          <ProgressChart progress={stats.progress} />
          <VolumeChart weeklyVolume={stats.weekly_volume} />
          <RadarChart radarData={stats.radar_30d} />
          <HeatmapCalendar heatmapData={stats.heatmap} />
          <MedalsGrid medals={medalsData?.all_medals || []} />
          <SessionsFeed sessions={stats.recent_sessions} />
          <StoryCard token={token} apiBase={API_BASE} summary={summary} quickStats={stats.quick_stats} />
        </main>
      </div>

      <ScrollNav mobile />
    </div>
  );
}
