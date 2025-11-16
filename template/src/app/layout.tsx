import type { Metadata } from "next";
import { Plus_Jakarta_Sans, DM_Serif_Display } from "next/font/google";
import "./globals.css";
// import { Nav } from "@/components/ui/Nav";

// Font setup: Jakarta for UI, DM Serif Display for expressive headings
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-sans" });
const dmSerif = DM_Serif_Display({ weight: "400", subsets: ["latin"], variable: "--font-heading" });

export const metadata: Metadata = {
  title: "Landing Page Template - Your Product Tagline",
  description:
    "Describe your product value prop in one or two sentences. Mention the core outcome and who it serves.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="bg-background" suppressHydrationWarning>
      <body className={`${jakarta.variable} ${dmSerif.variable} antialiased min-h-dvh bg-background text-foreground`}>
        {/* Compact, unobtrusive navigation. No global padding. */}
        {/* <Nav /> */}
        {children}
      </body>
    </html>
  );
}
