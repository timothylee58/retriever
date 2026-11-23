"use client";

import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const password = new FormData(event.currentTarget).get("password");
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) {
      setError("That password does not match DEMO_PASSWORD.");
      return;
    }
    window.location.href = "/";
  }

  return (
    <>
      <h1>Owner sign-in</h1>
      <form onSubmit={onSubmit}>
        <label>Shared demo password <input name="password" type="password" required /></label>
        <p><button type="submit">Enter</button></p>
      </form>
      {error ? <p>{error}</p> : null}
    </>
  );
}
