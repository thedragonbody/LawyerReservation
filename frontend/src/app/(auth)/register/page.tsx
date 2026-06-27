'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';
import { getDashboardPath, useAuthStore } from '@/lib/store';

type Step = 'role' | 'info' | 'otp';
type Role = 'customer' | 'lawyer';

export default function RegisterPage() {
  const [step, setStep] = useState<Step>('role');
  const [role, setRole] = useState<Role>('customer');
  const [form, setForm] = useState({ phone: '', first_name: '', last_name: '' });
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [devOtp, setDevOtp] = useState('');
  const router = useRouter();
  const { setUser, setTokens } = useAuthStore();

  useEffect(() => {
    const r = new URLSearchParams(window.location.search).get('role');
    if (r === 'lawyer' || r === 'customer') { setRole(r); setStep('info'); }
  }, []);

  const chooseRole = (r: Role) => { setRole(r); setStep('info'); setError(''); };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const { data } = await authApi.register({ ...form, role });

      console.log('REGISTER RESPONSE:', data);

      setDevOtp(
        data._dev_otp ||
        data.dev_otp ||
        data.otp ||
        data.code ||
        ''
      );

      setStep('otp');
    } catch (err: any) {
      const d = err.response?.data;

      console.log('REGISTER ERROR:', d);

      setError(
        d?.detail ||
        d?.phone?.[0] ||
        d?.first_name?.[0] ||
        d?.last_name?.[0] ||
        d?.role?.[0] ||
        JSON.stringify(d) ||
        'ثبت‌نام انجام نشد. اطلاعات را بررسی کن.'
      );
    } finally { setLoading(false); }
  };

  const handleVerify = async () => {
    const code = otp.join('');
    if (code.length < 6 || loading) return;
    setLoading(true); setError('');
    try {
      const { data } = await authApi.verifyOtp(form.phone, code);
      setTokens(data.access, data.refresh);
      setUser(data.user);
      router.push(getDashboardPath(data.user.role || role));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'کد واردشده صحیح نیست.');
      setOtp(['', '', '', '', '', '']);
    } finally { setLoading(false); }
  };

  const handleOtpInput = (i: number, val: string) => {
    if (!/^\d?$/.test(val)) return;
    const next = [...otp]; next[i] = val; setOtp(next);
    if (val && i < 5) document.getElementById(`otp-${i + 1}`)?.focus();
    if (next.every(Boolean) && val) setTimeout(() => handleVerify(), 120);
  };

  return (
    <main className="page-shell auth-page">
      <nav className="register-simple-logo-nav" aria-label="لوگوی لکسارا">
        <Link href="/" className="logo register-simple-logo"><span className="logo-mark">ل</span> لکسارا</Link>
      </nav>
      <div className="hero-orb" style={{ top: '12%', left: '8%' }} />

      {step === 'role' && (
        <section className="auth-card register-role-section glass animate-fade-up" style={{ width: 'min(860px, 100%)' }}>
          <div className="section-heading" style={{ marginBottom: 28 }}>
            <div className="section-eyebrow">نوع حساب</div>
            <h1 style={{ fontSize: '2.35rem' }}>چطور می‌خواهی از لکسارا استفاده کنی؟</h1>
            <p className="muted" style={{ marginTop: 10 }}>مسیر و امکانات کاربر و وکیل کاملاً جداست.</p>
          </div>
          <div className="register-role-grid">
            <button className="card motion-card register-role-card" onClick={() => chooseRole('customer')} style={{ padding: 30, color: 'inherit', cursor: 'pointer', textAlign: 'center' }}>
              <div style={{ fontSize: 42 }}>👤</div>
              <h3 style={{ margin: '12px 0 8px' }}>حساب کاربر</h3>
              <p className="secondary" style={{ lineHeight: 1.9 }}>برای پیدا کردن وکیل، رزرو مشاوره و پیگیری مدارک و جلسات.</p>
              <span className="register-kiosk-cta register-kiosk-cta-gold">ثبت‌نام کاربر</span>
            </button>
            <button className="card motion-card register-role-card" onClick={() => chooseRole('lawyer')} style={{ padding: 30, color: 'inherit', cursor: 'pointer', textAlign: 'center' }}>
              <div style={{ fontSize: 42 }}>⚖️</div>
              <h3 style={{ margin: '12px 0 8px' }}>حساب وکیل</h3>
              <p className="secondary" style={{ lineHeight: 1.9 }}>برای ساخت پروفایل حرفه‌ای، مدیریت نوبت‌ها و پذیرش موکل.</p>
              <span className="register-kiosk-cta register-kiosk-cta-outline">ثبت‌نام وکیل</span>
            </button>
          </div>
          <p className="muted" style={{ textAlign: 'center', marginTop: 22 }}>حساب داری؟ <Link href="/login" className="gold">وارد شو</Link></p>
        </section>
      )}

      {step === 'info' && (
        <section className="auth-card glass animate-fade-up">
          <button className="btn btn-ghost btn-sm" onClick={() => setStep('role')} style={{ marginBottom: 18 }}>تغییر نوع حساب</button>
          <div className="section-eyebrow">{role === 'lawyer' ? 'ثبت‌نام وکیل' : 'ثبت‌نام کاربر'}</div>
          <h1 style={{ fontSize: '2rem' }}>{role === 'lawyer' ? 'ساخت حساب وکیل' : 'ساخت حساب کاربری'}</h1>
          <p className="muted" style={{ margin: '10px 0 26px', lineHeight: 1.9 }}>تایید حساب با کد پیامکی انجام می‌شود و نیاز به ایمیل نیست.</p>
          {error && <Alert text={error} />}
          <form onSubmit={handleRegister}>
            <div className="grid-2">
              <div><label>نام</label><input className="input" required value={form.first_name} onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))} placeholder="مثلاً امین" /></div>
              <div><label>نام خانوادگی</label><input className="input" required value={form.last_name} onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))} placeholder="مثلاً محمدی" /></div>
            </div>
            <div style={{ marginTop: 14 }}><label>شماره موبایل</label><input className="input" type="tel" required value={form.phone} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))} placeholder="09123456789" /></div>
            <button className="btn btn-gold" type="submit" disabled={loading} style={{ width: '100%', marginTop: 20 }}>{loading ? 'در حال ساخت حساب...' : 'ادامه و دریافت کد'}</button>
          </form>
        </section>
      )}

      {step === 'otp' && (
        <section className="auth-card glass animate-fade-up">
          <div className="section-eyebrow">تکمیل ثبت‌نام</div>
          <h1 style={{ fontSize: '2rem' }}>شماره را تایید کن</h1>
          <p className="muted" style={{ margin: '10px 0 14px' }}>کد تایید برای <span className="gold">{form.phone}</span> ارسال شد.</p>
          {devOtp && <div className="badge badge-gold" style={{ marginBottom: 18 }}>کد توسعه: {devOtp}</div>}
          {error && <Alert text={error} />}
          <div className="otp-grid" style={{ margin: '18px 0 22px' }}>
            {otp.map((v, i) => <input key={i} id={`otp-${i}`} className="input otp-input" inputMode="numeric" maxLength={1} value={v} onChange={(e) => handleOtpInput(i, e.target.value)} />)}
          </div>
          <button className="btn btn-gold" onClick={handleVerify} disabled={loading || otp.join('').length < 6} style={{ width: '100%' }}>{loading ? 'در حال تایید...' : 'ورود به پنل اختصاصی'}</button>
        </section>
      )}
    </main>
  );
}

function Alert({ text }: { text: string }) {
  return <div className="badge badge-danger" style={{ width: '100%', justifyContent: 'flex-start', marginBottom: 16 }}>{text}</div>;
}
