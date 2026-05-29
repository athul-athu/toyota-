/** Base URL for the Django backend (Supabase is accessed only from the server). */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
