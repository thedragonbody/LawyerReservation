'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import Cookies from 'js-cookie';
import { adminApi, authApi } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

const LAWYER_STATUS: Record<string, string> = { pending: 'در انتظار بررسی', verified: 'تایید شده', rejected: 'رد شده' };
const BOOKING_STATUS: Record<string, string> = { pending: 'در انتظار', confirmed: 'تایید شده', completed: 'انجام شده', cancelled: 'لغو شده', rejected: 'رد شده' };
const nf = (v: any) => Number(v || 0).toLocaleString('fa-IR');
const formatDate = (value?: string) => {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' });
};

export default function AdminDashboardPage() {
  const { fetchMe, logout, setTokens, setUser } = useAuthStore();

  const [adminReady, setAdminReady] = useState(false);
  const [adminPhone, setAdminPhone] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>({});
  const [lawyers, setLawyers] = useState<any[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [revenue, setRevenue] = useState<any>({});
  const [financeOverview, setFinanceOverview] = useState<any>({});
  const [commission, setCommission] = useState<any>({});
  const [discounts, setDiscounts] = useState<any[]>([]);
  const [settlements, setSettlements] = useState<any[]>([]);
  const [cancellations, setCancellations] = useState<any[]>([]);
  const [siteContents, setSiteContents] = useState<any[]>([]);
  const [tab, setTab] = useState<'lawyers' | 'bookings' | 'users' | 'documents' | 'reviews' | 'revenue' | 'finance' | 'settlements' | 'discounts' | 'cancellations' | 'content'>('lawyers');
  const [status, setStatus] = useState('');
  const [query, setQuery] = useState('');
  const [savingId, setSavingId] = useState('');
  const [selectedLawyer, setSelectedLawyer] = useState<any>(null);
  const [editLawyer, setEditLawyer] = useState<any>({});

  const loadAll = async () => {
    setLoading(true);
    try {
      const [ov, lw, bk, us, docs, rv, rev, fin, com, disc, sets, cancels, contents] = await Promise.all([
        adminApi.overview(),
        adminApi.lawyers({ page_size: 20, status: tab === 'lawyers' ? status || undefined : undefined, q: query || undefined }),
        adminApi.bookings({ page_size: 20, status: tab === 'bookings' ? status || undefined : undefined, q: query || undefined }),
        adminApi.users({ page_size: 20, q: query || undefined }),
        adminApi.documents({ page_size: 20, q: query || undefined }),
        adminApi.reviews({ page_size: 20, q: query || undefined }),
        adminApi.revenue(),
        adminApi.financeOverview(),
        adminApi.commission(),
        adminApi.discounts({ page_size: 20 }),
        adminApi.settlements({ page_size: 20 }),
        adminApi.cancellations({ page_size: 20 }),
        adminApi.siteContent(),
      ]);
      setOverview(ov.data || {});
      setLawyers(lw.data?.results || []);
      setBookings(bk.data?.results || []);
      setUsers(us.data?.results || []);
      setDocuments(docs.data?.results || []);
      setReviews(rv.data?.results || []);
      setRevenue(rev.data || {});
      setFinanceOverview(fin.data || {});
      setCommission(com.data || {});
      setDiscounts(disc.data?.results || []);
      setSettlements(sets.data?.results || []);
      setCancellations(cancels.data?.results || []);
      setSiteContents(contents.data || []);
    } catch (err: any) {
      if (err?.response?.status === 401 || err?.response?.status === 403) {
        setAdminReady(false);
        setLoginError('برای ورود به پنل ادمین باید با حساب ادمین وارد شوید.');
        Cookies.remove('access_token', { path: '/' });
        Cookies.remove('refresh_token', { path: '/' });
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const boot = async () => {
      const token = Cookies.get('access_token');
      if (!token) { setAdminReady(false); setLoading(false); return; }
      await fetchMe();
      const u = useAuthStore.getState().user;
      if (u?.is_staff || u?.is_superuser) { setAdminReady(true); await loadAll(); }
      else { setAdminReady(false); setLoading(false); setLoginError('این ورود ادمین است. لطفاً مشخصات ادمین را وارد کنید.'); }
    };
    boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitAdminLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoginError('');
    if (!adminPhone.trim() || !adminPassword) { setLoginError('شماره موبایل و رمز عبور ادمین را وارد کنید.'); return; }
    setLoginLoading(true);
    try {
      const { data } = await authApi.adminLogin(adminPhone.trim(), adminPassword);
      setTokens(data.access, data.refresh);
      setUser(data.user);
      if (!data.user?.is_staff && !data.user?.is_superuser) {
        setLoginError('این حساب دسترسی ادمین ندارد.');
        setAdminReady(false);
        return;
      }
      setAdminReady(true);
      setAdminPassword('');
      await loadAll();
    } catch (err: any) {
      setLoginError(err?.response?.data?.detail || 'ورود ادمین انجام نشد.');
      setAdminReady(false);
    } finally { setLoginLoading(false); }
  };

  const filteredTitle = useMemo(() => {
    if (tab === 'lawyers') return 'جزئیات و ویرایش وکلا';
    if (tab === 'bookings') return 'مدیریت رزروها';
    if (tab === 'users') return 'مدیریت کاربران';
    if (tab === 'documents') return 'مدارک بارگذاری‌شده';
    if (tab === 'reviews') return 'مدیریت کامنت‌ها و امتیازها';
    return 'گزارش درآمد';
  }, [tab]);

  const updateLawyerStatus = async (id: string, next: 'verified' | 'rejected' | 'pending') => {
    setSavingId(id);
    try {
      const { data } = await adminApi.verifyLawyer(id, next);
      setLawyers((items) => items.map((x) => (x.id === id ? data : x)));
      const ov = await adminApi.overview();
      setOverview(ov.data || {});
    } finally { setSavingId(''); }
  };

  const updateBookingStatus = async (id: string, next: string) => {
    setSavingId(id);
    try {
      const { data } = await adminApi.updateBooking(id, { status: next });
      setBookings((items) => items.map((x) => (x.id === id ? data : x)));
      const ov = await adminApi.overview();
      setOverview(ov.data || {});
    } finally { setSavingId(''); }
  };

  const toggleFeatured = async (lawyer: any) => {
    setSavingId(lawyer.id);
    try {
      const { data } = await adminApi.updateLawyer(lawyer.id, { is_featured: !lawyer.is_featured });
      setLawyers((items) => items.map((x) => (x.id === lawyer.id ? data : x)));
    } finally { setSavingId(''); }
  };

  const openLawyerDetails = async (lawyer: any) => {
    const { data } = await adminApi.lawyerDetail(lawyer.id);
    setSelectedLawyer(data);
    setEditLawyer({
      headline: data.headline || '',
      bio: data.bio || '',
      city: data.city || '',
      office_address: data.office_address || '',
      consultation_fee: data.consultation_fee || '',
      years_experience: data.years_experience || '',
      verification_status: data.verification_status || 'pending',
      is_accepting_clients: !!data.is_accepting_clients,
      is_featured: !!data.is_featured,
    });
  };

  const saveLawyerDetails = async () => {
    if (!selectedLawyer) return;
    setSavingId(selectedLawyer.id);
    try {
      const { data } = await adminApi.updateLawyer(selectedLawyer.id, editLawyer);
      setSelectedLawyer(data);
      setLawyers((items) => items.map((x) => (x.id === data.id ? data : x)));
    } finally { setSavingId(''); }
  };

  const toggleUserActive = async (u: any) => {
    setSavingId(u.id);
    try {
      const { data } = await adminApi.updateUser(u.id, { is_active: !u.is_active });
      setUsers((items) => items.map((x) => (x.id === u.id ? data : x)));
    } finally { setSavingId(''); }
  };

  const deleteReview = async (review: any) => {
    if (!confirm('این نظر حذف شود؟')) return;
    setSavingId(review.id);
    try {
      await adminApi.deleteReview(review.id);
      setReviews((items) => items.filter((x) => x.id !== review.id));
    } finally { setSavingId(''); }
  };

  const handleLogout = async () => { await logout(); };

  const saveCommission = async () => {
    const value = prompt('درصد کمیسیون را وارد کنید:', String(commission.commission_percent || 9));
    if (!value) return;
    const { data } = await adminApi.updateCommission({ commission_percent: value, title: 'کمیسیون پیش‌فرض', is_active: true });
    setCommission(data);
    await loadAll();
  };

  const createDiscount = async () => {
    const code = prompt('کد تخفیف را وارد کنید:');
    if (!code) return;
    const percent = prompt('درصد تخفیف:', '10') || '0';
    const { data } = await adminApi.createDiscount({ code, percent: Number(percent), is_active: true });
    setDiscounts((items) => [data, ...items]);
  };

  const createSettlement = async () => {
    const lawyer = prompt('ID وکیل را وارد کنید:');
    if (!lawyer) return;
    const amount = prompt('مبلغ ناخالص تسویه:', '0') || '0';
    const { data } = await adminApi.createSettlement({ lawyer, amount: Number(amount), status: 'pending' });
    setSettlements((items) => [data, ...items]);
  };

  const saveContent = async (item: any) => {
    const title = prompt('عنوان:', item.title || '') ?? item.title;
    const body = prompt('متن:', item.body || '') ?? item.body;
    const { data } = await adminApi.updateSiteContent({ key: item.key, title, body, is_active: item.is_active });
    setSiteContents((items) => items.map((x) => x.key === data.key ? data : x));
  };

  const cards = [
    ['کل کاربران', overview.users_total],
    ['وکلای تاییدشده', overview.lawyers_verified],
    ['در انتظار تایید', overview.lawyers_pending],
    ['کل رزروها', overview.bookings_total],
    ['رزروهای امروز', overview.today_bookings],
    ['مدارک', overview.documents_total],
    ['درآمد تخمینی', `${nf(overview.estimated_revenue)} تومان`],
  ];

  if (!adminReady) {
    return (
      <main className="admin-login-page">
        <Link href="/" className="logo admin-login-logo"><span className="logo-mark">ل</span> لکسارا</Link>
        <form className="admin-login-card glass" onSubmit={submitAdminLogin}>
          <div className="section-eyebrow">ورود اختصاصی ادمین</div>
          <h1>ورود به پنل مدیریت</h1>
          <p className="muted">برای ورود، شماره موبایل و رمز عبور ادمین را وارد کنید.</p>
          {loginError && <div className="badge badge-danger admin-login-error">{loginError}</div>}
          <label>شماره موبایل ادمین<input className="input" value={adminPhone} onChange={(e) => setAdminPhone(e.target.value)} placeholder="09123456789" dir="ltr" /></label>
          <label>رمز عبور<input className="input" type="password" value={adminPassword} onChange={(e) => setAdminPassword(e.target.value)} placeholder="رمز عبور ادمین" dir="ltr" /></label>
          <button className="btn btn-gold" disabled={loginLoading}>{loginLoading ? 'در حال ورود...' : 'ورود به پنل ادمین'}</button>
        </form>
      </main>
    );
  }

  return (
    <main className="admin-dashboard-page">
      <nav className="navbar admin-navbar">
        <Link href="/" className="logo"><span className="logo-mark">ل</span> لکسارا</Link>
        <div className="nav-links">
          <Link href="/lawyers" className="nav-link">وکلا</Link>
          <button className="btn btn-outline btn-sm" onClick={handleLogout}>خروج</button>
        </div>
      </nav>

      <section className="admin-shell">
        <header className="admin-hero glass">
          <div>
            <div className="section-eyebrow">پنل ادمین مرحله دوم</div>
            <h1>مدیریت حرفه‌ای لکسارا</h1>
            <p className="muted">جزئیات وکلا، ویرایش، مدارک، کاربران، نظرها و گزارش درآمد.</p>
          </div>
          <strong className="badge badge-gold">ادمین</strong>
        </header>

        <section className="admin-feature-modules-grid">
          <div className="card admin-wallet-feature-note">
            <strong>کیف پول کاربران</strong>
            <span>اعتبار برگشتی کنسلی‌ها و تخفیف‌ها از بخش مالی و کاربران قابل پیگیری است.</span>
          </div>
          <div className="card admin-wallet-feature-note">
            <strong>تسویه حرفه‌ای وکلا</strong>
            <span>درخواست‌های تسویه، کمیسیون و وضعیت پرداخت وکلا از تب «تسویه‌ها» مدیریت می‌شود.</span>
          </div>
          <div className="card admin-wallet-feature-note">
            <strong>یادآور مشاوره</strong>
            <span>رزروهای تاییدشده وضعیت یادآور دارند و برای اتصال SMS آماده هستند.</span>
          </div>
        </section>

        <section className="admin-stats-grid">
          {cards.map(([label, value]: any) => (
            <div className="card admin-stat-card" key={label}><span>{label}</span><strong>{typeof value === 'string' ? value : nf(value)}</strong></div>
          ))}
        </section>

        <section className="card admin-panel-card">
          <div className="admin-panel-head">
            <div><div className="section-eyebrow">{filteredTitle}</div><h2>{filteredTitle}</h2></div>
            <div className="admin-tabs">
              <button className={tab === 'lawyers' ? 'active' : ''} onClick={() => setTab('lawyers')}>وکلا</button>
              <button className={tab === 'bookings' ? 'active' : ''} onClick={() => setTab('bookings')}>رزروها</button>
              <button className={tab === 'users' ? 'active' : ''} onClick={() => setTab('users')}>کاربران</button>
              <button className={tab === 'documents' ? 'active' : ''} onClick={() => setTab('documents')}>مدارک</button>
              <button className={tab === 'reviews' ? 'active' : ''} onClick={() => setTab('reviews')}>نظرها</button>
              <button className={tab === 'revenue' ? 'active' : ''} onClick={() => setTab('revenue')}>درآمد</button>
              <button className={tab === 'finance' ? 'active' : ''} onClick={() => setTab('finance')}>مالی</button>
              <button className={tab === 'settlements' ? 'active' : ''} onClick={() => setTab('settlements')}>تسویه‌ها</button>
              <button className={tab === 'discounts' ? 'active' : ''} onClick={() => setTab('discounts')}>تخفیف</button>
              <button className={tab === 'cancellations' ? 'active' : ''} onClick={() => setTab('cancellations')}>لغو و Refund</button>
              <button className={tab === 'content' ? 'active' : ''} onClick={() => setTab('content')}>محتوا</button>
            </div>
          </div>

          <div className="admin-filters">
            <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="جستجو..." />
            {(tab === 'lawyers' || tab === 'bookings') && (
              <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">همه وضعیت‌ها</option>
                {tab === 'lawyers' ? (
                  <>
                    <option value="pending">در انتظار بررسی</option>
                    <option value="verified">تایید شده</option>
                    <option value="rejected">رد شده</option>
                  </>
                ) : (
                  <>
                    <option value="pending">در انتظار</option>
                    <option value="confirmed">تایید شده</option>
                    <option value="completed">انجام شده</option>
                    <option value="cancelled">لغو شده</option>
                    <option value="rejected">رد شده</option>
                  </>
                )}
              </select>
            )}
            <button className="btn btn-gold" onClick={loadAll}>اعمال فیلتر</button>
          </div>

          {loading ? <div className="admin-empty">در حال دریافت اطلاعات...</div> : (
            <>
              {tab === 'lawyers' && (
                <div className="admin-list">
                  <div className="admin-featured-note card">
                    <strong>مدیریت وکلای پیشنهادی هوم</strong>
                    <span>با دکمه «افزودن به پیشنهادهای هوم» می‌توانید وکلا را در بخش «پیشنهادهای منتخب لکسارا» صفحه خانه نمایش دهید یا حذف کنید.</span>
                  </div>
                  {lawyers.map((l) => (
                    <article className="admin-row" key={l.id}>
                      <div>
                        <strong>{l.full_name || 'وکیل بدون نام'} {l.is_featured && <span className="admin-home-featured-badge">پیشنهادی هوم</span>}</strong>
                        <span>{l.phone} · {l.city || 'بدون شهر'} · {LAWYER_STATUS[l.verification_status] || l.verification_status}</span>
                        <small>{l.headline || 'عنوان ثبت نشده'} {l.office_address ? `· ${l.office_address}` : ''}</small>
                      </div>
                      <div className="admin-row-actions">
                        <button className="btn btn-outline btn-sm" onClick={() => openLawyerDetails(l)}>جزئیات و ویرایش</button>
                        {l.bar_document_url && <a className="btn btn-outline btn-sm" href={l.bar_document_url} target="_blank" rel="noreferrer">مدرک</a>}
                        <button className="btn btn-outline btn-sm admin-featured-toggle" disabled={savingId === l.id} onClick={() => toggleFeatured(l)}>{l.is_featured ? 'حذف از پیشنهادهای هوم' : 'افزودن به پیشنهادهای هوم'}</button>
                        <button className="btn btn-gold btn-sm" disabled={savingId === l.id} onClick={() => updateLawyerStatus(l.id, 'verified')}>تایید</button>
                        <button className="btn btn-danger btn-sm" disabled={savingId === l.id} onClick={() => updateLawyerStatus(l.id, 'rejected')}>رد</button>
                      </div>
                    </article>
                  ))}
                  {!lawyers.length && <div className="admin-empty">وکیلی پیدا نشد.</div>}
                </div>
              )}

              {tab === 'bookings' && (
                <div className="admin-list">
                  {bookings.map((b) => (
                    <article className="admin-row" key={b.id}>
                      <div><strong>{b.subject || b.type_display || 'رزرو مشاوره'}</strong><span>موکل: {b.customer_name} · وکیل: {b.lawyer_name}</span><small>{formatDate(b.scheduled_at)} · {BOOKING_STATUS[b.status] || b.status} · مدارک: {nf(b.documents_count)}</small></div>
                      <div className="admin-row-actions">
                        <button className="btn btn-outline btn-sm" onClick={() => updateBookingStatus(b.id, 'confirmed')}>تایید</button>
                        <button className="btn btn-outline btn-sm" onClick={() => updateBookingStatus(b.id, 'completed')}>انجام شد</button>
                        <button className="btn btn-danger btn-sm" onClick={() => updateBookingStatus(b.id, 'cancelled')}>لغو</button>
                      </div>
                    </article>
                  ))}
                  {!bookings.length && <div className="admin-empty">رزروی پیدا نشد.</div>}
                </div>
              )}

              {tab === 'users' && (
                <div className="admin-list">
                  {users.map((u) => (
                    <article className="admin-row" key={u.id}>
                      <div><strong>{u.full_name || 'کاربر بدون نام'}</strong><span>{u.phone} · {u.role === 'lawyer' ? 'وکیل' : 'کاربر'} · {u.is_active ? 'فعال' : 'غیرفعال'}</span><small>{formatDate(u.created_at)}</small></div>
                      <div className="admin-row-actions"><button className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-gold'}`} disabled={savingId === u.id} onClick={() => toggleUserActive(u)}>{u.is_active ? 'غیرفعال کردن' : 'فعال کردن'}</button></div>
                    </article>
                  ))}
                  {!users.length && <div className="admin-empty">کاربری پیدا نشد.</div>}
                </div>
              )}

              {tab === 'documents' && (
                <div className="admin-list">
                  {documents.map((d) => (
                    <article className="admin-row" key={d.id}>
                      <div><strong>{d.title || 'مدرک'}</strong><span>{d.uploaded_by_name || 'نامشخص'} · {d.mime_type || 'فایل'}</span><small>{formatDate(d.uploaded_at)}</small></div>
                      <div className="admin-row-actions">{d.file_url && <a href={d.file_url} className="btn btn-outline btn-sm" target="_blank" rel="noreferrer">مشاهده</a>}</div>
                    </article>
                  ))}
                  {!documents.length && <div className="admin-empty">مدرکی پیدا نشد.</div>}
                </div>
              )}

              {tab === 'reviews' && (
                <div className="admin-list">
                  {reviews.map((r) => (
                    <article className="admin-row" key={r.id}>
                      <div><strong>{'★'.repeat(Number(r.rating || 0))} برای {r.lawyer_name}</strong><span>کاربر: {r.customer_name || 'ناشناس'} · {formatDate(r.created_at)}</span><small>{r.comment || 'بدون متن'}</small></div>
                      <div className="admin-row-actions"><button className="btn btn-danger btn-sm" disabled={savingId === r.id} onClick={() => deleteReview(r)}>حذف نظر</button></div>
                    </article>
                  ))}
                  {!reviews.length && <div className="admin-empty">نظری پیدا نشد.</div>}
                </div>
              )}

              
              {tab === 'finance' && (
                <div className="admin-list">
                  <div className="admin-revenue-summary">
                    <strong>{nf(financeOverview.gross_revenue)} تومان</strong>
                    <span>درآمد ناخالص · کمیسیون {nf(financeOverview.commission_percent)}٪ · سهم وکلا {nf(financeOverview.lawyers_payable)} تومان</span>
                    <button className="btn btn-gold btn-sm" onClick={saveCommission}>ویرایش کمیسیون</button>
                  </div>
                  {(financeOverview.results || []).map((r: any) => (
                    <article className="admin-row" key={r.booking_id}>
                      <div><strong>{nf(r.amount)} تومان</strong><span>کمیسیون: {nf(r.commission_amount)} · سهم وکیل: {nf(r.net_amount)}</span><small>{r.lawyer_name} · {r.customer_name}</small></div>
                    </article>
                  ))}
                </div>
              )}

              {tab === 'settlements' && (
                <div className="admin-list">
                  <div className="admin-row-actions"><button className="btn btn-gold btn-sm" onClick={createSettlement}>ثبت تسویه جدید</button></div>
                  {settlements.map((s) => (
                    <article className="admin-row" key={s.id}>
                      <div><strong>{s.lawyer_name}</strong><span>خالص: {nf(s.net_amount)} تومان · کمیسیون: {nf(s.commission_amount)}</span><small>{s.status === 'paid' ? 'پرداخت شده' : 'در انتظار'} · {formatDate(s.created_at)}</small></div>
                    </article>
                  ))}
                  {!settlements.length && <div className="admin-empty">تسویه‌ای ثبت نشده است.</div>}
                </div>
              )}

              {tab === 'discounts' && (
                <div className="admin-list">
                  <div className="admin-row-actions"><button className="btn btn-gold btn-sm" onClick={createDiscount}>ساخت کد تخفیف</button></div>
                  {discounts.map((d) => (
                    <article className="admin-row" key={d.id}>
                      <div><strong>{d.code}</strong><span>{nf(d.percent)}٪ تخفیف · {d.is_active ? 'فعال' : 'غیرفعال'}</span><small>استفاده: {nf(d.used_count)} / {nf(d.usage_limit || 0)}</small></div>
                    </article>
                  ))}
                  {!discounts.length && <div className="admin-empty">کد تخفیفی ثبت نشده است.</div>}
                </div>
              )}

              {tab === 'cancellations' && (
                <div className="admin-list">
                  {cancellations.map((c) => (
                    <article className="admin-row" key={c.id}>
                      <div><strong>{c.booking_subject || 'لغو رزرو'}</strong><span>موکل: {c.customer_name} · وکیل: {c.lawyer_name}</span><small>Refund: {nf(c.refund_amount)} تومان · جریمه: {nf(c.cancellation_fee)} · {c.refund_status}</small></div>
                    </article>
                  ))}
                  {!cancellations.length && <div className="admin-empty">گزارش لغوی ثبت نشده است.</div>}
                </div>
              )}

              {tab === 'content' && (
                <div className="admin-list">
                  {siteContents.map((c) => (
                    <article className="admin-row" key={c.key}>
                      <div><strong>{c.title || c.key}</strong><span>{c.key} · {c.is_active ? 'فعال' : 'غیرفعال'}</span><small>{String(c.body || '').slice(0, 120)}</small></div>
                      <div className="admin-row-actions"><button className="btn btn-outline btn-sm" onClick={() => saveContent(c)}>ویرایش محتوا</button></div>
                    </article>
                  ))}
                  {!siteContents.length && <div className="admin-empty">محتوایی ثبت نشده است.</div>}
                </div>
              )}

{tab === 'revenue' && (
                <div className="admin-list">
                  <div className="admin-revenue-summary">
                    <strong>{nf(revenue.estimated_revenue)} تومان</strong>
                    <span>درآمد تخمینی از {nf(revenue.count)} رزرو تایید/انجام‌شده</span>
                  </div>
                  {(revenue.results || []).map((r: any) => (
                    <article className="admin-row" key={r.booking_id}>
                      <div><strong>{nf(r.amount)} تومان</strong><span>وکیل: {r.lawyer_name} · موکل: {r.customer_name}</span><small>{formatDate(r.created_at)} · {BOOKING_STATUS[r.status] || r.status}</small></div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </section>

      {selectedLawyer && (
        <div className="admin-modal-backdrop" onClick={() => setSelectedLawyer(null)}>
          <section className="admin-lawyer-modal glass" onClick={(e) => e.stopPropagation()}>
            <div className="admin-panel-head">
              <div><div className="section-eyebrow">جزئیات کامل وکیل</div><h2>{selectedLawyer.full_name}</h2></div>
              <button className="btn btn-outline btn-sm" onClick={() => setSelectedLawyer(null)}>بستن</button>
            </div>
            <div className="admin-lawyer-detail-grid">
              <Detail label="شماره موبایل" value={selectedLawyer.phone} />
              <Detail label="شماره پروانه" value={selectedLawyer.bar_number} />
              <Detail label="امتیاز" value={`${Number(selectedLawyer.average_rating || 0).toFixed(1)} از ۵`} />
              <Detail label="رزروها" value={nf(selectedLawyer.total_bookings)} />
              <Detail label="تخصص‌ها" value={(selectedLawyer.practice_areas_fa || []).join('، ') || 'ثبت نشده'} />
              <Detail label="آدرس" value={selectedLawyer.office_address || 'ثبت نشده'} />
            </div>

            <div className="admin-edit-grid">
              <label>عنوان<input className="input" value={editLawyer.headline} onChange={(e) => setEditLawyer((x: any) => ({ ...x, headline: e.target.value }))} /></label>
              <label>شهر<input className="input" value={editLawyer.city} onChange={(e) => setEditLawyer((x: any) => ({ ...x, city: e.target.value }))} /></label>
              <label>هزینه مشاوره<input className="input" value={editLawyer.consultation_fee} onChange={(e) => setEditLawyer((x: any) => ({ ...x, consultation_fee: e.target.value }))} /></label>
              <label>سابقه<input className="input" value={editLawyer.years_experience} onChange={(e) => setEditLawyer((x: any) => ({ ...x, years_experience: e.target.value }))} /></label>
              <label>وضعیت
                <select className="select" value={editLawyer.verification_status} onChange={(e) => setEditLawyer((x: any) => ({ ...x, verification_status: e.target.value }))}>
                  <option value="pending">در انتظار</option><option value="verified">تایید شده</option><option value="rejected">رد شده</option>
                </select>
              </label>
              <label className="admin-edit-full">آدرس دفتر<textarea className="input" rows={3} value={editLawyer.office_address} onChange={(e) => setEditLawyer((x: any) => ({ ...x, office_address: e.target.value }))} /></label>
              <label className="admin-edit-full">بیوگرافی<textarea className="input" rows={4} value={editLawyer.bio} onChange={(e) => setEditLawyer((x: any) => ({ ...x, bio: e.target.value }))} /></label>
            </div>

            <div className="admin-row-actions">
              {selectedLawyer.bar_document_url && <a className="btn btn-outline" href={selectedLawyer.bar_document_url} target="_blank" rel="noreferrer">مشاهده مدرک وکالت</a>}
              <button className="btn btn-gold" disabled={savingId === selectedLawyer.id} onClick={saveLawyerDetails}>ذخیره تغییرات</button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function Detail({ label, value }: any) {
  return <div className="admin-detail-box"><span>{label}</span><strong>{value || '—'}</strong></div>;
}
