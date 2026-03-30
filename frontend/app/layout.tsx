import type { Metadata } from "next";
import { Fraunces, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

const fontDisplay = Fraunces({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const fontBody = DM_Sans({ subsets: ["latin"], variable: "--font-body", display: "swap" });
const fontMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CuraSource | Medical & Fitness AI",
  description: "Grounded RAG Assistant for Medical and Fitness Professionals",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${fontDisplay.variable} ${fontBody.variable} ${fontMono.variable}`}>
      <body className="font-body antialiased bg-[#212121] text-stone-100 overflow-hidden">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
