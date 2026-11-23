"use client";

export function ThemeToggle() {
  return (
    <button
      className="icon-btn"
      type="button"
      aria-label="Change theme"
      onClick={() => {
        const root = document.documentElement;
        root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
      }}
    >
      Aa
    </button>
  );
}
