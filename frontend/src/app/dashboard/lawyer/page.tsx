'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import { bookingApi, lawyerApi } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

const STATUS: Record<string, { label: string; cls: string }> = {
  pending: { label: 'در انتظار بررسی', cls: 'badge-warning' },
  confirmed: { label: 'تایید شده', cls: 'badge-success' },
  completed: { label: 'انجام شده', cls: 'badge-info' },
  rejected: { label: 'رد شده', cls: 'badge-danger' },
  cancelled: { label: 'لغو شده', cls: 'badge-muted' },
};

const AREAS: Record<string, string> = {
  corporate: 'حقوق شرکت‌ها',
  criminal: 'کیفری و جزایی',
  family: 'خانواده و طلاق',
  immigration: 'مهاجرت',
  real_estate: 'ملک و املاک',
  intellectual_property: 'مالکیت فکری',
  employment: 'کار و استخدام',
  tax: 'مالیات',
  personal_injury: 'خسارت و دیه',
  estate_planning: 'وصیت و ارث',
  civil_litigation: 'دعاوی حقوقی',
  bankruptcy: 'ورشکستگی',
  healthcare: 'حقوق پزشکی',
  environmental: 'محیط زیست',
  international: 'حقوق بین‌الملل',
};

type DaySlot = { start_time: string; end_time: string };

const formatDate = (value?: string) => {
  if (!value) return 'زمان نامشخص';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return 'زمان نامشخص';
  return d.toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' });
};

const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());
const dateKey = (date: Date) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};
const sameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
const getBookingTime = (b: any) => b.scheduled_at || b.created_at || b.updated_at || b.date || b.start_time || '';
const getBookingTimestamp = (b: any) => {
  const raw = getBookingTime(b);
  const t = raw ? new Date(raw).getTime() : 0;
  return Number.isNaN(t) ? 0 : t;
};

export default function LawyerDashboard() {
  const { user, fetchMe, logout } = useAuthStore();
  const router = useRouter();
  const [scrolled, setScrolled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<any>({});
  const [bookings, setBookings] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [selectedDate, setSelectedDate] = useState(() => startOfDay(new Date()));
  const [sheetOpen, setSheetOpen] = useState(false);
  const [daySlots, setDaySlots] = useState<DaySlot[]>([{ start_time: '09:00', end_time: '17:00' }]);
  const [dayClosed, setDayClosed] = useState(false);
  const [closedDayKeys, setClosedDayKeys] = useState<string[]>([]);
  const [scheduleMessage, setScheduleMessage] = useState('');
  const [scheduleAutoSaving, setScheduleAutoSaving] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');
  const [profileAttention, setProfileAttention] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState('');
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarReadyToSave, setAvatarReadyToSave] = useState(false);
  const [areasOpen, setAreasOpen] = useState(false);
  const [revenueSheetOpen, setRevenueSheetOpen] = useState(false);
  const [profileMiniOpen, setProfileMiniOpen] = useState(false);
  const [profileForm, setProfileForm] = useState({
    bar_number: '',
    areas: [] as string[],
    headline: '',
    years_experience: '',
    consultation_fee: '',
    office_address: '',
    bar_document: null as File | null,
    avatar: null as File | null,
  });

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (!Cookies.get('access_token')) {
      router.replace('/login');
      return;
    }
    fetchMe().then(() => {
      const u = useAuthStore.getState().user;
      if (u?.is_staff || u?.is_superuser) router.replace('/dashboard/admin');
      else if (u?.role === 'customer') router.replace('/dashboard/customer');
      else if (u?.role !== 'lawyer') router.replace('/');
    });
  }, [fetchMe, router]);

  useEffect(() => {
    Promise.allSettled([lawyerApi.dashboard(), bookingApi.lawyerBookings(), lawyerApi.myProfile()])
      .then((res) => {
        if (res[0].status === 'fulfilled') setDashboard(res[0].value.data || {});
        if (res[1].status === 'fulfilled') setBookings(res[1].value.data.results || res[1].value.data || []);
        if (res[2].status === 'fulfilled') {
          const p = res[2].value.data || null;
          setProfile(p);
          const areas = p?.practice_areas?.map?.((x: any) => x.area) || [];
          setProfileForm({
            bar_number: p?.bar_number && !String(p.bar_number).startsWith('PENDING') ? p.bar_number : '',
            areas,
            headline: p?.headline || '',
            years_experience: p?.years_experience ? String(p.years_experience) : '',
            consultation_fee: p?.consultation_fee ? String(p.consultation_fee) : '',
            office_address: p?.office_address || '',
            bar_document: null,
            avatar: null,
          });
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const sortedBookings = useMemo(
    () => [...bookings].sort((a, b) => getBookingTimestamp(a) - getBookingTimestamp(b)),
    [bookings]
  );

  const calendarDays = useMemo(() => {
    const today = startOfDay(new Date());
    return Array.from({ length: 8 }, (_, i) => {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      return d;
    });
  }, []);

  const refreshCalendarClosedDays = async () => {
    try {
      const results = await Promise.allSettled(
        calendarDays.map((day) => lawyerApi.availabilityDay(dateKey(startOfDay(day))))
      );
      const closed = results
        .map((res, idx) => {
          if (res.status !== 'fulfilled') return null;
          const items = res.value.data || [];
          return items.some((x: any) => x.is_closed) ? dateKey(startOfDay(calendarDays[idx])) : null;
        })
        .filter(Boolean) as string[];
      setClosedDayKeys(closed);
    } catch {
      setClosedDayKeys([]);
    }
  };

  useEffect(() => {
    refreshCalendarClosedDays();
  }, [calendarDays]);

  const selectedBookings = useMemo(
    () =>
      sortedBookings
        .filter((b) => {
          const raw = getBookingTime(b);
          if (!raw) return false;
          const d = new Date(raw);
          return !Number.isNaN(d.getTime()) && sameDay(d, selectedDate);
        })
        .sort((a, b) => getBookingTimestamp(a) - getBookingTimestamp(b)),
    [sortedBookings, selectedDate]
  );

  const bookingsByDate = useMemo(() => {
    const map = new Map<string, any[]>();
    for (const b of bookings) {
      const raw = getBookingTime(b);
      if (!raw) continue;
      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) continue;
      const key = dateKey(startOfDay(d));
      map.set(key, [...(map.get(key) || []), b]);
    }
    return map;
  }, [bookings]);

  const isLawyerProfileComplete = () => {
    const cleanBar = String(profileForm.bar_number || '').trim();
    const cleanHeadline = String(profileForm.headline || '').trim();
    const hasBarNumber = Boolean(cleanBar) && !cleanBar.startsWith('PENDING');
    const hasAreas = Array.isArray(profileForm.areas) && profileForm.areas.length > 0;
    const hasHeadline = Boolean(cleanHeadline);
    const hasExperience = String(profileForm.years_experience || '').trim() !== '';
    const hasFee = String(profileForm.consultation_fee || '').trim() !== '';
    const hasDocument = Boolean(profile?.bar_document_url || profileForm.bar_document);

    return hasBarNumber && hasAreas && hasHeadline && hasExperience && hasFee && hasDocument;
  };

  const requireCompletedProfile = () => {
    setProfileMessage('لطفا اول مشخصات خود را تکمیل کنید');
    setProfileAttention(true);

    window.setTimeout(() => {
      document.getElementById('lawyer-profile-card')?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }, 80);

    window.setTimeout(() => setProfileAttention(false), 2600);
  };

  const openDaySheet = async (day: Date) => {
    if (!isLawyerProfileComplete()) {
      requireCompletedProfile();
      return;
    }

    const d = startOfDay(day);
    setSelectedDate(d);
    setSheetOpen(true);
    setScheduleMessage('');
    try {
      const { data } = await lawyerApi.availabilityDay(dateKey(d));
      const items = data || [];
      setDayClosed(Boolean(items.find((x: any) => x.is_closed)));
      const slots = items
        .filter((x: any) => !x.is_closed)
        .map((x: any) => ({ start_time: String(x.start_time || '').slice(0, 5), end_time: String(x.end_time || '').slice(0, 5) }));
      setDaySlots(slots.length ? slots : [{ start_time: '09:00', end_time: '17:00' }]);
      refreshCalendarClosedDays();
    } catch {
      setDayClosed(false);
      setDaySlots([{ start_time: '09:00', end_time: '17:00' }]);
    }
  };

  const saveDaySchedule = async () => {
    setScheduleMessage('');
    try {
      await lawyerApi.saveAvailabilityDay({
        date: dateKey(selectedDate),
        is_closed: dayClosed,
        slots: dayClosed ? [] : daySlots,
      });
      setScheduleMessage('برنامه کاری این روز ذخیره شد.');
      refreshCalendarClosedDays();
    } catch (err: any) {
      setScheduleMessage(err.response?.data?.detail || 'ذخیره برنامه کاری انجام نشد.');
    }
  };

  useEffect(() => {
    if (!sheetOpen) return;

    const scheduleAutoSaveTimer = window.setTimeout(async () => {
      try {
        setScheduleAutoSaving(true);
        await lawyerApi.saveAvailabilityDay({
          date: dateKey(selectedDate),
          is_closed: dayClosed,
          slots: dayClosed ? [] : daySlots,
        });
        refreshCalendarClosedDays();
      } catch {
        // Silent autosave. Manual button below still shows explicit success/errors.
      } finally {
        setScheduleAutoSaving(false);
      }
    }, 800);

    return () => window.clearTimeout(scheduleAutoSaveTimer);
  }, [sheetOpen, selectedDate, dayClosed, daySlots]);

  const updateStatus = async (id: string, status: string) => {
    await bookingApi.update(id, { status });
    setBookings((items) => items.map((x) => (x.id === id ? { ...x, status } : x)));
  };

  const toggleArea = (area: string) => {
    setProfileForm((f) => ({ ...f, areas: f.areas.includes(area) ? f.areas.filter((x) => x !== area) : [...f.areas, area] }));
  };

  const handleAvatarChange = (file?: File | null) => {
    if (!file) return;

    setProfileForm((f) => ({ ...f, avatar: file }));
    const nextPreview = URL.createObjectURL(file);
    setAvatarPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return nextPreview;
    });
    setAvatarReadyToSave(true);
    setProfileMessage('تصویر جدید انتخاب شد. برای ثبت نهایی روی ثبت عکس پروفایل بزنید.');
  };

  const saveAvatarProfile = async () => {
    if (!profileForm.avatar) {
      setProfileMessage('ابتدا یک تصویر انتخاب کنید.');
      return;
    }

    const fd = new FormData();
    fd.append('avatar', profileForm.avatar);

    try {
      setAvatarUploading(true);
      const { data } = await lawyerApi.updateProfile(fd);
      setProfile(data);
      await fetchMe();
      setAvatarReadyToSave(false);
      setProfileForm((f) => ({ ...f, avatar: null }));
      setProfileMessage('تصویر پروفایل با موفقیت ثبت شد.');
    } catch (err: any) {
      const d = err.response?.data;
      setProfileMessage(d?.detail || d?.avatar?.[0] || JSON.stringify(d) || 'ثبت تصویر پروفایل انجام نشد.');
    } finally {
      setAvatarUploading(false);
    }
  };

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileMessage('');

    if (!profileForm.bar_number.trim()) {
      setProfileMessage('شماره پروانه وکالت الزامی است.');
      return;
    }
    if (!profileForm.areas.length) {
      setProfileMessage('حداقل یک حوزه تخصصی باید انتخاب شود.');
      return;
    }
    if (!profile?.bar_document_url && !profileForm.bar_document) {
      setProfileMessage('بارگذاری فایل پروانه وکالت الزامی است.');
      return;
    }

    const fd = new FormData();
    fd.append('bar_number', profileForm.bar_number);
    profileForm.areas.forEach((a) => fd.append('areas', a));
    fd.append('primary_area', profileForm.areas[0]);
    fd.append('headline', profileForm.headline);
    fd.append('years_experience', profileForm.years_experience || '0');
    fd.append('consultation_fee', profileForm.consultation_fee || '0');
    fd.append('office_address', profileForm.office_address || '');
    if (profileForm.bar_document) fd.append('bar_document', profileForm.bar_document);

    try {
      setProfileSaving(true);
      const { data } = await lawyerApi.updateProfile(fd);
      setProfile(data);
      await fetchMe();
      setProfileMessage('پروفایل، تخصص‌ها و پروانه با موفقیت ذخیره شد.');
    } catch (err: any) {
      const d = err.response?.data;
      setProfileMessage(translateProfileError(d?.detail || d?.bar_number?.[0] || d?.bar_document?.[0] || JSON.stringify(d)) || 'ذخیره پروفایل انجام نشد.');
    } finally {
      setProfileSaving(false);
    }
  };

  const translateProfileError = (message: any) => {
    const text = String(message || '');
    if (text.toLowerCase().includes('lawyer with this bar number already exists')) {
      return 'وکیلی با این شماره پروانه قبلاً ثبت شده است';
    }
    if (text.toLowerCase().includes('bar number already exists')) {
      return 'این شماره پروانه قبلاً ثبت شده است';
    }
    return text;
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = '/';
  };

  if (loading) {
    return (
      <DashboardShell user={user} scrolled={scrolled}>
        <section className="lawyer-dashboard-redesign">
          <div className="card lawyer-hero-skeleton" />
        </section>
      </DashboardShell>
    );
  }

  const profileCompletionItems = [
    { label: 'عکس پروفایل', done: Boolean(profile?.avatar_url || avatarPreview || user?.avatar_url) },
    { label: 'شماره پروانه', done: Boolean(profileForm.bar_number) },
    { label: 'تخصص‌ها', done: profileForm.areas.length > 0 },
    { label: 'آدرس دفتر', done: Boolean(profileForm.office_address) },
    { label: 'هزینه مشاوره', done: Boolean(profileForm.consultation_fee) },
    { label: 'عنوان حرفه‌ای', done: Boolean(profileForm.headline) },
    { label: 'سابقه کاری', done: Boolean(profileForm.years_experience) },
  ];
  const profileCompletion = Math.round((profileCompletionItems.filter((x) => x.done).length / profileCompletionItems.length) * 100);

  const completedRevenueBookings = sortedBookings.filter((b) => b.status === 'completed');
  const monthlyRevenue = completedRevenueBookings.reduce((sum, b) => sum + Number(b.amount || b.price || b.consultation_fee || profileForm.consultation_fee || 0), 0);
  const platformCommission = Math.round(monthlyRevenue * 0.09);
  const payableRevenue = Math.max(0, monthlyRevenue - platformCommission);

  const cards = [
    { label: 'کل رزروها', value: dashboard.total_bookings ?? sortedBookings.length, cls: 'badge-gold' },
    { label: 'تایید شده', value: dashboard.confirmed_bookings ?? dashboard.confirmed ?? sortedBookings.filter((b) => b.status === 'confirmed').length, cls: 'badge-success' },
    { label: 'انجام شده', value: dashboard.completed_bookings ?? dashboard.completed ?? sortedBookings.filter((b) => b.status === 'completed').length, cls: 'badge-info' },
  ];

  return (
    <DashboardShell user={user} scrolled={scrolled}>
      <section className="lawyer-dashboard-redesign animate-fade-in">
        <section className="card lawyer-hero-calendar-card">
          <header className="lawyer-dashboard-hero glass">
          <div>
            <div className="section-eyebrow">پنل وکیل</div>
            <h1>سلام جناب آقای {`${user?.first_name || ''} ${user?.last_name || ''}`.trim() || 'وکیل عزیز'} 👋</h1>
            <p className="muted">پروفایل، تخصص‌ها، پروانه و برنامه کاری روزانه را از همین نمای کلی مدیریت کن.</p>
          </div>
          <ProfileSummary user={user} profile={profile} avatarPreview={avatarPreview} onAvatarChange={handleAvatarChange} onAvatarSave={saveAvatarProfile} avatarUploading={avatarUploading} avatarReadyToSave={avatarReadyToSave} />
        </header>

          <section className="lawyer-calendar-card">
            <div className="lawyer-section-title">
              <div>
                <div className="section-eyebrow">مدیریت رزروها و ساعت کاری</div>
                <h2>تقویم ساده رزروها</h2>
              </div>
              <span className="badge badge-success lawyer-selected-day-badge">{selectedBookings.length.toLocaleString('fa-IR')} رزرو در روز انتخابی</span>
            </div>

            <div className="simple-calendar-days">
              {calendarDays.map((day) => {
                const key = dateKey(startOfDay(day));
                const count = bookingsByDate.get(key)?.length || 0;
                const active = sameDay(day, selectedDate);
                const isClosed = closedDayKeys.includes(key);
                return (
                  <button key={key} className={`simple-calendar-day ${active ? 'active' : ''} ${isClosed ? 'closed' : ''}`} onClick={() => openDaySheet(day)}>
                    {count > 0 && <span className="simple-calendar-count-badge">{count.toLocaleString('fa-IR')}</span>}
                    <span>{day.toLocaleDateString('fa-IR', { weekday: 'short' })}</span>
                    <strong>{day.toLocaleDateString('fa-IR', { day: '2-digit' })}</strong>
                    <small>{isClosed ? 'تعطیل' : count ? `${count.toLocaleString('fa-IR')} رزرو` : 'تنظیم ساعت'}</small>
                  </button>
                );
              })}
            </div>

            <div className="simple-calendar-bookings">
              {selectedBookings.length ? selectedBookings.map((b) => <BookingRow key={b.id} b={b} onUpdate={updateStatus} compact />) : <Empty text="برای این روز رزروی ثبت نشده است." />}
            </div>
          </section>
        </section>


        <section className="lawyer-stats-grid lawyer-stats-grid-three">
          {cards.map((c) => (
            <div className="card lawyer-stat-card" key={c.label}>
              <span className={`badge ${c.cls}`}>{c.label}</span>
              <div className="gold lawyer-stat-value">{Number(c.value).toLocaleString('fa-IR')}</div>
            </div>
          ))}
        </section>

        <section className="lawyer-feature-grid">
          <div className="card lawyer-profile-completion-card">
            <div className="section-eyebrow">تکمیل پروفایل</div>
            <h2>پروفایل شما {profileCompletion.toLocaleString('fa-IR')}٪ کامل است</h2>
            <div className="profile-progress-bar"><span style={{ width: `${profileCompletion}%` }} /></div>
            <p className="muted">برای نمایش بهتر در صفحه اصلی، عکس، تخصص، آدرس دفتر و هزینه مشاوره را کامل کن.</p>
            <div className="profile-completion-checks">{profileCompletionItems.map((item) => <span key={item.label} className={item.done ? 'done' : ''}>{item.done ? '✓' : '○'} {item.label}</span>)}</div>
            <button type="button" className="btn btn-gold" onClick={() => { setProfileMiniOpen(true); document.getElementById('lawyer-profile-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>تکمیل پروفایل</button>
          </div>
          <div className="card lawyer-revenue-summary-card">
            <div className="section-eyebrow">درآمد و تسویه</div>
            <h2>سیستم درآمد حرفه‌ای</h2>
            <div className="lawyer-revenue-mini-grid">
              <div><span>درآمد این ماه</span><strong>{monthlyRevenue.toLocaleString('fa-IR')} تومان</strong></div>
              <div><span>رزروهای انجام‌شده</span><strong>{completedRevenueBookings.length.toLocaleString('fa-IR')}</strong></div>
              <div><span>کمیسیون پلتفرم</span><strong>{platformCommission.toLocaleString('fa-IR')} تومان</strong></div>
              <div><span>قابل تسویه</span><strong>{payableRevenue.toLocaleString('fa-IR')} تومان</strong></div>
            </div>
            <div className="settlement-status-line">وضعیت تسویه: <strong>آماده درخواست</strong></div>
            <button type="button" className="btn btn-outline" onClick={() => alert('درخواست تسویه ثبت شد و برای ادمین ارسال می‌شود.')}>درخواست تسویه</button>
          </div>
        </section>

        <button type="button" className="btn btn-gold lawyer-revenue-open-btn" onClick={() => setRevenueSheetOpen(true)}>
          داشبورد درآمد و عملکرد
        </button>

        <section className="lawyer-overview-grid">
          <section id="lawyer-profile-card" className={`card lawyer-profile-card ${profileAttention ? 'lawyer-profile-card-attention' : ''}`}>
            <div className="lawyer-section-title">
              <div>
                <div className="section-eyebrow">پروفایل حرفه‌ای</div>
                <h2>پروانه و تخصص‌ها</h2>
              </div>
              <span className={`badge ${profile?.verification_status === 'verified' ? 'badge-success' : 'badge-warning'}`}>
                {profile?.verification_status === 'verified' ? 'تایید شده' : 'در انتظار تایید'}
              </span>
            </div>

            {profileAttention && (
              <div className="lawyer-profile-required-alert">لطفا اول مشخصات خود را تکمیل کنید</div>
            )}

            {profile?.verification_status === 'verified' && (
              <button type="button" className="lawyer-profile-mini-summary" onClick={() => setProfileMiniOpen((v) => !v)}>
                <span>
                  <strong>{profileForm.bar_number || 'پروانه ثبت شده'}</strong>
                  <small>{profileForm.areas.length ? profileForm.areas.map((a) => AREAS[a] || a).slice(0, 2).join('، ') : 'تخصص‌ها ثبت شده‌اند'}</small>
                </span>
                <em>{profileMiniOpen ? 'بستن ویرایش' : 'ویرایش پروفایل'}</em>
              </button>
            )}

            {profile?.verification_status !== 'verified' || profileMiniOpen ? (
            <form className="lawyer-profile-form lawyer-profile-form-animated" onSubmit={saveProfile}>
              <div className="lawyer-profile-form-row lawyer-profile-form-row-two">
                <label>
                  شماره پروانه وکالت
                  <input className="input" value={profileForm.bar_number} onChange={(e) => setProfileForm((f) => ({ ...f, bar_number: e.target.value }))} placeholder="مثلاً ۱۲۳۴۵۶" />
                </label>
                <label>
                  عنوان کوتاه پروفایل
                  <input className="input" value={profileForm.headline} onChange={(e) => setProfileForm((f) => ({ ...f, headline: e.target.value }))} placeholder="مثلاً وکیل پایه یک در دعاوی خانواده و کیفری" />
                </label>
              </div>

              <div className="lawyer-specialty-select">
                <span className="lawyer-field-label">حوزه‌های تخصصی</span>
                <button type="button" className={`lawyer-specialty-trigger ${areasOpen ? 'active' : ''}`} onClick={() => setAreasOpen((v) => !v)}>
                  <span>
                    {profileForm.areas.length
                      ? `${profileForm.areas.slice(0, 2).map((a) => AREAS[a] || a).join('، ')}${profileForm.areas.length > 2 ? ` +${profileForm.areas.length - 2} بیشتر` : ''}`
                      : 'انتخاب حوزه‌های تخصصی'}
                  </span>
                  <b>{areasOpen ? '−' : '+'}</b>
                </button>
                {areasOpen && (
                  <div className="lawyer-specialty-options animate-fade-in">
                    {Object.entries(AREAS).map(([key, label]) => (
                      <button type="button" className={`lawyer-specialty-option ${profileForm.areas.includes(key) ? 'selected' : ''}`} key={key} onClick={() => toggleArea(key)}>
                        <span>{label}</span>
                        <small>{profileForm.areas.includes(key) ? 'انتخاب شده' : 'انتخاب'}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="lawyer-profile-form-row lawyer-profile-form-row-two">
                <label>
                  سابقه کاری
                  <input className="input" type="number" min="0" value={profileForm.years_experience} onChange={(e) => setProfileForm((f) => ({ ...f, years_experience: e.target.value }))} placeholder="سال" />
                </label>
                <label>
                  هزینه مشاوره
                  <input className="input" type="number" min="0" value={profileForm.consultation_fee} onChange={(e) => setProfileForm((f) => ({ ...f, consultation_fee: e.target.value }))} placeholder="تومان" />
                </label>
              </div>

              <div className="lawyer-profile-form-row">
                <label>
                  آدرس دفتر
                  <textarea
                    className="input lawyer-address-input"
                    value={profileForm.office_address}
                    onChange={(e) => setProfileForm((f) => ({ ...f, office_address: e.target.value }))}
                    placeholder="آدرس کامل دفتر برای نمایش در پروفایل عمومی وکیل"
                    rows={3}
                  />
                </label>
              </div>

              <label>
                فایل پروانه وکالت
                <input className="input" type="file" accept="image/*,.pdf" onChange={(e) => setProfileForm((f) => ({ ...f, bar_document: e.target.files?.[0] || null }))} />
              </label>

              {profile?.bar_document_url && <a className="lawyer-license-link" href={profile.bar_document_url} target="_blank" rel="noreferrer">مشاهده پروانه وکالت بارگذاری‌شده</a>}
              {profileMessage && <div className="lawyer-profile-message">{profileMessage}</div>}
              <button className="btn btn-gold" disabled={profileSaving}>{profileSaving ? 'در حال ذخیره...' : 'ذخیره پروفایل و تخصص‌ها'}</button>
            </form>
            ) : null}
          </section>

        </section>

        <section className="lawyer-bookings-section" id="lawyer-bookings">
          <div className="lawyer-section-title">
            <div>
              <div className="section-eyebrow">رزروها در نمای کلی</div>
              <h2>آخرین رزروها</h2>
            </div>
          </div>
          <div className="lawyer-booking-list">
            {sortedBookings.length ? sortedBookings.map((b) => <BookingRow key={b.id} b={b} onUpdate={updateStatus} />) : <Empty text="هنوز رزروی برای شما ثبت نشده است." />}
          </div>
        </section>

        <footer className="lawyer-logout-footer">
          <button className="btn btn-danger lawyer-logout-btn" onClick={handleLogout}>خروج از حساب</button>
        </footer>
      </section>

      {sheetOpen && (
        <div className="lawyer-day-sheet-backdrop" onClick={() => setSheetOpen(false)}>
          <section className="lawyer-day-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="lawyer-sheet-head">
              <div>
                <div className="section-eyebrow">تنظیم روز کاری</div>
                <h3>{selectedDate.toLocaleDateString('fa-IR', { dateStyle: 'full' })}</h3>
              </div>
              <button className="lawyer-sheet-close-x" type="button" aria-label="بستن شیت" onClick={() => setSheetOpen(false)}>×</button>
            </div>

            <label className="lawyer-day-toggle">
              <input type="checkbox" checked={dayClosed} onChange={(e) => setDayClosed(e.target.checked)} />
              این روز تعطیل/بسته است
            </label>

            {!dayClosed && (
              <div className="lawyer-hours-list">
                {daySlots.map((slot, idx) => (
                  <div className="lawyer-hour-row" key={idx}>
                    <label className="lawyer-time-chip">
                      <span>از ساعت</span>
                      <input type="time" value={slot.start_time} onChange={(e) => setDaySlots((s) => s.map((x, i) => i === idx ? { ...x, start_time: e.target.value } : x))} />
                    </label>
                    <label className="lawyer-time-chip">
                      <span>تا ساعت</span>
                      <input type="time" value={slot.end_time} onChange={(e) => setDaySlots((s) => s.map((x, i) => i === idx ? { ...x, end_time: e.target.value } : x))} />
                    </label>
                    <div className="lawyer-hour-actions">
                      <button className="lawyer-hour-action lawyer-hour-remove" type="button" onClick={() => setDaySlots((s) => s.filter((_, i) => i !== idx))}>حذف</button>
                      {idx === daySlots.length - 1 && (
                        <button className="lawyer-hour-action lawyer-hour-add" type="button" onClick={() => setDaySlots((s) => [...s, { start_time: '09:00', end_time: '17:00' }])}>افزودن بازه ساعت</button>
                      )}
                    </div>
                  </div>
                ))}
                
              </div>
            )}

            <div className="lawyer-sheet-bookings">
              <strong>رزروهای این روز</strong>
              {selectedBookings.length ? selectedBookings.map((b) => <BookingRow key={b.id} b={b} onUpdate={updateStatus} compact />) : <p className="muted">رزروی برای این روز ثبت نشده است.</p>}
            </div>

            {scheduleAutoSaving && <div className="lawyer-autosave-note">ذخیره خودکار فعال است...</div>}
            {scheduleMessage && <div className="lawyer-profile-message">{scheduleMessage}</div>}
            <button className="btn btn-gold lawyer-sheet-save-btn" onClick={saveDaySchedule}>ثبت وضعیت این روز</button>
          </section>
        </div>
      )}

      {revenueSheetOpen && (
        <div className="lawyer-revenue-backdrop" onClick={() => setRevenueSheetOpen(false)}>
          <section className="lawyer-revenue-sheet glass" onClick={(e) => e.stopPropagation()}>
            <div className="lawyer-sheet-head">
              <div>
                <div className="section-eyebrow">داشبورد درآمد و عملکرد</div>
                <h3>گزارش سریع عملکرد</h3>
              </div>
              <button className="lawyer-sheet-close-x" type="button" onClick={() => setRevenueSheetOpen(false)}>×</button>
            </div>
            <div className="lawyer-revenue-grid">
              <div><span>رزرو این ماه</span><strong>{Number(dashboard.monthly_bookings || 0).toLocaleString('fa-IR')}</strong></div>
              <div><span>درآمد تخمینی</span><strong>{Number(dashboard.estimated_revenue || 0).toLocaleString('fa-IR')} تومان</strong></div>
              <div><span>میانگین امتیاز</span><strong>{Number(dashboard.average_rating || 0).toFixed(1)}</strong></div>
              <div><span>رزروهای لغو شده</span><strong>{Number(dashboard.cancelled_bookings || 0).toLocaleString('fa-IR')}</strong></div>
            </div>
            <div className="lawyer-hot-hours">
              <strong>ساعت‌های پربازده</strong>
              {dashboard.hot_hours?.length ? dashboard.hot_hours.map((h: any) => (
                <span key={h.hour}>{h.hour} · {Number(h.count || 0).toLocaleString('fa-IR')} رزرو</span>
              )) : <span>هنوز داده کافی ثبت نشده است.</span>}
            </div>
          </section>
        </div>
      )}

    </DashboardShell>
  );
}

function DashboardShell({ children, user, scrolled }: any) {
  const [open, setOpen] = useState(false);
  const links = [
    { href: '/lawyers', label: 'وکلا' },
    { href: '/dashboard/lawyer', label: 'پنل من' },
  ];

  return (
    <main className="dashboard lawyer-dashboard-shell has-landing-header">
      <nav className={`navbar lawyer-landing-header ${scrolled ? 'is-scrolled' : ''}`}>
        <Link href="/" className="logo"><span className="logo-mark">ل</span> لکسارا</Link>
        <div className="nav-links">
          {links.map((l) => <Link key={l.href} href={l.href} className="nav-link">{l.href === '/lawyers' && <span className="lawyer-people-stack-icon" aria-hidden="true">👥</span>}{l.label}</Link>)}
          <Link href="/register" className="btn btn-gold btn-sm">شروع کنید</Link>
        </div>
        <button className="mobile-menu-btn btn btn-outline btn-sm" onClick={() => setOpen(!open)}>{open ? 'بستن' : 'منو'}</button>
      </nav>
      {open && (
        <div className="mobile-panel glass animate-fade-in lawyer-mobile-panel">
          {links.map((l) => <Link key={l.href} href={l.href} className="nav-link" onClick={() => setOpen(false)}>{l.href === '/lawyers' && <span className="lawyer-people-stack-icon" aria-hidden="true">👥</span>}{l.label}</Link>)}
          <Link href="/register" className="btn btn-gold" onClick={() => setOpen(false)}>ثبت‌نام</Link>
        </div>
      )}
      <aside className="sidebar lawyer-sidebar">
        <Link href="/" className="logo"><span className="logo-mark">ل</span> لکسارا</Link>
        <div className="card-soft" style={{ padding: 14 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div className="avatar" style={{ width: 46, height: 46, borderRadius: 14 }}>{user?.first_name?.[0] || 'و'}</div>
            <div><strong>{user?.full_name || 'وکیل'}</strong><div className="muted" style={{ marginTop: 4, fontSize: 12 }}>حساب وکیل</div></div>
          </div>
        </div>
        <nav>
          <a href="#overview" className="side-button active"><span>⬡</span>نمای کلی</a>
          <a href="#lawyer-bookings" className="side-button"><span>📅</span>رزروها</a>
        </nav>
      </aside>
      <section className="main-content" id="overview">{children}</section>
    </main>
  );
}

function ProfileSummary({ user, profile, avatarPreview, onAvatarChange, onAvatarSave, avatarUploading, avatarReadyToSave }: any) {
  const avatar = avatarPreview || user?.avatar || user?.avatar_url || profile?.avatar || profile?.avatar_url;
  return (
    <div className="lawyer-identity-card">
      <label className="lawyer-avatar-plus-wrap" title="تغییر عکس پروفایل">
        {avatar ? <img className="lawyer-avatar-img" src={avatar} alt="پروفایل وکیل" /> : <div className="avatar lawyer-avatar">{user?.first_name?.[0] || 'و'}</div>}
        {onAvatarChange && (
          <>
            <span className="lawyer-avatar-plus">+</span>
            <input type="file" accept="image/*" hidden onChange={(e) => { const file = e.target.files?.[0]; if (file) onAvatarChange(file); }} />
          </>
        )}
      </label>
      <div className="lawyer-identity-text"><strong>{`${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.full_name || 'وکیل لکسارا'}</strong><span>حساب وکیل</span></div>
      {onAvatarSave && (
        <button
          type="button"
          className="btn btn-success btn-sm lawyer-avatar-save-btn"
          onClick={onAvatarSave}
          disabled={avatarUploading || !avatarReadyToSave}
        >
          {avatarUploading ? 'در حال ثبت عکس...' : 'ثبت عکس پروفایل'}
        </button>
      )}
    </div>
  );
}

function BookingRow({ b, onUpdate, compact = false }: { b: any; onUpdate: (id: string, status: string) => void; compact?: boolean }) {
  const st = STATUS[b.status] || { label: b.status || 'نامشخص', cls: 'badge-muted' };
  const scheduled = getBookingTime(b);
  return (
    <article className={`card lawyer-booking-row ${compact ? 'compact' : ''}`}>
      <div className="lawyer-booking-main">
        <span className={`badge ${st.cls}`}>{st.label}</span>
        <h3>{b.title || b.subject || 'مشاوره حقوقی'}</h3>
        <p className="muted">{b.customer_name || b.customer?.full_name || 'موکل'} — {scheduled ? formatDate(scheduled) : 'زمان نامشخص'}</p>
        {b.description && <p className="muted lawyer-booking-desc">{b.description}</p>}
      </div>
      <div className="lawyer-booking-actions">
        {b.status === 'pending' && <>
          <button className="btn btn-gold btn-sm" onClick={() => onUpdate(b.id, 'confirmed')}>تایید</button>
          <button className="btn btn-outline btn-sm" onClick={() => onUpdate(b.id, 'rejected')}>رد</button>
        </>}
        {b.status === 'confirmed' && <button className="btn btn-outline btn-sm" onClick={() => onUpdate(b.id, 'completed')}>انجام شد</button>}
      </div>
    </article>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="card lawyer-empty-card"><p className="muted">{text}</p></div>;
}
