import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { getHtmlLang } from "@/lib/i18n";
import { TopNav } from "@/components/top-nav";

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
    <html lang={getHtmlLang()}>
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <TopNav />
          <main className="p-6">{children}</main>
        </div>
        <Toaster />
      </body>
    </html>
  );
}
