"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";
import { forgetReviewToken, getReviewToken, setReviewToken } from "@/lib/api";

const REQUIRED = process.env.NEXT_PUBLIC_REVIEW_TOKEN_REQUIRED === "true";

export default function ReviewAccessGate({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getReviewToken());
  const [value, setValue] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const invalid = () => { forgetReviewToken(); setToken(null); setMessage("That review token was rejected."); };
    const changed = () => setToken(getReviewToken());
    window.addEventListener("corpus-review-token-invalid", invalid);
    window.addEventListener("corpus-review-token-changed", changed);
    return () => { window.removeEventListener("corpus-review-token-invalid", invalid); window.removeEventListener("corpus-review-token-changed", changed); };
  }, []);

  if (!REQUIRED) return <>{children}</>;
  if (!token) {
    function submit(event: FormEvent<HTMLFormElement>) {
      event.preventDefault();
      const next = value.trim();
      if (!next) { setMessage("Enter the reviewer access token."); return; }
      setReviewToken(next); setToken(next); setValue(""); setMessage(null);
    }
    return <main style={{ maxWidth: 560, margin: "8rem auto", padding: "2rem", fontFamily: "system-ui" }}>
      <h1>Corpus review access</h1>
      <p>Enter the reviewer token supplied with this POC deployment. It is kept only in this browser session.</p>
      <form onSubmit={submit}>
        <label style={{ display: "grid", gap: ".4rem" }}><span>Review token</span><input autoFocus type="password" value={value} onChange={(event) => setValue(event.target.value)} style={{ padding: ".7rem" }} /></label>
        <button type="submit" style={{ marginTop: "1rem", padding: ".7rem 1rem" }}>Continue</button>
      </form>
      {message && <p role="alert">{message}</p>}
    </main>;
  }

  return <>
    <div role="note" style={{ padding: "0.45rem 1rem", background: "#fff7ed", color: "#7c2d12", borderBottom: "1px solid #fed7aa", fontSize: "0.85rem", textAlign: "center" }}>
      Free-tier review deployment: the backend may sleep; the first request can take a moment to wake it.
    </div>
    {children}
    <div style={{ position: "fixed", bottom: 12, right: 12, zIndex: 10 }}><button type="button" onClick={() => { forgetReviewToken(); setToken(null); }}>Forget review token</button></div>
  </>;
}
