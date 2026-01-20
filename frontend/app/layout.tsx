import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { htmlLang, t } from "@/lib/i18n";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MeetingMod - AI Meeting Moderator",
  description: "Real-time AI meeting facilitation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang={htmlLang}>
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <header className="bg-white border-b px-6 py-4">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold">MeetingMod</h1>
              <nav className="flex gap-4">
                <a href="/" className="text-sm hover:underline">{t("nav.prepare")}</a>
                <a href="/principles" className="text-sm hover:underline">{t("nav.principles")}</a>
              </nav>
            </div>
          </header>
          <main className="p-6">{children}</main>
        </div>
        <Toaster />
      </body>
    </html>
  );
}
