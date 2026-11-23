"use client";

import { FormEvent, useState } from "react";

const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function InvoicesPage() {
  const [result, setResult] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const due = new Date();
    due.setDate(due.getDate() + 7);
    const response = await fetch(`${base}/api/invoices`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: form.get("customer_name"),
        ref: form.get("ref"),
        amount_minor: Math.round(Number(form.get("amount")) * 100),
        currency: "SGD",
        due_at: due.toISOString(),
      }),
    });
    setResult(await response.text());
  }

  return (
    <>
      <h1>New invoice</h1>
      <form onSubmit={onSubmit}>
        <label>Customer <input name="customer_name" required /></label>
        <label>Reference <input name="ref" defaultValue="INV-104" required /></label>
        <label>Amount (SGD) <input name="amount" type="number" step="0.01" defaultValue="420.00" required /></label>
        <p><button type="submit">Create payment request</button></p>
      </form>
      {result ? <pre>{result}</pre> : null}
    </>
  );
}
