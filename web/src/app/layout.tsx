import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocAssist - Book Doctor Appointments",
  description: "Find and book appointments with top doctors. Simple, fast, and convenient.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
