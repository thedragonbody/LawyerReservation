'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { lawyerApi } from '@/lib/api';

const AREAS: Record<string, string> = {
  corporate: 'حقوق شرکت‌ها',
  criminal: 'کیفری و جزایی',
  criminal_defense: 'دفاع کیفری',
  family: 'خانواده و طلاق',
  family_law: 'حقوق خانواده',
  immigration: 'مهاجرت',
  real_estate: 'ملک و املاک',
  intellectual_property: 'مالکیت فکری',
  employment: 'کار و استخدام',
  employment_law: 'حقوق کار و استخدام',
  tax_law: 'حقوق مالیاتی',
  personal_injury: 'خسارت و دیه',
  estate_planning: 'وصیت و ارث',
  civil_litigation: 'دعاوی حقوقی',
  bankruptcy: 'ورشکستگی',
  healthcare_law: 'حقوق پزشکی و سلامت',
  environmental_law: 'حقوق محیط زیست',
  international_law: 'حقوق بین‌الملل',
};

const PRACTICE_AREA_FA_LIST: Record<string, string> = {
  corporate: 'حقوق شرکت‌ها',
  corporate_law: 'حقوق شرکت‌ها',
  corporatelaw: 'حقوق شرکت‌ها',
  criminal: 'کیفری و جزایی',
  criminal_defense: 'دفاع کیفری',
  criminaldefense: 'دفاع کیفری',
  family: 'خانواده و طلاق',
  family_law: 'حقوق خانواده',
  familylaw: 'حقوق خانواده',
  immigration: 'مهاجرت',
  real_estate: 'ملک و املاک',
  intellectual_property: 'مالکیت فکری',
  employment: 'کار و استخدام',
  employment_law: 'حقوق کار و استخدام',
  employmentlaw: 'حقوق کار و استخدام',
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
};

function translatePracticeAreaList(value: any) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const key = raw.toLowerCase().replace(/[\s-]+/g, '_');
  const compactKey = raw.toLowerCase().replace(/[\s_-]+/g, '');
  return PRACTICE_AREA_FA_LIST[key] || PRACTICE_AREA_FA_LIST[compactKey] || PRACTICE_AREA_FA_LIST[raw] || raw;
}

function getLawyerSpecialties(lawyer: any) {
  const areas = Array.isArray(lawyer?.practice_areas) ? lawyer.practice_areas : [];
  const mapped = areas
    .map((a: any) => translatePracticeAreaList(a?.area_display || a?.label || a?.name || a?.area))
    .filter(Boolean);
  const primary = lawyer?.primary_area ? [translatePracticeAreaList(lawyer.primary_area)] : [];
  return Array.from(new Set([...primary, ...mapped]));
}



const CITIES = ['تهران', 'مشهد', 'اصفهان', 'شیراز', 'تبریز', 'کرج', 'قم', 'اهواز', 'رشت', 'یزد'];

export default function LawyersPage() {
  const [navHidden, setNavHidden] = useState(false);
  const [lawyers, setLawyers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [area, setArea] = useState('');
  const [city, setCity] = useState('');
  const [maxFee, setMaxFee] = useState('');
  const [minRating, setMinRating] = useState('');
  const [smartMatchOpen, setSmartMatchOpen] = useState(false);
  const [smartStep, setSmartStep] = useState(1);
  const [smartLoading, setSmartLoading] = useState(false);
  const [smartResults, setSmartResults] = useState<any[]>([]);
  const [smartForm, setSmartForm] = useState({ area: '', city: '', budget: '', urgency: 'normal' });

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

  

  

  

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setSearch(q.get('search') || '');
    setArea(q.get('area') || '');
    setCity(q.get('city') || '');
    setMaxFee(q.get('max_fee') || '');
    setMinRating(q.get('min_rating') || '');
  }, []);

  const query = useMemo(
    () => ({ search: search || undefined, area: area || undefined, city: city || undefined, max_fee: maxFee || undefined, min_rating: minRating || undefined, ordering: '-average_rating' }),
    [search, area, city, maxFee, minRating]
  );

  useEffect(() => {
    setLoading(true);
    lawyerApi.list(query)
      .then((r) => setLawyers(r.data.results || r.data || []))
      .catch(() => setLawyers([]))
      .finally(() => setLoading(false));
  }, [query]);


  const runSmartMatch = async () => {
    setSmartLoading(true);
    const budgetMax =
      smartForm.budget === 'economic' ? '300000' :
      smartForm.budget === 'middle' ? '700000' :
      smartForm.budget === 'premium' ? '1200000' :
      undefined;

    const params: any = {
      page_size: 3,
      ordering: '-average_rating',
      area: smartForm.area || undefined,
      city: smartForm.city || undefined,
      max_fee: budgetMax,
    };

    try {
      const res = await lawyerApi.list(params);
      const items = res.data.results || res.data || [];
      setSmartResults(items);
      setSmartStep(5);
    } catch {
      setSmartResults([]);
      setSmartStep(5);
    } finally {
      setSmartLoading(false);
    }
  };

  return (
    <main className="page-shell lawyers-list-page" style={{ paddingTop: 92 }}>
      <SimpleNav hidden={navHidden} />

      <section className="section" style={{ paddingTop: 34 }}>
        <div className="container">
          <div className="section-heading">
            <div className="section-eyebrow">لیست و وکلا</div>
            <h1 style={{ fontSize: 'clamp(2rem, 5vw, 4rem)' }}>وکیل مناسب پرونده‌ات را پیدا کن</h1>
</div>

          <div className="glass lawyer-search-box">
            <input
              className="input lawyer-search-main-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="جستجو بر اساس نام، شماره پروانه، تخصص یا توضیح..."
            />

            <div className="lawyer-filter-row lawyer-filter-row-primary">
              <select className="select" value={area} onChange={(e) => setArea(e.target.value)}>
              <option value="">همه حوزه‌ها</option>
              {Object.entries(AREAS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>

            <select className="select" value={city} onChange={(e) => setCity(e.target.value)}>
              <option value="">همه شهرها</option>
              {CITIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            </div>

            <div className="lawyer-filter-row lawyer-filter-row-secondary">
              <select className="select" value={maxFee} onChange={(e) => setMaxFee(e.target.value)}>
              <option value="">همه هزینه‌ها</option>
              <option value="300000">تا ۳۰۰ هزار تومان</option>
              <option value="500000">تا ۵۰۰ هزار تومان</option>
              <option value="800000">تا ۸۰۰ هزار تومان</option>
              <option value="1200000">تا ۱.۲ میلیون تومان</option>
            </select>

            <select className="select" value={minRating} onChange={(e) => setMinRating(e.target.value)}>
              <option value="">همه امتیازها</option>
              <option value="5">۵ ستاره</option>
              <option value="4">۴ ستاره به بالا</option>
              <option value="3">۳ ستاره به بالا</option>
            </select>
            </div>
{(search || area || city || maxFee || minRating) && (
              <button className="btn btn-outline" onClick={() => { setSearch(''); setArea(''); setCity(''); setMaxFee(''); setMinRating(''); }}>
                پاک کردن فیلتر
              </button>
            )}
          </div>
          <div className="lawyers-smart-mini-kiosk card">
            <div className="lawyers-smart-mini-icon">⚖</div>
            <div className="lawyers-smart-mini-copy">
              <span>انتخاب هوشمند</span>
              <strong>وکیل مناسب پرونده‌ات را پیدا کن</strong>
              <small>چند سوال کوتاه جواب بده و پیشنهاد دقیق‌تر بگیر.</small>
            </div>
            <button type="button" className="btn btn-gold lawyers-smart-mini-btn" onClick={() => { setSmartMatchOpen(true); setSmartStep(1); }}>شروع</button>
          </div>

{loading ? (
            <LoadingGrid />
          ) : lawyers.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <h3>نتیجه‌ای پیدا نشد</h3>
              <p className="muted" style={{ marginTop: 10 }}>فیلترها یا عبارت جستجو را تغییر بده.</p>
            </div>
          ) : (
            <>
<div className="lawyers-two-grid lawyers-enter-grid">
                {lawyers.map((lawyer, index) => <LawyerCard key={lawyer.id} lawyer={lawyer} index={index} />)}
              </div>
            </>
          )}
        </div>
      </section>

      {smartMatchOpen && (
        <div className="smart-lawyer-modal-backdrop lawyers-smart-modal-backdrop" onClick={() => setSmartMatchOpen(false)}>
          <section className="smart-lawyer-modal lawyers-smart-modal" onClick={(e) => e.stopPropagation()}>
            <button className="smart-modal-close lawyers-smart-close" type="button" aria-label="بستن" onClick={() => setSmartMatchOpen(false)}><span>×</span></button>
            <div className="smart-lawyer-modal-head">
              <span>مسیر سریع انتخاب وکیل</span>
              <h3>وکیل مناسب پرونده‌ات را پیدا کن</h3>
              <p>چند سوال کوتاه را جواب بده تا پیشنهاد دقیق‌تری بگیری.</p>
            </div>

            <div className="smart-lawyer-progress">
              {[1, 2, 3, 4].map((step) => (
                <span key={step} className={smartStep >= step ? 'active' : ''}>{step}</span>
              ))}
            </div>

            {smartStep === 1 && (
              <div key="lawyers-smart-step-1" className="smart-step-card smart-step-animated lawyers-smart-step-area-compact">
                <h4>موضوع پرونده چیست؟</h4>
                <div className="lawyers-smart-area-scroll" role="listbox" aria-label="انتخاب حوزه حقوقی">
                  {Object.entries(AREAS).map(([k, v]) => (
                    <button
                      key={k}
                      type="button"
                      className={smartForm.area === k ? 'active' : ''}
                      onClick={() => setSmartForm((p) => ({ ...p, area: k }))}
                    >
                      {v}
                    </button>
                  ))}
                </div>
                <button className="btn btn-gold" type="button" onClick={() => setSmartStep(2)}>مرحله بعد</button>
              </div>
            )}

            {smartStep === 2 && (
              <div key="lawyers-smart-step-2" className="smart-step-card smart-step-animated">
                <h4>در کدام شهر دنبال وکیل هستی؟</h4>
                <input className="input" value={smartForm.city} onChange={(e) => setSmartForm((p) => ({ ...p, city: e.target.value }))} placeholder="مثلاً تهران" />
                <div className="smart-step-actions">
                  <button className="btn btn-outline" type="button" onClick={() => setSmartStep(1)}>قبلی</button>
                  <button className="btn btn-gold" type="button" onClick={() => setSmartStep(3)}>مرحله بعد</button>
                </div>
              </div>
            )}

            {smartStep === 3 && (
              <div key="lawyers-smart-step-3" className="smart-step-card smart-step-animated">
                <h4>بودجه مشاوره را انتخاب کن</h4>
                <div className="smart-choice-grid smart-choice-grid-inline">
                  {[
                    ['economic', 'اقتصادی'],
                    ['middle', 'متوسط'],
                    ['premium', 'ویژه'],
                  ].map(([key, label]) => (
                    <button key={key} type="button" className={smartForm.budget === key ? 'active' : ''} onClick={() => setSmartForm((p) => ({ ...p, budget: key }))}>{label}</button>
                  ))}
                </div>
                <div className="smart-step-actions">
                  <button className="btn btn-outline" type="button" onClick={() => setSmartStep(2)}>قبلی</button>
                  <button className="btn btn-gold" type="button" onClick={() => setSmartStep(4)}>مرحله بعد</button>
                </div>
              </div>
            )}

            {smartStep === 4 && (
              <div key="lawyers-smart-step-4" className="smart-step-card smart-step-animated">
                <h4>فوریت پرونده چقدر است؟</h4>
                <div className="smart-choice-grid smart-choice-grid-inline">
                  {[
                    ['normal', 'معمولی'],
                    ['urgent', 'فوری'],
                    ['critical', 'خیلی فوری'],
                  ].map(([key, label]) => (
                    <button key={key} type="button" className={smartForm.urgency === key ? 'active' : ''} onClick={() => setSmartForm((p) => ({ ...p, urgency: key }))}>{label}</button>
                  ))}
                </div>
                <div className="smart-step-actions">
                  <button className="btn btn-outline" type="button" onClick={() => setSmartStep(3)}>قبلی</button>
                  <button className="btn btn-gold" type="button" onClick={runSmartMatch}>{smartLoading ? 'در حال بررسی...' : 'دیدن پیشنهادها'}</button>
                </div>
              </div>
            )}

            {smartStep === 5 && (
              <div key="lawyers-smart-step-results" className="smart-results smart-step-animated">
                <h4>پیشنهادهای مناسب</h4>
                {smartResults.length === 0 ? (
                  <p className="muted">فعلاً پیشنهادی با این فیلترها پیدا نشد؛ فیلترها را ساده‌تر کن.</p>
                ) : (
                  smartResults.map((lawyer) => (
                    <Link key={lawyer.id} href={`/lawyers/${lawyer.id}`} className="smart-result-card">
                      <strong>{lawyer.full_name || 'وکیل منتخب'}</strong>
                      <span>{translatePracticeAreaList(lawyer.primary_area) || 'مشاوره حقوقی'} · {lawyer.city || 'شهر ثبت نشده'}</span>
                    </Link>
                  ))
                )}
                <div className="smart-step-actions">
                  <button className="btn btn-outline" type="button" onClick={() => setSmartStep(1)}>شروع دوباره</button>
                  <button className="btn btn-gold" type="button" onClick={() => setSmartMatchOpen(false)}>بستن</button>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

    </main>
  );
}

function LawyerCard({ lawyer, index = 0 }: { lawyer: any; index?: number }) {
  const rating = Math.round(Number(lawyer.average_rating || 0));
  const initials = (lawyer.full_name || 'و').slice(0, 1);
  return (
    <Link href={`/lawyers/${lawyer.id}`} className="lawyer-list-card-link">
      <article className="card motion-card lawyer-list-card redesigned lawyer-enter-card" style={{ animationDelay: `${Math.min(index, 8) * 0.075}s` }}>
        <div className="lawyer-card-glow" />
        <div className="lawyer-list-card-head">
          <div className="avatar lawyer-list-avatar">
            {lawyer.avatar_url ? <img src={lawyer.avatar_url} alt={lawyer.full_name || 'وکیل'} /> : initials}
          </div>

          <div className="lawyer-list-title">
            <div className="lawyer-title-line">
              <h3 className="lawyer-card-name-text">{lawyer.full_name || 'وکیل لکسارا'}</h3>
              {lawyer.first_available_slot?.time && (
                <span className="first-slot-badge">اولین وقت: {lawyer.first_available_slot.time}</span>
              )}
            </div>
          </div>
        </div>
        <div className="lawyer-card-specialties-rail" aria-label="تخصص‌های وکیل">
          <div className="lawyer-card-specialties-track">
            {[...getLawyerSpecialties(lawyer), ...getLawyerSpecialties(lawyer)].map((item: any, idx: number) => (
              <span key={`${item}-${idx}`} className="lawyer-card-specialty-chip">{item}</span>
            ))}
          </div>
        </div>

        <div className="lawyer-smart-badges">
          {(lawyer.smart_badges || []).slice(0, 1).map((b: string) => <span key={b} data-badge={b}>{b}</span>)}
        </div>

        <div className="lawyer-list-card-tags">
          <span>{Number(lawyer.years_experience || 0).toLocaleString('fa-IR')} سال سابقه</span>
          {lawyer.city && <span>شهر: {lawyer.city}</span>}
          {lawyer.bar_number && <span>پروانه: {lawyer.bar_number}</span>}
        </div>

        <div className="lawyer-list-card-foot">
          <span className="gold lawyer-list-stars">
            {'★'.repeat(rating)}{'☆'.repeat(5 - rating)}
            <small className="muted">میانگین {Number(lawyer.average_rating || 0).toFixed(1)}</small>
          </span>
          <strong className="lawyer-card-price">{Number(lawyer.consultation_fee || 0).toLocaleString('fa-IR')} تومان</strong>
        </div>

        <div className="lawyer-card-cta">مشاهده پروفایل و رزرو وقت</div>
      </article>
    </Link>
  );
}

function LoadingGrid() {
  return (
    <div className="lawyers-two-grid">
      {[1, 2, 3, 4].map((x) => <div key={x} className="card" style={{ height: 250, opacity: .6 }} />)}
    </div>
  );
}

function SimpleNav({ hidden = false }: { hidden?: boolean }) {
  return (
    <nav className={`navbar landing-like-nav ${hidden ? 'nav-hidden' : ''}`}>
      <Link href="/" className="logo"><span className="logo-mark">ل</span> لکسارا</Link>
      <div className="nav-links">
        <Link className="nav-link" href="/">خانه</Link>
        <Link className="btn btn-gold btn-sm" href="/register">ثبت‌نام</Link>
      </div>
    </nav>
  );
}
