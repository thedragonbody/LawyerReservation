'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { bookingApi, lawyerApi } from '@/lib/api';

const todayKey = () => new Date().toISOString().slice(0, 10);

const PRACTICE_AREA_FA: Record<string, string> = {
  corporate: 'حقوق شرکت‌ها',
  criminal: 'کیفری و جزایی',
  criminal_defense: 'دفاع کیفری',
  employment_law: 'حقوق کار و استخدام',
  corporate_law: 'حقوق شرکت‌ها',
  criminaldefense: 'دفاع کیفری',
  employmentlaw: 'حقوق کار و استخدام',
  corporatelaw: 'حقوق شرکت‌ها',
  family: 'خانواده و طلاق',
  family_law: 'حقوق خانواده',
  familylaw: 'حقوق خانواده',
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
  internationallaw: 'حقوق بین‌الملل',
  international_law: 'حقوق بین‌الملل',
  taxlaw: 'حقوق مالیاتی',
  tax_law: 'حقوق مالیاتی',
  healthcarelaw: 'حقوق پزشکی و سلامت',
  healthcare_law: 'حقوق پزشکی و سلامت',
  environmentallaw: 'حقوق محیط زیست',
  environmental_law: 'حقوق محیط زیست',
  international: 'حقوق بین‌الملل',
  contracts: 'قراردادها',
  commercial: 'تجاری و بازرگانی',
  labor: 'کار و تأمین اجتماعی',
  insurance: 'بیمه',
  banking: 'بانکی و مالی',
  startups: 'استارتاپ‌ها',
  cyber: 'جرایم رایانه‌ای',
  administrative: 'دیوان عدالت اداری',
  property: 'ملکی',
  inheritance: 'ارث و وصیت',
  divorce: 'طلاق',
  child_custody: 'حضانت فرزند',
  medical: 'پزشکی',
  arbitration: 'داوری',
};

function translatePracticeArea(value: any) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const key = raw.toLowerCase().replace(/[\s-]+/g, '_');
  const compactKey = raw.toLowerCase().replace(/[\s_-]+/g, '');
  return PRACTICE_AREA_FA[key] || PRACTICE_AREA_FA[compactKey] || PRACTICE_AREA_FA[raw] || raw;
}


function starsFor(value: number) {
  const rounded = Math.round(Number(value || 0));
  return '★'.repeat(rounded) + '☆'.repeat(5 - rounded);
}

export default function LawyerDetailPage({ params }: { params: { id: string } }) {
  const [navHidden, setNavHidden] = useState(false);
  const [lawyer, setLawyer] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [comment, setComment] = useState('');
  const [message, setMessage] = useState('');
  const [ratingSaving, setRatingSaving] = useState(false);

  const [bookingDate, setBookingDate] = useState(todayKey());
  const [slots, setSlots] = useState<any[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [bookingMessage, setBookingMessage] = useState('');
  const [bookingSaving, setBookingSaving] = useState('');
  const [timeSheetOpen, setTimeSheetOpen] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<any>(null);
  const [bookingSessionType, setBookingSessionType] = useState<'in_person' | 'phone'>('in_person');
  const [paymentSheetOpen, setPaymentSheetOpen] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState<any>(null);
  const [bookingInvoice, setBookingInvoice] = useState<any>(null);
  const [caseTitle, setCaseTitle] = useState('');
  const [caseDescription, setCaseDescription] = useState('');
  const [bookingDayStatuses, setBookingDayStatuses] = useState<Record<string, any>>({});

  useEffect(() => {
    let lastY = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      setNavHidden(y > lastY && y > 80);
      lastY = y;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const refreshLawyer = async () => {
    const { data } = await lawyerApi.detail(params.id);
    setLawyer(data);
    return data;
  };

  useEffect(() => {
    refreshLawyer().finally(() => setLoading(false));
  }, [params.id]);

  useEffect(() => {
    let alive = true;
    if (!bookingDate) return;

    setSlotsLoading(true);
    setBookingMessage('');

    lawyerApi.slots(params.id, bookingDate)
      .then((r) => {
        if (!alive) return;
        setSlots(r.data?.slots || []);
        if (r.data?.is_closed) setBookingMessage('متاسفانه این روز تعطیل میباشد');
        else if (r.data?.message) setBookingMessage(r.data.message === 'No availability on this day.' ? 'برای این روز ساعت فعالی ثبت نشده است.' : r.data.message);
      })
      .catch((err) => {
        if (!alive) return;
        const d = err.response?.data;
        setSlots([]);
        setBookingMessage(d?.detail || 'دریافت ساعت‌های قابل رزرو انجام نشد.');
      })
      .finally(() => {
        if (alive) setSlotsLoading(false);
      });

    return () => { alive = false; };
  }, [params.id, bookingDate]);

  useEffect(() => {
    if (!lawyer) return;
    setRating(Math.round(Number(lawyer.my_review?.rating || 0)));
    setComment(lawyer.my_review?.comment || '');
  }, [lawyer?.id]);

  const averageRating = Number(lawyer?.average_rating || 0);
  const initials = (lawyer?.full_name || 'و').slice(0, 1);

  const practiceAreaValue = useMemo(() => {
    const areas = lawyer?.practice_areas || [];
    return areas?.[0]?.area || lawyer?.primary_area || '';
  }, [lawyer]);

  const lawyerSpecialties = useMemo(() => {
    const areas = Array.isArray(lawyer?.practice_areas) ? lawyer.practice_areas : [];
    const mapped = areas
      .map((a: any) => translatePracticeArea(a?.area_display || a?.label || a?.name || a?.area))
      .filter(Boolean);

    const primary = lawyer?.primary_area ? [translatePracticeArea(lawyer.primary_area)] : [];
    return Array.from(new Set([...primary, ...mapped]));
  }, [lawyer]);
  const bookingDays = useMemo(() => {
    const start = new Date();
    start.setDate(start.getDate() + 3);
    return Array.from({ length: 14 }, (_, idx) => {
      const d = new Date(start);
      d.setDate(start.getDate() + idx);
      return d;
    });
  }, []);

  const formatBookingDate = (value: string) => {
    const d = new Date(`${value}T00:00:00`);
    if (Number.isNaN(d.getTime())) return 'انتخاب تاریخ';
    return d.toLocaleDateString('fa-IR', { weekday: 'long', day: '2-digit', month: 'long' });
  };

  const refreshBookingDayStatuses = async () => {
    const entries = await Promise.all(
      bookingDays.map(async (day) => {
        const key = day.toISOString().slice(0, 10);
        try {
          const { data } = await lawyerApi.slots(params.id, key);
          return [key, {
            is_closed: Boolean(data?.is_closed),
            has_slots: Boolean((data?.slots || []).length),
            message: data?.message || '',
          }];
        } catch {
          return [key, { is_closed: false, has_slots: false, message: '' }];
        }
      })
    );
    setBookingDayStatuses(Object.fromEntries(entries));
  };

  useEffect(() => {
    refreshBookingDayStatuses();
  }, [params.id, bookingDays]);

  const translateReviewError = (raw: any) => {
    const text = String(raw || '');
    const lower = text.toLowerCase();
    if (lower.includes('completed consultation')) return 'فقط بعد از انجام مشاوره می‌توانید امتیاز ثبت کنید.';
    if (lower.includes('only customers')) return 'فقط موکل می‌تواند امتیاز ثبت کند.';
    if (lower.includes('lawyer is not verified') || lower.includes('not verified')) return 'این وکیل هنوز توسط ادمین تایید نشده است.';
    if (lower.includes('not found')) return 'وکیل پیدا نشد.';
    if (lower.includes('credentials')) return 'برای امتیازدهی باید وارد حساب کاربری شوید.';
    return text;
  };

  const submitStarRating = async (score: number) => {
    setRating(score);
    setMessage('');
    setRatingSaving(true);

    try {
      await lawyerApi.addReview(params.id, { rating: score, comment: comment || '', is_anonymous: false });
      setMessage('امتیاز شما ثبت شد.');
      await refreshLawyer();
    } catch (err: any) {
      const d = err.response?.data;
      const raw = d?.detail || d?.rating?.[0] || JSON.stringify(d) || '';
      setMessage(translateReviewError(raw) || 'ثبت امتیاز انجام نشد.');
    } finally {
      setRatingSaving(false);
    }
  };

  const saveCommentOnly = async () => {
    if (!rating) {
      setMessage('اول با کلیک روی ستاره‌ها امتیاز را انتخاب کنید.');
      return;
    }
    setRatingSaving(true);
    try {
      await lawyerApi.addReview(params.id, { rating, comment, is_anonymous: false });
      setMessage('نظر شما ذخیره شد.');
      await refreshLawyer();
    } catch (err: any) {
      const d = err.response?.data;
      setMessage(translateReviewError(d?.detail || d?.comment?.[0] || JSON.stringify(d)) || 'ذخیره نظر انجام نشد.');
    } finally {
      setRatingSaving(false);
    }
  };

  const openDaySheet = (day: Date) => {
    const key = day.toISOString().slice(0, 10);
    const status = bookingDayStatuses[key] || {};
    setBookingDate(key);
    setSelectedSlot(null);
    setConfirmedBooking(null);
    setBookingInvoice(null);
    setCaseTitle('');
    setCaseDescription('');

    if (status.is_closed) {
      setBookingMessage('متاسفانه این روز تعطیل میباشد');
      return;
    }

    setBookingMessage('');
    setTimeSheetOpen(true);
  };

  const startPaymentForSlot = (slot: any, type: 'in_person' | 'phone') => {
    if (!slot.available) return;
    setSelectedSlot(slot);
    setBookingSessionType(type);
    setPaymentSheetOpen(true);
    setBookingMessage('');
  };

  const createBooking = async () => {
    if (!selectedSlot?.available) return;

    const cleanTitle = caseTitle.trim();
    const cleanDescription = caseDescription.trim();

    if (!cleanTitle) {
      setBookingMessage('عنوان پرونده را وارد کنید.');
      return;
    }

    if (!cleanDescription || cleanDescription.length < 10) {
      setBookingMessage('شرح مشکل را حداقل در ۱۰ کاراکتر وارد کنید.');
      return;
    }

    const scheduledAt = selectedSlot.datetime || `${bookingDate}T${selectedSlot.time || '09:00'}:00`;
    setBookingSaving(scheduledAt);
    setBookingMessage('');

    try {
      const sessionText = bookingSessionType === 'phone' ? 'تلفنی' : 'حضوری';
      const { data } = await bookingApi.create({
        lawyer: params.id,
        booking_type: 'consultation',
        scheduled_at: scheduledAt,
        duration_minutes: selectedSlot.duration_minutes || 60,
        subject: cleanTitle,
        description: `نوع رزرو: ${sessionText}\n\nشرح مشکل:\n${cleanDescription}`,
        practice_area: practiceAreaValue,
      });

      setConfirmedBooking(data);
      setBookingInvoice(data?.invoice || null);
      setBookingMessage('پرداخت انجام شد و رزرو شما نهایی شد. می‌توانید مدارک مورد نیاز رزرو مشاوره خود را در حساب کاربری بارگذاری نمایید.');
      setPaymentSheetOpen(false);
      setTimeSheetOpen(false);
      const r = await lawyerApi.slots(params.id, bookingDate);
      setSlots(r.data?.slots || []);
      await refreshBookingDayStatuses();
      await refreshLawyer();
    } catch (err: any) {
      const d = err.response?.data;
      let msg = d?.detail || d?.subject?.[0] || d?.description?.[0] || d?.scheduled_at?.[0] || d?.lawyer?.[0] || JSON.stringify(d) || '';
      if (String(msg).toLowerCase().includes('credentials')) msg = 'برای رزرو باید وارد حساب کاربری شوید.';
      if (String(msg).toLowerCase().includes('only customers')) msg = 'رزرو فقط با حساب موکل امکان‌پذیر است.';
      if (String(msg).toLowerCase().includes('not verified')) msg = 'این وکیل هنوز توسط ادمین تایید نشده است.';
      setBookingMessage(msg || 'ثبت رزرو انجام نشد.');
    } finally {
      setBookingSaving('');
    }
  };

  if (loading) {
    return (
      <main className="page-shell" style={{ paddingTop: 110 }}>
        <SimpleNav hidden={navHidden} />
        <section className="container lawyer-detail-enter-wrap"><div className="card" style={{ height: 320 }} /></section>
      </main>
    );
  }

  if (!lawyer) {
    return (
      <main className="page-shell" style={{ paddingTop: 110 }}>
        <SimpleNav hidden={navHidden} />
        <section className="container"><div className="card" style={{ padding: 30 }}>وکیل پیدا نشد.</div></section>
      </main>
    );
  }

  return (
    <main className="page-shell lawyer-detail-page" style={{ paddingTop: 110 }}>
      <SimpleNav hidden={navHidden} />

      <section className="container">
        <header className="card lawyer-detail-hero compact lawyer-profile-enter lawyer-profile-enter-hero">
          <div className="lawyer-detail-identity">
            <div className="avatar lawyer-detail-avatar">
              {lawyer.avatar_url ? <img src={lawyer.avatar_url} alt={lawyer.full_name || 'وکیل'} /> : initials}
            </div>

            <div className="lawyer-detail-hero-text">
              <h1>{lawyer.full_name || 'وکیل لکسارا'}</h1>
              <p className="muted">{lawyer.headline || 'وکیل پایه یک دادگستری'}</p>
{lawyerSpecialties.length > 0 && (
                <div className="lawyer-detail-specialties">
                  {lawyerSpecialties.map((item: string) => (
                    <span key={item} className="lawyer-specialty-chip">{item}</span>
                  ))}

                </div>
              )}
            </div>
          </div>

          <div className="lawyer-detail-score">
            <strong aria-label={`میانگین امتیاز ${averageRating}`}>{starsFor(averageRating)}</strong>
            <small className="muted">میانگین: {averageRating.toFixed(1)}</small>
          </div>

          <div className="lawyer-detail-info merged">
            <h2>اطلاعات حرفه‌ای</h2>
            <div className="lawyer-detail-info-grid">
              <Detail label="شماره پروانه" value={lawyer.bar_number || 'ثبت نشده'} />
              <Detail label="سابقه" value={`${Number(lawyer.years_experience || 0).toLocaleString('fa-IR')} سال`} />
              <Detail label="هزینه مشاوره" value={`${Number(lawyer.consultation_fee || 0).toLocaleString('fa-IR')} تومان`} />
            </div>
            {lawyer.office_address && (
              <div className="lawyer-detail-address">
                <span>آدرس دفتر</span>
                <strong>{lawyer.office_address}</strong>
              </div>
            )}
            {lawyer.bio && <p className="muted lawyer-detail-bio">{lawyer.bio}</p>}
          </div>

          <a href="#lawyer-booking-card" className="btn btn-gold lawyer-detail-booking-cta">رزرو وقت مشاوره</a>
        </header>

        <section className="lawyer-detail-grid clean lawyer-profile-enter lawyer-profile-enter-grid">
          <section id="lawyer-booking-card" className="card lawyer-booking-card redesigned-booking scroll-days-booking lawyer-profile-enter-card">
            <h2>رزرو وقت با وکیل</h2>
            <div className="lawyer-booking-day-rail" aria-label="انتخاب روز رزرو">
              {bookingDays.map((day) => {
                const key = day.toISOString().slice(0, 10);
                const active = key === bookingDate;
                const status = bookingDayStatuses[key] || {};
                const isClosed = Boolean(status.is_closed);
                const hasSlots = Boolean(status.has_slots);
                return (
                  <button
                    key={key}
                    type="button"
                    className={`lawyer-rail-day ${active ? 'active' : ''} ${isClosed ? 'closed' : ''} ${!isClosed && !hasSlots ? 'empty' : ''}`}
                    onClick={() => openDaySheet(day)}
                  >
                    <span>{day.toLocaleDateString('fa-IR', { weekday: 'short' })}</span>
                    <strong>{day.toLocaleDateString('fa-IR', { day: '2-digit' })}</strong>
                    <small>{isClosed ? 'تعطیل' : hasSlots ? 'دارای وقت' : 'بدون ساعت'}</small>
                  </button>
                );
              })}
            </div>

            {bookingMessage && <div className="lawyer-profile-message">{bookingMessage}</div>}

            {confirmedBooking && (
              <div className="lawyer-booking-confirmed">
                <strong>رزرو فعال شد</strong>
                <span>{formatBookingDate(bookingDate)} - {bookingInvoice?.time || selectedSlot?.time}</span>
                <small>کد رزرو: {bookingInvoice?.booking_code || String(confirmedBooking.id || '').slice(0, 8).toUpperCase()}</small>
              </div>
            )}
          </section>

          <section className="card lawyer-review-form lawyer-profile-enter-card">
            <h2>امتیازدهی به وکیل</h2>
            <div className="lawyer-click-stars" onMouseLeave={() => setHoverRating(0)} aria-label="امتیازدهی ستاره‌ای">
              {[1, 2, 3, 4, 5].map((score) => {
                const active = score <= (hoverRating || rating);
                return (
                  <button key={score} type="button" className={active ? 'active' : ''} onMouseEnter={() => setHoverRating(score)} onClick={() => submitStarRating(score)} disabled={ratingSaving} aria-label={`${score} ستاره`}>
                    ★
                  </button>
                );
              })}
            </div>

            <label>
              نظر شما
              <textarea className="input" value={comment} onChange={(e) => setComment(e.target.value)} rows={3} placeholder="تجربه خود را بنویس..." />
            </label>

            <button type="button" className="btn btn-gold lawyer-review-submit" onClick={saveCommentOnly} disabled={ratingSaving}>
              ثبت نظر
            </button>

            {message && <div className="lawyer-profile-message">{message}</div>}
            {ratingSaving && <div className="lawyer-autosave-note">در حال ذخیره امتیاز...</div>}
          </section>
        </section>

        <section className="card lawyer-reviews-list lawyer-profile-enter lawyer-profile-enter-reviews">
          <h2>نظرات کاربران</h2>
          {lawyer.reviews?.length ? (
            <div className="lawyer-review-items">
              {lawyer.reviews.map((r: any) => (
                <div className="lawyer-review-item" key={r.id}>
                  <strong>{starsFor(Number(r.rating || 0))}</strong>
                  <p>{r.comment || 'بدون توضیح'}</p>
                  <small className="muted">{r.customer_name || 'کاربر'}</small>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">هنوز نظری برای این وکیل ثبت نشده است.</p>
          )}
        </section>
      </section>
      {timeSheetOpen && (
        <div className="lawyer-time-sheet-backdrop" onClick={() => setTimeSheetOpen(false)}>
          <section className="lawyer-time-sheet" onClick={(e) => e.stopPropagation()}>
            <button className="lawyer-sheet-close-x" type="button" aria-label="بستن" onClick={() => setTimeSheetOpen(false)}>×</button>
            <h3>{formatBookingDate(bookingDate)}</h3>
            <p className="muted">یکی از ساعت‌های قابل رزرو را انتخاب کن.</p>

            <div className="lawyer-time-sheet-slots">
              {slotsLoading ? (
                <p className="muted">در حال دریافت ساعت‌ها...</p>
              ) : slots.length ? (
                slots.map((slot: any) => {
                  const slotKey = slot.datetime || `${bookingDate}T${slot.time}:00`;
                  const active = selectedSlot && (selectedSlot.datetime || selectedSlot.time) === (slot.datetime || slot.time);
                  return (
                    <button
                      key={slotKey}
                      type="button"
                      className={`lawyer-sheet-slot ${slot.available ? 'available' : 'booked'} ${active ? 'active' : ''}`}
                      disabled={!slot.available}
                      onClick={() => setSelectedSlot(slot)}
                    >
                      <span>{slot.time || 'زمان نامشخص'}</span>
                      <small>{slot.available ? 'قابل رزرو' : 'رزرو شده'}</small>
                    </button>
                  );
                })
              ) : (
                <p className="muted">برای این تاریخ ساعت قابل رزرو پیدا نشد.</p>
              )}
            </div>

            <div className="lawyer-booking-type-actions">
              <button
                type="button"
                className="btn btn-gold lawyer-sheet-submit"
                disabled={!selectedSlot?.available}
                onClick={() => startPaymentForSlot(selectedSlot, 'in_person')}
              >
                رزرو مشاوره حضوری
              </button>
              <button
                type="button"
                className="btn btn-outline lawyer-sheet-submit"
                disabled={!selectedSlot?.available}
                onClick={() => startPaymentForSlot(selectedSlot, 'phone')}
              >
                رزرو مشاوره تلفنی
              </button>
            </div>
          </section>
        </div>
      )}

      {paymentSheetOpen && selectedSlot && (
        <div className="lawyer-time-sheet-backdrop payment" onClick={() => setPaymentSheetOpen(false)}>
          <section className="lawyer-payment-sheet booking-case-sheet" onClick={(e) => e.stopPropagation()}>
            <button className="lawyer-sheet-close-x" type="button" aria-label="بستن" onClick={() => setPaymentSheetOpen(false)}>×</button>
            <h3>تکمیل اطلاعات پرونده و پرداخت</h3>

            <div className="lawyer-payment-summary">
              <div><span>وکیل</span><strong>{lawyer.full_name || 'وکیل لکسارا'}</strong></div>
              <div><span>تاریخ</span><strong>{formatBookingDate(bookingDate)}</strong></div>
              <div><span>ساعت</span><strong>{selectedSlot.time}</strong></div>
              <div><span>نوع رزرو</span><strong>{bookingSessionType === 'phone' ? 'تلفنی' : 'حضوری'}</strong></div>
              {bookingSessionType === 'in_person' && lawyer.office_address && <div><span>آدرس</span><strong>{lawyer.office_address}</strong></div>}
              <div><span>مبلغ</span><strong>{Number(lawyer.consultation_fee || 0).toLocaleString('fa-IR')} تومان</strong></div>
            </div>

            <div className="booking-case-form">
              <label>
                عنوان پرونده
                <input
                  className="input"
                  value={caseTitle}
                  onChange={(e) => setCaseTitle(e.target.value)}
                  placeholder="مثلاً: مشاوره طلاق توافقی، اختلاف ملکی، مطالبه وجه..."
                  maxLength={120}
                />
              </label>

              <label>
                شرح مشکل
                <textarea
                  className="input"
                  value={caseDescription}
                  onChange={(e) => setCaseDescription(e.target.value)}
                  rows={5}
                  placeholder="مشکل خود را شفاف بنویسید تا وکیل قبل از جلسه دید اولیه داشته باشد."
                />
              </label>
            </div>

            {bookingMessage && <div className="lawyer-profile-message booking-case-error">{bookingMessage}</div>}

            <p className="muted">بعد از پرداخت، رزرو شما نهایی می‌شود و می‌توانید مدارک مورد نیاز را در حساب کاربری خود بارگذاری نمایید.</p>

            <button
              type="button"
              className="btn btn-gold lawyer-sheet-submit"
              disabled={Boolean(bookingSaving)}
              onClick={createBooking}
            >
              {bookingSaving ? 'در حال ثبت...' : 'پرداخت و نهایی‌سازی رزرو'}
            </button>
          </section>
        </div>
      )}

      {confirmedBooking && bookingInvoice && (
        <div className="lawyer-time-sheet-backdrop invoice" onClick={() => setConfirmedBooking(null)}>
          <section className="lawyer-invoice-sheet" onClick={(e) => e.stopPropagation()}>
            <button className="lawyer-sheet-close-x" type="button" aria-label="بستن" onClick={() => setConfirmedBooking(null)}>×</button>
            <h3>فاکتور رزرو شما</h3>
            <div className="lawyer-invoice-success">رزرو با موفقیت ثبت شد</div>

            <div className="lawyer-payment-summary invoice">
              <div><span>کد رزرو</span><strong>{bookingInvoice.booking_code}</strong></div>
              <div><span>وکیل</span><strong>{bookingInvoice.lawyer_name}</strong></div>
              <div><span>موکل</span><strong>{bookingInvoice.customer_name}</strong></div>
              <div><span>تاریخ</span><strong>{formatBookingDate(bookingInvoice.date || bookingDate)}</strong></div>
              <div><span>ساعت</span><strong>{bookingInvoice.time}</strong></div>
              <div><span>نوع رزرو</span><strong>{bookingInvoice.session_type_display || (bookingSessionType === 'phone' ? 'تلفنی' : 'حضوری')}</strong></div>
              <div><span>عنوان پرونده</span><strong>{bookingInvoice.subject || caseTitle}</strong></div>
              {bookingInvoice.office_address && <div><span>آدرس</span><strong>{bookingInvoice.office_address}</strong></div>}
              <div><span>مدت</span><strong>{Number(bookingInvoice.duration_minutes || 60).toLocaleString('fa-IR')} دقیقه</strong></div>
              <div><span>مبلغ</span><strong>{Number(bookingInvoice.amount || lawyer.consultation_fee || 0).toLocaleString('fa-IR')} تومان</strong></div>
              <div><span>وضعیت</span><strong>تایید شده</strong></div>
            </div>

            <div className="booking-upload-notice">شما می‌توانید مدارک مورد نیاز رزرو مشاوره خود را در حساب کاربری خود بارگذاری نمایید.</div>
            <p className="muted">پیامک تایید رزرو برای شماره شما ارسال شد.</p>
            <button type="button" className="btn btn-gold lawyer-sheet-submit" onClick={() => setConfirmedBooking(null)}>
              متوجه شدم
            </button>
          </section>
        </div>
      )}

    </main>
  );
}

function Detail({ label, value }: { label: string; value: any }) {
  return (
    <div className="lawyer-detail-item">
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  );
}

function SimpleNav({ hidden = false }: { hidden?: boolean }) {
  return (
    <nav className={`navbar landing-like-nav ${hidden ? 'nav-hidden' : ''}`}>
      <Link href="/" className="logo"><span className="logo-mark">ل</span> لکسارا</Link>
      <div className="nav-links">
        <Link className="nav-link" href="/">خانه</Link>
        <Link className="nav-link" href="/lawyers"><span className="lawyer-people-stack-icon" aria-hidden="true">👥</span>لیست وکلا</Link>
        <Link className="btn btn-gold btn-sm" href="/register">ثبت‌نام</Link>
      </div>
    </nav>
  );
}
