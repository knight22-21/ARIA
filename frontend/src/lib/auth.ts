// Lightweight client-side auth gate for the demo dashboard.
// Credentials default to admin / aria2026; override via frontend/.env.local:
//   VITE_LOGIN_USER=...  VITE_LOGIN_PASS=...
// (This is a demo gate, not production auth — there is no server-side session.)

const USER = (import.meta.env.VITE_LOGIN_USER as string) || "admin";
const PASS = (import.meta.env.VITE_LOGIN_PASS as string) || "aria2026";
const KEY = "aria_auth";

export const DEMO_USER = USER;

export function isAuthed(): boolean {
  return localStorage.getItem(KEY) === "1";
}

export function login(username: string, password: string): boolean {
  if (username === USER && password === PASS) {
    localStorage.setItem(KEY, "1");
    return true;
  }
  return false;
}

export function logout(): void {
  localStorage.removeItem(KEY);
}
