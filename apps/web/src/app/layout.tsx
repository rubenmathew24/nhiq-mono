import type { Metadata } from "next";
import { DM_Sans, Space_Grotesk } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "NeighborhoodIQ — Know your neighborhood before you buy",
  description:
    "AI-powered neighborhood intelligence for U.S. home buyers. Healthcare, safety, environment, schools, and economy — scored for any address.",
  openGraph: {
    title: "NeighborhoodIQ — Know your neighborhood before you buy",
    description:
      "AI-powered neighborhood intelligence for home buyers. Score any U.S. address on healthcare, safety, environment, schools, and economy.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${dmSans.variable} ${spaceGrotesk.variable} h-full antialiased`}
    >
      <body className="min-h-full font-sans">
          <Providers>{children}</Providers>
        </body>
    </html>
  );
}
