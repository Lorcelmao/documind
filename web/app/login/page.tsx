"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch, setAccessToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const body = JSON.stringify({ email, password });
      if (mode === "register") {
        const res = await apiFetch("/auth/register", { method: "POST", body });
        if (!res.ok) {
          setError((await res.json()).detail ?? "Registration failed");
          return;
        }
      }
      const res = await apiFetch("/auth/login", { method: "POST", body });
      if (!res.ok) {
        setError((await res.json()).detail ?? "Login failed");
        return;
      }
      setAccessToken((await res.json()).access_token);
      router.push("/dashboard");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="mb-6 text-2xl font-bold">
        {mode === "login" ? "Sign in" : "Create an account"}
      </h1>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Password (min 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-gray-900 px-4 py-2 text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {mode === "login" ? "Sign in" : "Register"}
        </button>
      </form>
      <button
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="mt-4 text-sm text-gray-600 underline"
      >
        {mode === "login" ? "No account yet? Register" : "Have an account? Sign in"}
      </button>
    </main>
  );
}
