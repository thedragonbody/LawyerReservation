'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { lawyerApi } from '@/lib/api';
import { getDashboardPath, useAuthStore } from '@/lib/store';

const PRACTICE_AREAS = [
  { key: 'corporate', label: 'حقوق شرکت‌ها', icon: '⚖️' },
  { key: 'criminal', label: 'کیفری و جزایی', icon: '🛡️' },
  { key: 'family', label: 'خانواده و طلاق', icon: '🏛️' },
  { key: 'immigration', label: 'مهاجرت', icon: '✈️' },
  { key: 'real_estate', label: 'ملک و املاک', icon: '🏢' },
  { key: 'intellectual_property', label: 'مالکیت فکری', icon: '©️' },
  { key: 'employment', label: 'کار و استخدام', icon: '👔' },
  { key: 'tax', label: 'مالیات', icon: '📋' },
  { key: 'personal_injury', label: 'خسارت و دیه', icon: '⚕️' },
  { key: 'estate_planning', label: 'وصیت و ارث', icon: '📜' },
  { key: 'civil_litigation', label: 'دعاوی حقوقی', icon: '⚖️' },
  { key: 'bankruptcy', label: 'ورشکستگی', icon: '📊' },
];

const STATS = [
  { value: '۵۰۰+', label: 'وکیل تاییدشده' },
  { value: '۱۲هزار+', label: 'مشاوره و پرونده' },
  { value: '۹۸٪', label: 'رضایت کاربران' },
  { value: '۵۰+', label: 'حوزه تخصصی' },
];


const HOME_PRACTICE_AREA_FA: Record<string, string> = {
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
  tax: 'حقوق مالیاتی',
  tax_law: 'حقوق مالیاتی',
  taxlaw: 'حقوق مالیاتی',
  personal_injury: 'خسارت و دیه',
  estate_planning: 'وصیت و ارث',
  civil_litigation: 'دعاوی حقوقی',
  bankruptcy: 'ورشکستگی',
  healthcare: 'حقوق پزشکی و سلامت',
  healthcare_law: 'حقوق پزشکی و سلامت',
  healthcarelaw: 'حقوق پزشکی و سلامت',
  environmental: 'حقوق محیط زیست',
  environmental_law: 'حقوق محیط زیست',
  environmentallaw: 'حقوق محیط زیست',
  international: 'حقوق بین‌الملل',
  international_law: 'حقوق بین‌الملل',
  internationallaw: 'حقوق بین‌الملل',
};

function translateHomePracticeArea(value: any) {
  const raw = String(value || '').trim();
  if (!raw) return 'مشاوره حقوقی';
  const key = raw.toLowerCase().replace(/[\s-]+/g, '_');
  const compactKey = raw.toLowerCase().replace(/[\s_-]+/g, '');
  return HOME_PRACTICE_AREA_FA[key] || HOME_PRACTICE_AREA_FA[compactKey] || HOME_PRACTICE_AREA_FA[raw] || raw;
}

const STEPS = [
  { n: '۰۱', title: 'وکیل مناسب را پیدا کن', body: 'بر اساس تخصص، سابقه، امتیاز و وضعیت پذیرش، بهترین گزینه را انتخاب کن.' },
  { n: '۰۲', title: 'زمان مشاوره را رزرو کن', body: 'روز و ساعت آزاد را انتخاب کن، موضوع پرونده را بنویس و مدارک را امن بارگذاری کن.' },
  { n: '۰۳', title: 'با خیال راحت مشاوره بگیر', body: 'همه‌چیز ساختارمند، محرمانه و قابل پیگیری در پنل اختصاصی تو ذخیره می‌شود.' },
];

export default function HomePage() {
  const [featuredLawyers, setFeaturedLawyers] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedArea, setSelectedArea] = useState('');
  const [smartMatchOpen, setSmartMatchOpen] = useState(false);
  const [smartStep, setSmartStep] = useState(1);
  const [smartLoading, setSmartLoading] = useState(false);
  const [smartResults, setSmartResults] = useState<any[]>([]);
  const [smartForm, setSmartForm] = useState({ area: '', city: '', budget: '', urgency: 'normal' });

  useEffect(() => {
    lawyerApi.list({ ordering: '-average_rating', page_size: 4 })
      .then((r) => setFeaturedLawyers(r.data.results || r.data || []))
      .catch(() => setFeaturedLawyers([]));
  }, []);

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (searchQuery.trim()) params.set('search', searchQuery.trim());
    if (selectedArea) params.set('area', selectedArea);
    window.location.href = `/lawyers?${params.toString()}`;
  };

  const runSmartMatch = async () => {
    setSmartLoading(true);
    try {
      const params: any = { page_size: 3, ordering: '-average_rating' };
      if (smartForm.area) params.area = smartForm.area;
      if (smartForm.city.trim()) params.city = smartForm.city.trim();
      if (smartForm.budget === 'economic') params.max_fee = 500000;
      if (smartForm.budget === 'middle') params.max_fee = 1500000;
      const r = await lawyerApi.list(params);
      setSmartResults((r.data.results || r.data || []).slice(0, 3));
      setSmartStep(5);
    } catch {
      setSmartResults([]);
      setSmartStep(5);
    } finally {
      setSmartLoading(false);
    }
  };

  const smartAreaLabel = PRACTICE_AREAS.find((a) => a.key === smartForm.area)?.label || 'همه حوزه‌ها';

  return (
    <main className="page-shell">
      <Navbar />

      <section className="hero">
        <div className="hero-orb" style={{ top: '10%', left: '4%' }} />
        <div className="hero-orb" style={{ bottom: '4%', right: '8%', width: 260, height: 260, animationDelay: '1.5s' }} />
        <div className="container" style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ maxWidth: 880, marginInline: 'auto', textAlign: 'center' }}>
            <div className="section-eyebrow animate-fade-up">پلتفرم امن رزرو وکیل</div>
            <h1 className="animate-fade-up stagger-1">
              وکیل درست، در زمان درست، <span className="gold">برای تصمیم درست</span>
            </h1>
            <p className="secondary animate-fade-up stagger-2" style={{ fontSize: 18, lineHeight: 2, maxWidth: 680, margin: '22px auto 34px' }}>
              لکسارا مسیر پیدا کردن و رزرو مشاوره با وکلای تاییدشده را ساده، سریع و محرمانه می‌کند؛ بدون فرم‌های پیچیده و بدون سردرگمی.
            </p>

            <div className="search-box glass animate-fade-up stagger-3">
              <input
                className="input"
                placeholder="نام وکیل، حوزه حقوقی یا کلمه کلیدی..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <select className="select" value={selectedArea} onChange={(e) => setSelectedArea(e.target.value)}>
                <option value="">همه حوزه‌های حقوقی</option>
                {PRACTICE_AREAS.map((a) => <option key={a.key} value={a.key}>{a.label}</option>)}
              </select>
              <button className="btn btn-gold" onClick={handleSearch}>وکلا</button>
            </div>

            <div className="home-stats-inline animate-fade-up stagger-4" aria-label="آمار لکسارا">
              <div className="home-stats-track">
                {[...STATS, ...STATS].map((s, idx) => (
                  <div key={`${s.label}-${idx}`} className="home-stat-inline-item">
                    <strong className="gold">{s.value}</strong>
                    <span>{s.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* HOME ORDER: featured lawyers before practice areas */}
      {featuredLawyers.length > 0 && (
        <section className="section home-featured-section">
          <div className="container">
            <div className="section-heading">
              <div className="section-eyebrow">وکلای برتر</div>
              <h2>پیشنهادهای منتخب لکسارا</h2>
              <div className="gold-divider" />
            </div>
            <div className="home-featured-grid home-lawyers-showcase-grid">
              {featuredLawyers.slice(0, 4).map((lawyer, i) => <LawyerCard key={lawyer.id || i} lawyer={lawyer} rank={i + 1} />)}
            </div>
            <div style={{ textAlign: 'center', marginTop: 34 }}>
              <Link href="/lawyers" className="btn btn-outline btn-lg home-all-lawyers-glow">مشاهده همه وکلا</Link>
            </div>

            <div id="smart-lawyer-entry" className="smart-lawyer-entry smart-lawyer-home-kiosk animate-fade-up stagger-4">
              <div className="smart-kiosk-glow" />
              <div className="smart-kiosk-icon">⚖</div>
              <div className="smart-kiosk-copy">
                <span className="smart-kiosk-eyebrow">انتخاب هوشمند</span>
                <strong>وکیل مناسب پرونده‌ات را پیدا کن</strong>
                <p>موضوع، شهر، بودجه و فوریت را وارد کن؛ لکسارا ۳ وکیل مناسب را پیشنهاد می‌دهد.</p>
              </div>
              <button className="btn btn-gold smart-kiosk-btn smart-kiosk-btn-glow" type="button" onClick={() => { setSmartMatchOpen(true); setSmartStep(1); }}>شروع انتخاب هوشمند</button>
            </div>

            {smartMatchOpen && (
              <div className="smart-lawyer-modal-backdrop" onClick={() => setSmartMatchOpen(false)}>
                <section className="smart-lawyer-modal glass" onClick={(e) => e.stopPropagation()}>
                  <button className="smart-lawyer-close" type="button" onClick={() => setSmartMatchOpen(false)}>×</button>
                  <div className="section-eyebrow">وکیل مناسب من</div>
                  <h2>مسیر سریع انتخاب وکیل</h2>
                  <p className="muted">چهار قدم کوتاه را پر کن تا پیشنهادهای مناسب‌تری برای پرونده‌ات ببینی.</p>

                  <div className="smart-lawyer-progress">
                    {[1, 2, 3, 4].map((n) => <span key={n} className={smartStep >= n ? 'active' : ''}>{n}</span>)}
                  </div>

                  {smartStep === 1 && (
                    <div key="smart-step-1" className="smart-step-card smart-step-animated">
                      <h3>موضوع پرونده چیست؟</h3>
                      <select className="select" value={smartForm.area} onChange={(e) => setSmartForm((f) => ({ ...f, area: e.target.value }))}>
                        <option value="">همه حوزه‌ها</option>
                        {PRACTICE_AREAS.map((a) => <option key={a.key} value={a.key}>{a.label}</option>)}
                      </select>
                      <button className="btn btn-gold" type="button" onClick={() => setSmartStep(2)}>مرحله بعد</button>
                    </div>
                  )}

                  {smartStep === 2 && (
                    <div key="smart-step-2" className="smart-step-card smart-step-animated">
                      <h3>شهر موردنظر کجاست؟</h3>
                      <input className="input" value={smartForm.city} onChange={(e) => setSmartForm((f) => ({ ...f, city: e.target.value }))} placeholder="مثلاً تهران" />
                      <button className="btn btn-gold" type="button" onClick={() => setSmartStep(3)}>مرحله بعد</button>
                    </div>
                  )}

                  {smartStep === 3 && (
                    <div key="smart-step-3" className="smart-step-card smart-step-animated">
                      <h3>بودجه مشاوره را انتخاب کن</h3>
                      <div className="smart-choice-grid smart-choice-grid-inline">
                        {[
                          ['economic', 'اقتصادی'],
                          ['middle', 'متوسط'],
                          ['premium', 'ویژه'],
                        ].map(([key, label]) => (
                          <button key={key} type="button" className={smartForm.budget === key ? 'active' : ''} onClick={() => setSmartForm((f) => ({ ...f, budget: key }))}>{label}</button>
                        ))}
                      </div>
                      <button className="btn btn-gold" type="button" onClick={() => setSmartStep(4)}>مرحله بعد</button>
                    </div>
                  )}

                  {smartStep === 4 && (
                    <div key="smart-step-4" className="smart-step-card smart-step-animated">
                      <h3>پرونده چقدر فوری است؟</h3>
                      <div className="smart-choice-grid smart-choice-grid-inline">
                        {[
                          ['normal', 'معمولی'],
                          ['urgent', 'فوری'],
                          ['critical', 'خیلی فوری'],
                        ].map(([key, label]) => (
                          <button key={key} type="button" className={smartForm.urgency === key ? 'active' : ''} onClick={() => setSmartForm((f) => ({ ...f, urgency: key }))}>{label}</button>
                        ))}
                      </div>
                      <button className="btn btn-gold" type="button" onClick={runSmartMatch} disabled={smartLoading}>{smartLoading ? 'در حال جستجو...' : 'نمایش ۳ وکیل پیشنهادی'}</button>
                    </div>
                  )}

                  {smartStep === 5 && (
                    <div key="smart-step-results" className="smart-results smart-step-animated">
                      <div className="smart-result-summary">نتیجه برای: {smartAreaLabel} {smartForm.city ? `در ${smartForm.city}` : ''}</div>
                      {smartResults.length ? smartResults.map((lawyer, i) => (
                        <Link key={lawyer.id || i} href={`/lawyers/${lawyer.id}`} className="smart-result-card">
                          <strong>{lawyer.full_name || 'وکیل لکسارا'}</strong>
                          <span>{translateHomePracticeArea(lawyer.primary_area)} · امتیاز {Number(lawyer.average_rating || 0).toLocaleString('fa-IR')}</span>
                          <em>مشاهده پروفایل</em>
                        </Link>
                      )) : <p className="muted">فعلاً پیشنهادی پیدا نشد؛ فیلترها را ساده‌تر کن.</p>}
                      <button className="btn btn-outline" type="button" onClick={() => setSmartStep(1)}>شروع دوباره</button>
                    </div>
                  )}
                </section>
              </div>
            )}
          </div>
        </section>
      )}


      <section className="section" style={{ background: 'rgba(11,18,34,.58)' }}>
        <div className="container">
          <div className="section-heading">
            <div className="section-eyebrow">حوزه‌های تخصصی</div>
            <h2>هر مسئله حقوقی، یک مسیر تخصصی</h2>
            <div className="gold-divider" />
          </div>
          <div className="grid-auto">
            {PRACTICE_AREAS.map((area, i) => (
              <Link key={area.key} href={`/lawyers?area=${area.key}`}>
                <div className="card motion-card practice-card animate-fade-up" style={{ animationDelay: `${i * 0.035}s` }}>
                  <div className="practice-icon">{area.icon}</div>
                  <strong className="practice-title">{area.label}</strong>
                  <p className="muted practice-hint">مشاهده وکلای این حوزه</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section" style={{ background: 'rgba(11,18,34,.62)' }}>
        <div className="container">
          <div className="section-heading">
            <div className="section-eyebrow">فرآیند کار</div>
            <h2>رزرو مشاوره در سه قدم</h2>
            <div className="gold-divider" />
          </div>
          <div className="grid-3">
            {STEPS.map((step) => (
              <div key={step.n} className="card step-card">
                <div className="gold step-number">{step.n}</div>
                <h3 className="step-title">{step.title}</h3>
                <p className="secondary step-body">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section" style={{ textAlign: 'center' }}>
        <div className="container">
          <div className="section-eyebrow">شروع همکاری</div>
          <h2>کاربر هستی یا وکیل؟ پنل اختصاصی خودت را بساز</h2>
          <p className="secondary" style={{ margin: '18px auto 34px', maxWidth: 620, lineHeight: 2 }}>
            حساب کاربری موکل و وکیل کاملاً جداست؛ هر نقش مسیر، داشبورد و امکانات خودش را دارد.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link href="/register?role=customer" className="btn btn-gold btn-lg">ثبت‌نام به عنوان کاربر</Link>
            <Link href="/register?role=lawyer" className="btn btn-outline btn-lg">ثبت‌نام به عنوان وکیل</Link>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}

function LawyerCard({ lawyer, rank = 1 }: { lawyer: any; rank?: number }) {
  const initials = (lawyer.full_name || 'وکیل').slice(0, 1);
  const ratingValue = Number(lawyer.average_rating || 0);
  const fee = Number(lawyer.consultation_fee || 0).toLocaleString('fa-IR');
  const specialty = translateHomePracticeArea(lawyer.primary_area);
  const persianRank = String(rank).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]);

  return (
    <Link href={`/lawyers/${lawyer.id}`} className="home-lawyer-mini-link">
      <article className="card motion-card home-lawyer-mini-card">
        <div className="home-lawyer-mini-top">
          <span className="home-lawyer-mini-badge">منتخب #{persianRank}</span>
          <span className="home-lawyer-mini-rate">{ratingValue ? ratingValue.toFixed(1).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]) : 'جدید'} ★</span>
        </div>

        <div className="home-lawyer-mini-main">
          <div className="avatar home-lawyer-mini-avatar">
            {lawyer.avatar_url ? <img src={lawyer.avatar_url} alt={lawyer.full_name || 'وکیل'} /> : initials}
          </div>
          <div className="home-lawyer-mini-info">
            <h3>{lawyer.full_name || 'وکیل تاییدشده'}</h3>
            <p>{specialty}</p>
          </div>
        </div>

        <div className="home-lawyer-mini-fee">
          <span>هزینه مشاوره</span>
          <strong>{fee} تومان</strong>
        </div>

        <div className="home-lawyer-mini-footer">
          <span>مشاهده پروفایل</span>
        </div>
      </article>
    </Link>
  );
}

function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { user, fetchMe } = useAuthStore();
  useEffect(() => { fetchMe(); }, [fetchMe]);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 42);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  const links = [
    { href: '/lawyers', label: 'وکلا' },
    { href: user ? getDashboardPath(user.role, user.is_staff) : '/register', label: user ? 'پنل من' : 'ثبت نام' },
  ];
  return (
    <>
      <nav className={`navbar ${scrolled ? 'is-scrolled' : ''}`}>
        <Link href="/" className="logo"><span className="logo-mark">ل</span> لکسارا</Link>
        <div className="nav-links">
          {links.map((l) => <Link key={l.href} href={l.href} className="nav-link">{l.label}</Link>)}
          <Link href="/register" className="btn btn-gold btn-sm">شروع کنید</Link>
        </div>
        <button className="mobile-menu-btn btn btn-outline btn-sm" onClick={() => setOpen(!open)}>{open ? 'بستن' : 'منو'}</button>
      </nav>
      {open && (
        <div className="mobile-panel glass animate-fade-in">
          {links.map((l) => <Link key={l.href} href={l.href} className="nav-link" onClick={() => setOpen(false)}>{l.label}</Link>)}
          <Link href="/register" className="btn btn-gold" onClick={() => setOpen(false)}>ثبت‌نام</Link>
        </div>
      )}
    </>
  );
}

function Footer() {
  return (
    <footer style={{ background: 'var(--navy-2)', borderTop: '1px solid rgba(201,168,76,.1)', padding: '46px 0 26px' }}>
      <div className="container">
        <div className="footer-clean-grid" style={{ alignItems: 'start' }}>
          <div>
            <div className="logo" style={{ marginBottom: 12 }}><span className="logo-mark">ل</span> لکسارا</div>
            <p className="muted" style={{ lineHeight: 2, fontSize: 13 }}>لکسارا یک پلتفرم اتصال کاربر و وکیل است و جایگزین مشاوره حقوقی مستقل یا موسسه حقوقی نیست.</p>
          </div>
        </div>
        <div style={{ borderTop: '1px solid rgba(201,168,76,.08)', marginTop: 30, paddingTop: 20, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <span className="muted" style={{ fontSize: 12 }}>© {new Date().getFullYear()} لکسارا</span>
          <span className="muted" style={{ fontSize: 12 }}>طراحی امن، ریسپانسیو و فارسی‌سازی شده</span>
        </div>
      </div>
    </footer>
  );
}
