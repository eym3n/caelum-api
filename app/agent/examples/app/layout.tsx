import type { Metadata } from "next";
import { Nunito, Lato } from "next/font/google";
import "./globals.css";
import { twMerge } from "tailwind-merge";

const nunito = Nunito({ 
  subsets: ["latin"],
  weight: ["700"],
  variable: "--font-nunito",
  display: "swap",
});

const lato = Lato({ 
  subsets: ["latin"],
  weight: ["400", "700"], // Added 700 for bold body text if needed, safe fallback
  variable: "--font-lato",
  display: "swap",
});

export const metadata: Metadata = {
  title: "MatchMe | Find Your Perfect Match Today",
  description: "MatchMe: Find your perfect match with advanced compatibility algorithms. A safe, romantic, and exciting online dating app.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="relative">
      <body className={twMerge(nunito.variable, lato.variable, "antialiased bg-[#18181B] text-zinc-200 font-sans")}>{children}</body>
    </html>
  );
}