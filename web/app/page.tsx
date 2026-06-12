import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-4xl font-bold">DocuMind</h1>
      <p className="text-gray-600">
        Upload your documents, ask questions, get answers with citations to the source.
      </p>
      <Link
        href="/login"
        className="rounded-md bg-gray-900 px-5 py-2 text-white hover:bg-gray-700"
      >
        Sign in
      </Link>
    </main>
  );
}
