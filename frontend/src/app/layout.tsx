import type { Metadata, Viewport } from 'next';
import './globals.css';
import MobileBottomNav from '@/components/MobileBottomNav';


export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export const metadata: Metadata = {
  title: 'لکسارا | رزرو آنلاین وکیل',
  description: 'پلتفرم امن و سریع برای پیدا کردن و رزرو مشاوره با وکلای تاییدشده.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}<MobileBottomNav /></body>
    </html>
  );
}
