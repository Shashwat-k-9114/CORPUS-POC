import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Corpus",
  description: "Document-understanding prototype: upload a PDF, inspect its extraction and provenance.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
