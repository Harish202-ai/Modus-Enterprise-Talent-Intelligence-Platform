import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import SupportBubble from "@/components/chat/SupportBubble";
import { AuthProvider } from "@/lib/auth";

import "./globals.css";

// Headings font (design system). Body text uses Satoshi via the --font-sans stack in globals.css.
const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  weight: ["600", "700"],
});

export const metadata: Metadata = {
  title: "METI-MC",
  description: "METI Management Consulting Assessment & Development Platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${jakarta.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          {children}
          <SupportBubble />
        </AuthProvider>
      </body>
    </html>
  );
}
