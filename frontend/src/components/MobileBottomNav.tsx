'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { getDashboardPath, useAuthStore } from '@/lib/store';

export default function MobileBottomNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [legalOpen, setLegalOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const { user, fetchMe, logout } = useAuthStore();

  useEffect(() => { fetchMe(); }, [fetchMe]);
  useEffect(() => { setOpen(false); setLegalOpen(false); setAboutOpen(false); }, [pathname]);

  const accountHref = user ? getDashboardPath(user.role, user.is_staff) : '/register';
  const accountLabel = user ? (user.role === 'lawyer' ? 'پنل وکیل' : 'حساب من') : 'ثبت نام';

  const items = useMemo(() => ([
    { href: '/', label: 'خانه', icon: '⌂', active: pathname === '/' },
    { href: '/lawyers', label: 'جستجو', icon: '⌕', active: pathname?.startsWith('/lawyers') },
    { href: accountHref, label: accountLabel, icon: '◉', active: pathname?.startsWith('/dashboard') || pathname === '/login' },
  ]), [pathname, accountHref, accountLabel]);

  return (
    <>
      {open && <button className="bottom-sheet-backdrop" aria-label="بستن منو" onClick={() => setOpen(false)} />}

      <div className={`mobile-bottom-sheet glass ${open ? 'is-open' : ''}`} role="dialog" aria-label="منوی بیشتر">
        <div className="bottom-sheet-handle" />
        <div className="bottom-sheet-title">منوی سریع لکسارا</div>
        <div className="bottom-sheet-grid">
          <Link href="/register?role=customer" className="bottom-sheet-link">ثبت‌نام کاربر</Link>
          <Link href="/register?role=lawyer" className="bottom-sheet-link">ثبت‌نام وکیل</Link>
          <Link href="/lawyers" className="bottom-sheet-link">همه وکلا</Link>
          <Link href={accountHref} className="bottom-sheet-link">{user ? 'ورود به پنل' : 'ثبت نام'}</Link>

          <button
            type="button"
            className={`bottom-sheet-link bottom-sheet-toggle ${legalOpen ? 'is-active' : ''}`}
            onClick={() => {
              setLegalOpen((v) => !v);
              setAboutOpen(false);
            }}
          >
            بیشتر و قوانین <span>{legalOpen ? '−' : '+'}</span>
          </button>

          <button
            type="button"
            className={`bottom-sheet-link bottom-sheet-toggle ${aboutOpen ? 'is-active' : ''}`}
            onClick={() => {
              setAboutOpen((v) => !v);
              setLegalOpen(false);
            }}
          >
            درباره و تماس <span>{aboutOpen ? '−' : '+'}</span>
          </button>

          {legalOpen && (
            <div className="bottom-sheet-panel bottom-sheet-legal-panel">
              <div className="legal-mini-card">
                <strong>قوانین و مقررات</strong>
                <p>استفاده از لکسارا به معنی پذیرش قوانین رزرو، پرداخت، محرمانگی اطلاعات و رفتار حرفه‌ای در ارتباط با وکیل است.</p>
              </div>
              <div className="legal-mini-card">
                <strong>حریم خصوصی</strong>
                <p>اطلاعات هویتی، شماره تماس، مدارک و پیام‌های کاربران محرمانه است و فقط برای ارائه خدمات حقوقی استفاده می‌شود.</p>
              </div>
              <div className="legal-mini-card">
                <strong>قوانین لغو رزرو</strong>
                <p>لغو رزرو طبق زمان باقی‌مانده تا جلسه بررسی می‌شود و در نسخه پرداخت واقعی، شرایط استرداد وجه اعمال خواهد شد.</p>
              </div>
              <div className="legal-mini-card">
                <strong>سلب مسئولیت حقوقی</strong>
                <p>لکسارا واسطه ارتباط کاربر و وکیل است و جایگزین مشاوره رسمی، قرارداد وکالت یا تصمیم حقوقی مستقل نیست.</p>
              </div>
            </div>
          )}

          {aboutOpen && (
            <div className="bottom-sheet-panel bottom-sheet-about-panel">
              <div className="legal-mini-card">
                <strong>درباره ما</strong>
                <p>لکسارا برای ساده‌سازی پیدا کردن، مقایسه و رزرو مشاوره با وکلای تاییدشده طراحی شده است.</p>
              </div>
              <div className="legal-mini-card">
                <strong>تماس با ما</strong>
                <p>برای پشتیبانی، پیگیری رزرو یا گزارش مشکل می‌توانید از بخش پشتیبانی آینده لکسارا استفاده کنید.</p>
              </div>
            </div>
          )}

          {user && <button className="bottom-sheet-link danger" onClick={() => logout()}>خروج از حساب</button>}
        </div>
      </div>

      <nav className="mobile-bottom-nav" aria-label="ناوبری موبایل">
        {items.map((item) => (
          <Link key={item.href} href={item.href} className={`mobile-bottom-item ${item.active ? 'is-active' : ''}`}>
            <span className="mobile-bottom-icon">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
        <button className={`mobile-bottom-item ${open ? 'is-active' : ''}`} onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="mobile-more-menu">
          <span className="mobile-bottom-icon">☰</span>
          <span>بیشتر</span>
        </button>
      </nav>
    </>
  );
}
