import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'users', label: 'Users' },
  { key: 'revenue', label: 'Revenue' },
  { key: 'live', label: 'Sessions Feed' },
  { key: 'broadcast', label: 'Broadcast' }
];

function formatCurrency(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(Number(value || 0));
}

function formatDate(value) {
  if (!value) {
    return 'N/A';
  }
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDateTime(value) {
  if (!value) {
    return 'N/A';
  }
  return new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatRelative(value) {
  if (!value) {
    return 'Never';
  }
  const now = Date.now();
  const then = new Date(value).getTime();
  const diffMs = Math.max(now - then, 0);
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  if (hours < 1) {
    const mins = Math.max(Math.floor(diffMs / (1000 * 60)), 1);
    return `${mins}m ago`;
  }
  if (hours < 24) {
    return `${hours}h ago`;
  }
  return `${Math.floor(hours / 24)}d ago`;
}

function StatCard({ label, value }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-panel/80 p-4 shadow-violetGlow">
      <p className="font-heading text-3xl font-bold text-white">{value}</p>
      <p className="mt-2 text-xs uppercase tracking-[0.2em] text-zinc-400">{label}</p>
    </article>
  );
}

function AdminLogin({ password, setPassword, onSubmit, error, loading }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ink px-4 text-white">
      <section className="w-full max-w-md rounded-3xl border border-white/10 bg-[#0F1020]/90 p-8 shadow-violetGlow backdrop-blur-xl">
        <p className="text-center font-heading text-4xl font-bold text-adminAccent">GymPulse Admin</p>
        <p className="mt-2 text-center text-zinc-400">Enter admin password to continue.</p>
        <form
          className="mt-6 space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Admin password"
            className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-white placeholder:text-zinc-500 focus:border-adminAccent focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-adminAccent px-4 py-3 font-semibold text-white transition hover:bg-violet disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? 'Checking...' : 'Enter Admin Panel'}
          </button>
        </form>
        {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
      </section>
    </div>
  );
}

function TableHeader({ children }) {
  return <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">{children}</th>;
}

export default function Admin() {
  const [passwordInput, setPasswordInput] = useState('');
  const [adminToken, setAdminToken] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);

  const [activeTab, setActiveTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [usersPayload, setUsersPayload] = useState({ users: [], count: 0 });
  const [revenue, setRevenue] = useState(null);
  const [liveFeed, setLiveFeed] = useState({ sessions: [] });
  const [panelError, setPanelError] = useState('');
  const [loadingTab, setLoadingTab] = useState(false);

  const [search, setSearch] = useState('');
  const [planFilter, setPlanFilter] = useState('all');
  const [sortBy, setSortBy] = useState('joined');

  const [selectedUserDetail, setSelectedUserDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [messageBox, setMessageBox] = useState({ userId: '', text: '', sending: false });
  const [broadcastMessage, setBroadcastMessage] = useState('');
  const [broadcastSegment, setBroadcastSegment] = useState('all');
  const [broadcastPreviewCount, setBroadcastPreviewCount] = useState(null);
  const [broadcastSending, setBroadcastSending] = useState(false);

  const authHeaders = useMemo(
    () => ({
      Authorization: `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    }),
    [adminToken]
  );

  const fetchWithAuth = async (path, options = {}) => {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...authHeaders,
        ...(options.headers || {})
      }
    });
    if (response.status === 401) {
      setAdminToken('');
      setLoginError('Session expired. Please enter password again.');
      throw new Error('Unauthorized');
    }
    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || 'Request failed');
    }
    return response.json();
  };

  const loadOverview = async () => {
    const data = await fetchWithAuth('/api/admin/overview');
    setOverview(data);
  };

  const loadUsers = async () => {
    const params = new URLSearchParams({
      search,
      plan: planFilter,
      sort: sortBy
    });
    const data = await fetchWithAuth(`/api/admin/users?${params.toString()}`);
    setUsersPayload(data);
  };

  const loadRevenue = async () => {
    const data = await fetchWithAuth('/api/admin/revenue');
    setRevenue(data);
  };

  const loadLiveFeed = async () => {
    const data = await fetchWithAuth('/api/admin/live-sessions?limit=80');
    setLiveFeed(data);
  };

  const loadInitial = async () => {
    setPanelError('');
    setLoadingTab(true);
    try {
      await Promise.all([loadOverview(), loadUsers(), loadRevenue(), loadLiveFeed()]);
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : 'Failed to load admin panel');
    } finally {
      setLoadingTab(false);
    }
  };

  const handleLogin = async () => {
    setLoggingIn(true);
    setLoginError('');
    try {
      const response = await fetch(`${API_BASE}/api/admin/overview`, {
        headers: { Authorization: `Bearer ${passwordInput}` }
      });
      if (!response.ok) {
        throw new Error('Invalid password');
      }
      setAdminToken(passwordInput);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Invalid password');
    } finally {
      setLoggingIn(false);
    }
  };

  useEffect(() => {
    if (!adminToken) {
      return;
    }
    loadInitial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminToken]);

  useEffect(() => {
    if (!adminToken) {
      return;
    }
    if (activeTab !== 'users') {
      return;
    }
    const timer = setTimeout(() => {
      loadUsers().catch((err) => setPanelError(err instanceof Error ? err.message : 'Failed to load users'));
    }, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, planFilter, sortBy, activeTab, adminToken]);

  useEffect(() => {
    if (!adminToken || activeTab !== 'live') {
      return undefined;
    }
    const interval = setInterval(() => {
      loadLiveFeed().catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminToken, activeTab]);

  if (!adminToken) {
    return (
      <AdminLogin
        password={passwordInput}
        setPassword={setPasswordInput}
        onSubmit={handleLogin}
        error={loginError}
        loading={loggingIn}
      />
    );
  }

  const cards = overview?.cards || {};
  const users = usersPayload?.users || [];
  const liveSessions = liveFeed?.sessions || [];
  const successfulPayments = revenue?.successful_payments || [];
  const cancelledSubscriptions = revenue?.cancelled_subscriptions || [];
  const failedPayments = revenue?.failed_payments || [];

  return (
    <div className="min-h-screen bg-ink text-white">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[240px_1fr]">
        <aside className="h-fit rounded-2xl border border-white/10 bg-panel/80 p-4 shadow-violetGlow">
          <p className="font-heading text-2xl font-bold text-adminAccent">GymPulse Admin</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-zinc-400">Control Center</p>
          <div className="mt-5 space-y-2">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`w-full rounded-xl px-3 py-2 text-left text-sm font-medium transition ${
                  activeTab === tab.key
                    ? 'bg-adminAccent text-white shadow-violetGlow'
                    : 'border border-transparent text-zinc-300 hover:border-white/15 hover:bg-black/20'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </aside>

        <main className="space-y-4">
          <header className="rounded-2xl border border-white/10 bg-panel/70 p-5">
            <h1 className="font-heading text-3xl font-bold text-white">Admin Dashboard</h1>
            <p className="mt-1 text-sm text-zinc-400">Live metrics, subscription health, and messaging controls.</p>
          </header>

          {panelError ? (
            <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {panelError}
            </div>
          ) : null}

          {loadingTab && !overview ? (
            <div className="rounded-xl border border-white/10 bg-panel/70 p-6 text-zinc-300">Loading admin data...</div>
          ) : null}

          {activeTab === 'overview' && overview ? (
            <section className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard label="Total Registered Users" value={cards.total_registered_users || 0} />
                <StatCard label="Total Pro Users" value={cards.total_pro_users || 0} />
                <StatCard label="Free Users" value={cards.free_users || 0} />
                <StatCard label="Revenue This Month" value={formatCurrency(cards.total_revenue_month || 0)} />
                <StatCard label="Revenue All Time" value={formatCurrency(cards.total_revenue_all_time || 0)} />
                <StatCard label="Churn This Month" value={cards.churn_this_month || 0} />
                <StatCard label="New Users Today" value={cards.new_users_today || 0} />
                <StatCard label="New Users This Week" value={cards.new_users_week || 0} />
              </div>

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <article className="rounded-2xl border border-white/10 bg-panel/70 p-4">
                  <h3 className="font-heading text-xl font-semibold text-white">User Signups (30d)</h3>
                  <div className="mt-4 h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={overview.signups_30d || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="date" stroke="#A1A1AA" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#A1A1AA" tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Line type="monotone" dataKey="count" stroke="#A855F7" strokeWidth={3} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </article>

                <article className="rounded-2xl border border-white/10 bg-panel/70 p-4">
                  <h3 className="font-heading text-xl font-semibold text-white">Revenue (30d)</h3>
                  <div className="mt-4 h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={overview.revenue_30d || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="date" stroke="#A1A1AA" tick={{ fontSize: 11 }} />
                        <YAxis stroke="#A1A1AA" tick={{ fontSize: 11 }} />
                        <Tooltip formatter={(value) => formatCurrency(value)} />
                        <Line type="monotone" dataKey="amount" stroke="#22D3EE" strokeWidth={3} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </article>
              </div>

              <article className="rounded-2xl border border-white/10 bg-panel/70 p-4">
                <h3 className="font-heading text-xl font-semibold text-white">Daily Active Users (30d)</h3>
                <div className="mt-4 h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={overview.daily_active_users_30d || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="date" stroke="#A1A1AA" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#A1A1AA" tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#A855F7" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </article>
            </section>
          ) : null}

          {activeTab === 'users' ? (
            <section className="space-y-4">
              <div className="grid grid-cols-1 gap-3 rounded-2xl border border-white/10 bg-panel/70 p-4 md:grid-cols-4">
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search phone number"
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm focus:border-adminAccent focus:outline-none md:col-span-2"
                />
                <select
                  value={planFilter}
                  onChange={(event) => setPlanFilter(event.target.value)}
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm focus:border-adminAccent focus:outline-none"
                >
                  <option value="all">All</option>
                  <option value="free">Free</option>
                  <option value="pro">Pro</option>
                  <option value="expired">Expired</option>
                </select>
                <select
                  value={sortBy}
                  onChange={(event) => setSortBy(event.target.value)}
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm focus:border-adminAccent focus:outline-none"
                >
                  <option value="joined">Joined Date</option>
                  <option value="last_active">Last Active</option>
                  <option value="sessions">Sessions Count</option>
                </select>
              </div>

              <div className="overflow-x-auto rounded-2xl border border-white/10 bg-panel/70">
                <table className="min-w-full">
                  <thead className="border-b border-white/10">
                    <tr>
                      <TableHeader>Phone</TableHeader>
                      <TableHeader>Joined</TableHeader>
                      <TableHeader>Plan</TableHeader>
                      <TableHeader>Status</TableHeader>
                      <TableHeader>Expires</TableHeader>
                      <TableHeader>Sessions</TableHeader>
                      <TableHeader>Last Active</TableHeader>
                      <TableHeader>Actions</TableHeader>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((userRow) => (
                      <tr key={userRow.id} className="border-b border-white/5 text-sm hover:bg-white/[0.03]">
                        <td className="px-3 py-3">{userRow.phone_number}</td>
                        <td className="px-3 py-3">{formatDate(userRow.joined_at)}</td>
                        <td className="px-3 py-3 capitalize">{userRow.plan}</td>
                        <td className="px-3 py-3 capitalize">{userRow.status}</td>
                        <td className="px-3 py-3">{formatDate(userRow.expires_at)}</td>
                        <td className="px-3 py-3">{userRow.sessions_count}</td>
                        <td className="px-3 py-3">{formatRelative(userRow.last_active)}</td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              className="rounded-lg border border-white/15 px-2 py-1 text-xs hover:border-adminAccent"
                              onClick={async () => {
                                setDetailLoading(true);
                                try {
                                  const detail = await fetchWithAuth(`/api/admin/users/${userRow.id}`);
                                  setSelectedUserDetail(detail);
                                } catch (err) {
                                  setPanelError(err instanceof Error ? err.message : 'Failed to load user detail');
                                } finally {
                                  setDetailLoading(false);
                                }
                              }}
                            >
                              {detailLoading ? 'Loading...' : 'View'}
                            </button>
                            <button
                              type="button"
                              className="rounded-lg border border-white/15 px-2 py-1 text-xs hover:border-adminAccent"
                              onClick={() =>
                                setMessageBox({
                                  userId: userRow.id,
                                  text: '',
                                  sending: false
                                })
                              }
                            >
                              Message
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!users.length ? (
                      <tr>
                        <td colSpan={8} className="px-3 py-4 text-center text-sm text-zinc-400">
                          No users found for current filter.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {activeTab === 'revenue' && revenue ? (
            <section className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <StatCard label="MRR" value={formatCurrency(revenue.mrr || 0)} />
                <StatCard label="All-Time Revenue" value={formatCurrency(revenue.total_revenue_all_time || 0)} />
              </div>

              <article className="rounded-2xl border border-white/10 bg-panel/70 p-4">
                <h3 className="font-heading text-xl font-semibold text-white">Successful Payments</h3>
                <div className="mt-3 space-y-2">
                  {successfulPayments.slice(0, 100).map((item, index) => (
                    <div key={`${item.razorpay_payment_id || index}`} className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm">
                      <span className="font-semibold text-white">{formatDateTime(item.occurred_at)}</span>
                      <span className="ml-3 text-zinc-300">{item.phone_number || 'Unknown phone'}</span>
                      <span className="ml-3 text-emerald-300">{formatCurrency(item.amount_inr || 99)}</span>
                      <span className="ml-3 text-zinc-400">{item.razorpay_payment_id || item.razorpay_subscription_id}</span>
                    </div>
                  ))}
                  {!successfulPayments.length ? <p className="text-sm text-zinc-400">No successful payments recorded yet.</p> : null}
                </div>
              </article>

              <article className="rounded-2xl border border-white/10 bg-panel/70 p-4">
                <h3 className="font-heading text-xl font-semibold text-white">Cancelled Subscriptions</h3>
                <div className="mt-3 space-y-2">
                  {cancelledSubscriptions.slice(0, 100).map((item, index) => (
                    <div key={`${item.razorpay_subscription_id || index}`} className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm">
                      <span className="font-semibold text-white">{formatDateTime(item.occurred_at)}</span>
                      <span className="ml-3 text-zinc-300">{item.phone_number || 'Unknown phone'}</span>
                      <span className="ml-3 text-zinc-400">{item.razorpay_subscription_id}</span>
                    </div>
                  ))}
                  {!cancelledSubscriptions.length ? <p className="text-sm text-zinc-400">No cancelled subscriptions recorded yet.</p> : null}
                </div>
              </article>

              <article className="rounded-2xl border border-white/10 bg-panel/70 p-4">
                <h3 className="font-heading text-xl font-semibold text-white">Failed Payments</h3>
                <div className="mt-3 space-y-2">
                  {failedPayments.slice(0, 100).map((item, index) => (
                    <div key={`${item.razorpay_payment_id || index}`} className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm">
                      <span className="font-semibold text-white">{formatDateTime(item.occurred_at)}</span>
                      <span className="ml-3 text-zinc-300">{item.phone_number || 'Unknown phone'}</span>
                      <span className="ml-3 text-red-300">{item.status || 'failed'}</span>
                    </div>
                  ))}
                  {!failedPayments.length ? <p className="text-sm text-zinc-400">No failed payments recorded yet.</p> : null}
                </div>
              </article>
            </section>
          ) : null}

          {activeTab === 'live' ? (
            <section className="rounded-2xl border border-white/10 bg-panel/70 p-4">
              <h3 className="font-heading text-xl font-semibold text-white">Live Workout Logs</h3>
              <p className="mt-1 text-sm text-zinc-400">Polling every 30 seconds.</p>
              <div className="mt-4 space-y-2">
                {liveSessions.map((entry) => (
                  <div key={entry.session_id} className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm">
                    <span className="font-semibold text-white">{formatDateTime(entry.time)}</span>
                    <span className="ml-3 text-zinc-300">{entry.phone_masked}</span>
                    <span className="ml-3 text-zinc-300">{(entry.muscle_groups || []).join(', ') || 'Mixed'}</span>
                    <span className="ml-3 text-adminAccent">{Math.round(entry.total_volume || 0).toLocaleString()} kg</span>
                  </div>
                ))}
                {!liveSessions.length ? <p className="text-sm text-zinc-400">No live sessions yet.</p> : null}
              </div>
            </section>
          ) : null}

          {activeTab === 'broadcast' ? (
            <section className="rounded-2xl border border-white/10 bg-panel/70 p-4">
              <h3 className="font-heading text-xl font-semibold text-white">Broadcast Message</h3>
              <p className="mt-1 text-sm text-zinc-400">Rate limited to 1 message/second.</p>
              <div className="mt-4 space-y-3">
                <select
                  value={broadcastSegment}
                  onChange={(event) => setBroadcastSegment(event.target.value)}
                  className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm focus:border-adminAccent focus:outline-none"
                >
                  <option value="all">All Users</option>
                  <option value="pro">Pro Users</option>
                  <option value="free">Free Users</option>
                </select>
                <textarea
                  value={broadcastMessage}
                  onChange={(event) => setBroadcastMessage(event.target.value)}
                  rows={5}
                  placeholder="Compose WhatsApp message..."
                  className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm focus:border-adminAccent focus:outline-none"
                />
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-lg border border-white/15 px-3 py-2 text-sm hover:border-adminAccent"
                    onClick={async () => {
                      try {
                        const preview = await fetchWithAuth('/api/admin/broadcast', {
                          method: 'POST',
                          body: JSON.stringify({
                            segment: broadcastSegment,
                            message: broadcastMessage,
                            preview_only: true
                          })
                        });
                        setBroadcastPreviewCount(preview.target_count || 0);
                      } catch (err) {
                        setPanelError(err instanceof Error ? err.message : 'Preview failed');
                      }
                    }}
                  >
                    Preview Recipients
                  </button>
                  <button
                    type="button"
                    disabled={broadcastSending || !broadcastMessage.trim()}
                    className="rounded-lg bg-adminAccent px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet disabled:cursor-not-allowed disabled:opacity-70"
                    onClick={async () => {
                      const confirmText = `This will send a WhatsApp message to ${broadcastPreviewCount ?? '?'} users. Continue?`;
                      if (!window.confirm(confirmText)) {
                        return;
                      }
                      setBroadcastSending(true);
                      try {
                        const result = await fetchWithAuth('/api/admin/broadcast', {
                          method: 'POST',
                          body: JSON.stringify({
                            segment: broadcastSegment,
                            message: broadcastMessage,
                            preview_only: false
                          })
                        });
                        alert(`Broadcast finished. Sent ${result.sent_count}/${result.target_count}.`);
                        setBroadcastMessage('');
                      } catch (err) {
                        setPanelError(err instanceof Error ? err.message : 'Broadcast failed');
                      } finally {
                        setBroadcastSending(false);
                      }
                    }}
                  >
                    {broadcastSending ? 'Sending...' : 'Confirm & Send'}
                  </button>
                </div>
                {broadcastPreviewCount !== null ? (
                  <p className="text-sm text-zinc-300">This will send to {broadcastPreviewCount} users.</p>
                ) : null}
              </div>
            </section>
          ) : null}
        </main>
      </div>

      {selectedUserDetail ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-4">
          <div className="max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-white/10 bg-[#10111d] p-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="font-heading text-2xl font-bold text-white">User Detail</h2>
                <p className="text-sm text-zinc-400">{selectedUserDetail.user?.phone_number}</p>
              </div>
              <button type="button" onClick={() => setSelectedUserDetail(null)} className="text-zinc-400 hover:text-white">
                Close
              </button>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <StatCard label="Total Sessions" value={selectedUserDetail.stats?.summary?.total_sessions || 0} />
              <StatCard label="Total Volume" value={`${Math.round(selectedUserDetail.stats?.summary?.total_volume_kg || 0)} kg`} />
              <StatCard label="Current Streak" value={`${selectedUserDetail.stats?.summary?.current_streak || 0}d`} />
            </div>
            <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-3">
              <p className="text-sm font-semibold text-white">Sessions</p>
              <div className="mt-2 space-y-2">
                {(selectedUserDetail.all_sessions || []).slice(0, 20).map((session) => (
                  <div key={session.id} className="rounded-lg border border-white/10 px-3 py-2 text-sm">
                    <p className="text-white">{formatDateTime(session.logged_at)}</p>
                    <p className="text-zinc-300">{(session.muscle_groups || []).join(', ') || 'Mixed'}</p>
                    <p className="text-zinc-400">{Math.round(session.total_volume || 0)} kg volume</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {messageBox.userId ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-4">
          <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#10111d] p-5">
            <h3 className="font-heading text-xl font-bold text-white">Send Custom WhatsApp Message</h3>
            <textarea
              value={messageBox.text}
              onChange={(event) => setMessageBox((current) => ({ ...current, text: event.target.value }))}
              rows={5}
              placeholder="Type your message..."
              className="mt-3 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm focus:border-adminAccent focus:outline-none"
            />
            <div className="mt-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setMessageBox({ userId: '', text: '', sending: false })}
                className="rounded-lg border border-white/15 px-3 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={messageBox.sending || !messageBox.text.trim()}
                className="rounded-lg bg-adminAccent px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-70"
                onClick={async () => {
                  setMessageBox((current) => ({ ...current, sending: true }));
                  try {
                    await fetchWithAuth('/api/admin/message', {
                      method: 'POST',
                      body: JSON.stringify({
                        user_id: messageBox.userId,
                        message: messageBox.text
                      })
                    });
                    setMessageBox({ userId: '', text: '', sending: false });
                  } catch (err) {
                    setPanelError(err instanceof Error ? err.message : 'Failed to send message');
                    setMessageBox((current) => ({ ...current, sending: false }));
                  }
                }}
              >
                {messageBox.sending ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
