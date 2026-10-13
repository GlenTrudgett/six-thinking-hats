import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Six Thinking Hats",
  description: "Think a question through with de Bono's six hats.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
