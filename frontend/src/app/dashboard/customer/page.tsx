'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import { bookingApi, customerApi } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

const STATUS: Record<string, { label: string; cls: string }> = {
  pending: { label: 'در انتظار بررسی', cls: 'badge-warning' },
  confirmed: { label: 'تایید شده', cls: 'badge-success' },
  completed: { label: 'انجام شده', cls: 'badge-info' },
  rejected: { label: 'رد شده', cls: 'badge-danger' },
  cancelled: { label: 'لغو شده', cls: 'badge-muted' },
};

const formatDate = (value?: string) => {
  if (!value) return 'زمان نامشخص';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return 'زمان نامشخص';
  return d.toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' });
};

const getBookingTime = (b: any) =>
  b.scheduled_at || b.created_at || b.updated_at || b.date || b.start_time || '';

const getBookingTimestamp = (b: any) => {
  const raw = getBookingTime(b);
  const t = raw ? new Date(raw).getTime() : 0;
  return Number.isNaN(t) ? 0 : t;
};

export default function CustomerDashboard() {
  const { user, fetchMe, logout, setUser } = useAuthStore();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>({});
  const [bookings, setBookings] = useState<any[]>([]);
  const [docUploading, setDocUploading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!Cookies.get('access_token')) {
      router.replace('/login');
      return;
    }

    fetchMe().then(() => {
      const u = useAuthStore.getState().user;
      if (u?.is_staff || u?.is_superuser) router.replace('/dashboard/admin');
      else if (u?.role === 'lawyer') router.replace('/dashboard/lawyer');
      else if (u?.role !== 'customer') router.replace('/');
    });
  }, [fetchMe, router]);

  useEffect(() => {
    Promise.all([customerApi.dashboard(), bookingApi.list()])
      .then(([s, b]) => {
        setStats(s.data || {});
        setBookings(b.data.results || b.data || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const sortedBookings = useMemo(
    () => [...bookings].sort((a, b) => getBookingTimestamp(b) - getBookingTimestamp(a)),
    [bookings]
  );

  const cancelBooking = async (id: string) => {
    if (!confirm('این رزرو لغو شود؟')) return;
    await bookingApi.update(id, { status: 'cancelled' });
    setBookings((items) => items.map((x) => (x.id === id ? { ...x, status: 'cancelled' } : x)));
  };

  const uploadDoc = async (bookingId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || docUploading[bookingId]) return;

    const fd = new FormData();
    fd.append('file', file);
    fd.append('title', file.name);
    fd.append('document_type', 'other');
    fd.append('is_confidential', 'true');

    setDocUploading((x) => ({ ...x, [bookingId]: true }));
    try {
      const { data } = await bookingApi.uploadDocument(bookingId, fd);
      setBookings((items) =>
        items.map((x) =>
          x.id === bookingId ? { ...x, documents: [...(x.documents || []), data] } : x
        )
      );
    } catch {
      alert('بارگذاری فایل انجام نشد.');
    } finally {
      setDocUploading((x) => ({ ...x, [bookingId]: false }));
      e.target.value = '';
    }
  };
  const handleLogout = async () => {
    await logout();
    window.location.href = '/';
  };

  if (loading) {
    return (
      <DashboardShell user={user}>
        <section className="customer-dashboard-redesign">
          <div className="card customer-hero-skeleton" />
        </section>
      </DashboardShell>
    );
  }

  const refundableTotal = sortedBookings.reduce((sum, b) => sum + Number(b.refund_amount || 0), 0);
  const walletBalance = Number(stats.wallet_balance ?? refundableTotal ?? 0);

  const cards = [
    { label: 'کل رزروها', value: stats.total_bookings ?? sortedBookings.length, cls: 'badge-gold' },
    {
      label: 'تایید شده',
      value: stats.confirmed ?? sortedBookings.filter((b) => b.status === 'confirmed').length,
      cls: 'badge-success',
    },
    {
      label: 'انجام شده',
      value: stats.completed ?? sortedBookings.filter((b) => b.status === 'completed').length,
      cls: 'badge-info',
    },
  ];

  return (
    <DashboardShell user={user}>
      <section className="customer-dashboard-redesign animate-fade-in">
        <header className="customer-dashboard-hero glass">
          <div>
            <div className="section-eyebrow">پنل کاربر</div>
            <h1>سلام {user?.first_name || 'کاربر عزیز'} 👋</h1>
            <p className="muted">
              وضعیت رزروها، جزئیات جلسات و مدارک مرتبط با هر رزرو را در یک نمای مرتب و ساده ببین.
            </p>
          </div>

          <ProfileCard user={user} />
        </header>

        <section className="customer-stats-grid">
          {cards.map((c) => (
            <div className="card customer-stat-card" key={c.label}>
              <span className={`badge ${c.cls}`}>{c.label}</span>
              <div className="gold customer-stat-value">{Number(c.value).toLocaleString('fa-IR')}</div>
            </div>
          ))}
        </section>

        <section className="customer-smart-grid">
          <div className="card customer-wallet-card">
            <div>
              <div className="section-eyebrow">کیف پول</div>
              <h2>{walletBalance.toLocaleString('fa-IR')} تومان</h2>
              <p className="muted">اعتبار برگشتی کنسلی‌ها و تخفیف‌ها اینجا نمایش داده می‌شود و در رزروهای بعدی قابل استفاده است.</p>
            </div>
            <button className="btn btn-outline" type="button" onClick={() => alert('تراکنش‌های کیف پول در نسخه بعدی کامل‌تر نمایش داده می‌شود.')}>مشاهده تراکنش‌ها</button>
          </div>

          <div className="card customer-reminder-card">
            <div className="section-eyebrow">یادآور هوشمند</div>
            <h2>یادآور مشاوره فعال است</h2>
            <p className="muted">برای رزروهای تاییدشده، قبل از جلسه داخل پنل و بعداً از طریق SMS یادآوری ارسال می‌شود.</p>
          </div>
        </section>

        <section className="customer-bookings-section" id="all-bookings">
          <div className="customer-section-title centered-clean">
            <h2>همه رزروها</h2>
          </div>

          <div className="customer-booking-list">
            {sortedBookings.length ? (
              sortedBookings.map((booking) => (
                <BookingCard
                  key={booking.id}
                  booking={booking}
                  onCancel={cancelBooking}
                  onUpload={uploadDoc}
                  uploading={Boolean(docUploading[booking.id])}
                />
              ))
            ) : (
              <Empty text="هنوز رزروی ثبت نشده است." />
            )}
          </div>
        </section>

        <footer className="customer-logout-footer">
          <p className="muted">می‌خواهی از حساب کاربری خارج شوی؟</p>
          <button className="btn btn-danger customer-logout-btn" onClick={handleLogout}>
            خروج از حساب
          </button>
        </footer>
      </section>
    </DashboardShell>
  );
}

function DashboardShell({ children, user }: any) {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 18);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <main className="dashboard customer-dashboard-shell with-landing-navbar">
      <nav className={`navbar customer-top-navbar ${isScrolled ? 'is-scrolled' : ''}`}>
        <Link href="/" className="logo">
          <span className="logo-mark">ل</span> لکسارا
        </Link>
      </nav>

      <aside className="sidebar customer-sidebar">
        <ProfileCard user={user} compact />

        <nav>
          <a href="#overview" className="side-button active">
            <span>⬡</span>نمای کلی
          </a>
          <a href="#all-bookings" className="side-button">
            <span>📅</span>رزروها و مدارک
          </a>
        </nav>
      </aside>

      <section className="main-content" id="overview">
        {children}
      </section>
    </main>
  );
}

function ProfileCard({ user, compact = false }: any) {
  return (
    <div className={`customer-profile-card ${compact ? 'compact' : ''}`}>
      <div className="customer-profile-avatar-wrap static" title="پروفایل کاربر">
        <span className="avatar customer-avatar customer-avatar-letter">{user?.first_name?.[0] || 'ک'}</span>
      </div>

      <div className="customer-profile-text">
        <strong>{user?.full_name || 'کاربر لکسارا'}</strong>
        <span>حساب کاربری</span>
      </div>
    </div>
  );
}

function BookingCard({ booking, onCancel, onUpload, uploading }: any) {
  const st = STATUS[booking.status] || { label: booking.status || 'نامشخص', cls: 'badge-muted' };
  const docs = booking.documents || [];
  const lawyerName =
    booking.lawyer_name ||
    booking.lawyer?.full_name ||
    booking.lawyer?.user?.full_name ||
    booking.lawyer?.user?.first_name ||
    'وکیل نامشخص';

  const bookingType = booking.subject || booking.booking_type || booking.type || 'مشاوره حقوقی';
  const scheduledAt = formatDate(booking.scheduled_at || booking.date || booking.start_time);
  const code = String(booking.id || booking.uuid || '').slice(0, 8).toUpperCase();

  return (
    <article className="card customer-booking-card compact-mini">
      <div className="customer-booking-head">
        <div className="customer-booking-mainline">
          <span className={`badge ${st.cls}`}>{st.label}</span>
          <h3>{bookingType}</h3>
          <p className="muted">وکیل: {lawyerName}</p>
        </div>

        <div className="customer-booking-date">
          <span>زمان</span>
          <strong>{scheduledAt}</strong>
        </div>
      </div>

      <div className="customer-booking-details compact">
        <Detail label="کد رزرو" value={code || '—'} />
        <Detail label="مدت" value={`${Number(booking.duration_minutes || 60).toLocaleString('fa-IR')} دقیقه`} />
        <Detail label="وضعیت" value={st.label} />
      </div>

      {booking.description && (
        <div className="customer-case-summary">
          <strong>شرح مشکل</strong>
          <p>{String(booking.description).replace('نوع رزرو: تلفنی', '').replace('نوع رزرو: حضوری', '').replace('شرح مشکل:', '').trim()}</p>
        </div>
      )}

      {['confirmed', 'pending'].includes(booking.status) && !docs.length && (
        <div className="customer-upload-notice">
          شما می‌توانید مدارک مورد نیاز رزرو مشاوره خود را در همین بخش بارگذاری نمایید.
        </div>
      )}

      <section className={`customer-docs-box compact ${uploading ? 'is-uploading' : ''}`}>
        <div className="customer-docs-title">
          <div>
            <strong>مدارک</strong>
            <p className="muted">{docs.length ? `${docs.length.toLocaleString('fa-IR')} فایل بارگذاری شده` : 'هنوز مدرکی بارگذاری نشده است.'}</p>
          </div>

          <label className={`btn btn-outline btn-sm customer-upload-btn ${uploading ? 'disabled' : ''}`}>
            {uploading ? 'در حال بارگذاری...' : 'بارگذاری مدرک'}
            <input type="file" hidden disabled={uploading} onChange={(e) => onUpload(booking.id, e)} />
          </label>
        </div>

        {uploading && (
          <div className="customer-upload-loading">
            <span className="customer-upload-spinner" />
            <strong>در حال بارگذاری مدرک...</strong>
          </div>
        )}

        {docs.length ? (
          <div className="customer-doc-list compact">
            {docs.slice(0, 2).map((doc: any) => (
              <a
                key={doc.id || doc.file || doc.title}
                className="customer-doc-item"
                href={doc.file_url || doc.file}
                target="_blank"
                rel="noreferrer"
              >
                <span>📎</span>
                <div>
                  <strong>{doc.title || 'مدرک بارگذاری‌شده'}</strong>
                  <small>{doc.document_type || 'مدرک مرتبط'}</small>
                </div>
              </a>
            ))}
            {docs.length > 2 && <div className="customer-doc-more">+{(docs.length - 2).toLocaleString('fa-IR')} فایل دیگر</div>}
          </div>
        ) : !uploading ? (
          <div className="customer-doc-empty compact">مدرکی ثبت نشده</div>
        ) : null}
      </section>

      {['pending', 'confirmed'].includes(booking.status) && (
        <div className="customer-booking-actions">
          <button className="btn btn-danger btn-sm" onClick={() => onCancel(booking.id)}>
            لغو
          </button>
        </div>
      )}
    </article>
  );
}

function Detail({ label, value }: { label: string; value: any }) {
  return (
    <div className="customer-detail">
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="card customer-empty-card">
      <p className="muted">{text}</p>
    </div>
  );
}

{/* booking-reminder-line */}
