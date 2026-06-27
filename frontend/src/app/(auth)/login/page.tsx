'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';
import { getDashboardPath, useAuthStore } from '@/lib/store';

type Step = 'phone' | 'otp';

export default function LoginPage() {
  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [devOtp, setDevOtp] = useState('');
  const router = useRouter();
  const { setUser, setTokens } = useAuthStore();

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;
    setLoading(true); setError('');
    try {
      const { data } = await authApi.requestOtp(phone.trim());
      setDevOtp(data._dev_otp || '');
      setStep('otp');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'ارسال کد تایید انجام نشد. شماره را بررسی کن.');
    } finally { setLoading(false); }
  };

  const handleVerifyOtp = async () => {
    const code = otp.join('');
    if (code.length < 6 || loading) return;
    setLoading(true); setError('');
    try {
      const { data } = await authApi.verifyOtp(phone.trim(), code);
      setTokens(data.access, data.refresh);
      setUser(data.user);
      router.push(getDashboardPath(data.user.role));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'کد تایید اشتباه است. دوباره تلاش کن.');
      setOtp(['', '', '', '', '', '']);
    } finally { setLoading(false); }
  };

  const handleOtpInput = (i: number, val: string) => {
    if (!/^\d?$/.test(val)) return;
    const next = [...otp]; next[i] = val; setOtp(next);
    if (val && i < 5) document.getElementById(`otp-${i + 1}`)?.focus();
    if (next.every(Boolean) && val) setTimeout(() => handleVerifyOtp(), 120);
  };

  return (
    <main className="page-shell auth-page">
      <Link href="/" className="logo" style={{ position: 'absolute', top: 24 }}><span className="logo-mark">ل</span> لکسارا</Link>
      <div className="hero-orb" style={{ top: '8%', right: '8%' }} />
      <section className="auth-card glass animate-fade-up">
        {step === 'phone' ? (
          <>
            <div className="section-eyebrow login-eyebrow-center">ورود امن</div>
            <h1 style={{ fontSize: '2rem' }}>ورود به حساب کاربری</h1>
            <p className="muted" style={{ margin: '10px 0 26px', lineHeight: 1.9 }}>شماره موبایل خود را وارد کن تا کد ورود یک‌بارمصرف ارسال شود.</p>
            {error && <Alert text={error} />}
            <form onSubmit={handleRequestOtp}>
              <label>شماره موبایل</label>
              <input className="input" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="مثلاً 09123456789" autoFocus />
              <button className="btn btn-gold" type="submit" disabled={loading} style={{ width: '100%', marginTop: 18 }}>
                {loading ? 'در حال ارسال...' : 'ارسال کد تایید'}
              </button>
            </form>
          </>
        ) : (
          <>
            <button className="btn btn-ghost btn-sm" onClick={() => setStep('phone')} style={{ marginBottom: 18 }}>بازگشت</button>
            <div className="section-eyebrow">تایید شماره</div>
            <h1 style={{ fontSize: '2rem' }}>کد تایید را وارد کن</h1>
            <p className="muted" style={{ margin: '10px 0 14px', lineHeight: 1.9 }}>کد ۶ رقمی برای <span className="gold">{phone}</span> ارسال شد.</p>
            {devOtp && <div className="badge badge-gold" style={{ marginBottom: 18 }}>کد توسعه: {devOtp}</div>}
            {error && <Alert text={error} />}
            <div className="otp-grid" style={{ margin: '18px 0 22px' }}>
              {otp.map((v, i) => (
                <input key={i} id={`otp-${i}`} className="input otp-input" inputMode="numeric" maxLength={1} value={v} onChange={(e) => handleOtpInput(i, e.target.value)} />
              ))}
            </div>
            <button className="btn btn-gold" onClick={handleVerifyOtp} disabled={loading || otp.join('').length < 6} style={{ width: '100%' }}>
              {loading ? 'در حال بررسی...' : 'ورود به پنل'}
            </button>
            <button className="btn btn-ghost" style={{ width: '100%', marginTop: 12 }} onClick={() => authApi.requestOtp(phone).then((r) => setDevOtp(r.data._dev_otp || ''))}>ارسال مجدد کد</button>
          </>
        )}
        <div className="muted" style={{ textAlign: 'center', marginTop: 24, fontSize: 13 }}>
          حساب نداری؟ <Link href="/register" className="gold">ثبت‌نام کن</Link>
        </div>
      </section>
    </main>
  );
}

function Alert({ text }: { text: string }) {
  return <div className="badge badge-danger" style={{ width: '100%', justifyContent: 'flex-start', marginBottom: 16 }}>{text}</div>;
}
