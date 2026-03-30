import type { Metadata } from "next";
import { Fraunces, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

const fontDisplay = Fraunces({ subsets: ["latin"], variable: "--font-display", display: "swap" });
const fontBody = DM_Sans({ subsets: ["latin"], variable: "--font-body", display: "swap" });
const fontMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "CuraSource | Medical & Fitness AI",
  description: "Grounded RAG Assistant for Medical and Fitness Professionals",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fontDisplay.variable} ${fontBody.variable} ${fontMono.variable}`}>
      <body className="font-body antialiased bg-[#FAFAF9] text-stone-800 overflow-hidden">
        <div className="flex h-screen w-full">
          
          {/* Desktop Sidebar - Hidden on mobile, visible on medium screens and up */}
          <div className="hidden md:flex h-full">
            <Sidebar />
          </div>

          <main className="flex-1 relative overflow-hidden bg-white shadow-[-4px_0_24px_-12px_rgba(0,0,0,0.05)]">
            {children}
          </main>
          
        </div>
      </body>
    </html>
  );
}