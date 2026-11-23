import type { ReactNode } from "react";
import { ThemeToggle } from "../../components/theme-toggle";

const links = [
  ["/dashboard", "Overview"],
  ["/queue", "Queue"],
  ["/invoices", "Invoices"],
  ["/rescues", "Rescues"],
  ["/audit", "Audit"],
];

export default function DeskLayout({ children }: { children: ReactNode }) {
  return (
    <div className="desk">
      <aside className="side">
        <a className="wordmark" href="/">Retriever</a>
        {links.map(([href, label]) => (
          <a key={href} href={href}>
            {label}
            {label === "Queue" ? <span className="count">1</span> : null}
          </a>
        ))}
        <div style={{ marginTop: "auto" }}>
          <ThemeToggle />
        </div>
      </aside>
      <div className="desk-main">{children}</div>
    </div>
  );
}
