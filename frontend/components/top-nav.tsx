"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getLocale, setLocale, t, type Locale } from "@/lib/i18n";

export function TopNav() {
  const [currentLocale, setCurrentLocale] = useState<Locale>(getLocale());

  useEffect(() => {
    const locale = getLocale();
    setCurrentLocale(locale);
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }, []);

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextLocale = event.target.value as Locale;
    setLocale(nextLocale);
    setCurrentLocale(nextLocale);
    if (typeof document !== "undefined") {
      document.documentElement.lang = nextLocale;
    }
    window.location.reload();
  };

  return (
    <header className="bg-white border-b px-6 py-4">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-xl font-bold">
          MeetingMod
        </Link>
        <div className="flex items-center gap-4">
          <nav className="flex gap-4">
            <Link href="/" className="text-sm hover:underline">
              {t("nav.prepare")}
            </Link>
            <Link href="/principles" className="text-sm hover:underline">
              {t("nav.principles")}
            </Link>
          </nav>
          <select
            className="rounded-md border border-gray-200 bg-white px-2 py-1 text-xs"
            value={currentLocale}
            onChange={handleChange}
            aria-label="Language"
          >
            <option value="ko">한국어</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
    </header>
  );
}
