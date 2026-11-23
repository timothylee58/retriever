import type { ReactNode } from "react";

export default function DeskLayout({ children }: { children: ReactNode }) {
  return (
    <main>
      <nav>
        <a href="/">Overview</a>
        <a href="/invoices">Invoices</a>
        <a href="/queue">Queue</a>
        <a href="/rescues">Rescues</a>
        <a href="/audit">Audit</a>
      </nav>
      {children}
    </main>
  );
}
