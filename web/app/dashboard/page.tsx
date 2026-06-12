"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { apiFetch, refreshSession, setAccessToken } from "@/lib/api";

type Workspace = { id: string; name: string; role: string };

export default function DashboardPage() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [name, setName] = useState("");

  const loadWorkspaces = useCallback(async () => {
    const res = await apiFetch("/workspaces");
    if (res.ok) setWorkspaces(await res.json());
  }, []);

  useEffect(() => {
    (async () => {
      // recover the session from the refresh cookie on page load
      if (!(await refreshSession())) {
        router.replace("/login");
        return;
      }
      const me = await apiFetch("/auth/me");
      if (me.ok) setEmail((await me.json()).email);
      await loadWorkspaces();
    })();
  }, [router, loadWorkspaces]);

  async function createWorkspace(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const res = await apiFetch("/workspaces", {
      method: "POST",
      body: JSON.stringify({ name: name.trim() }),
    });
    if (res.ok) {
      setName("");
      await loadWorkspaces();
    }
  }

  async function logout() {
    await apiFetch("/auth/logout", { method: "POST" });
    setAccessToken(null);
    router.replace("/login");
  }

  if (email === null) {
    return <main className="p-8 text-gray-500">Loading...</main>;
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workspaces</h1>
          <p className="text-sm text-gray-600">{email}</p>
        </div>
        <button onClick={logout} className="text-sm text-gray-600 underline">
          Sign out
        </button>
      </div>

      <form onSubmit={createWorkspace} className="mb-6 flex gap-2">
        <input
          placeholder="New workspace name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded-md border border-gray-300 px-3 py-2"
        />
        <button type="submit" className="rounded-md bg-gray-900 px-4 py-2 text-white">
          Create
        </button>
      </form>

      <ul className="flex flex-col gap-2">
        {workspaces.map((ws) => (
          <li
            key={ws.id}
            className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3"
          >
            <span>{ws.name}</span>
            <span className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600">{ws.role}</span>
          </li>
        ))}
        {workspaces.length === 0 && (
          <li className="text-sm text-gray-500">No workspaces yet. Create one above.</li>
        )}
      </ul>
    </main>
  );
}
