import type { Metadata } from "next";
import ReviewAccessGate from "@/components/corpus/ReviewAccessGate";
import "./globals.css";

export const metadata: Metadata = {
  title: "Corpus",
  description: "Durable custodian-scoped corpus register and processing monitor.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body><ReviewAccessGate>{children}</ReviewAccessGate></body>
    </html>
  );
}
