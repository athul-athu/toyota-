import type { NextConfig } from "next";

/** Where Next.js rewrites /api/* (server-side proxy — no browser CORS). */
function apiRewriteTarget(): string {
  const raw =
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    process.env.API_URL?.trim() ||
    "https://toyota-assessment.onrender.com";
  return raw.replace(/\/+$/, "").replace(/\/api$/i, "");
}

const nextConfig: NextConfig = {
  // Django uses APPEND_SLASH=False; don't redirect /api/foo → /api/foo/
  skipTrailingSlashRedirect: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  async rewrites() {
    const target = apiRewriteTarget();
    return [
      {
        source: "/api/:path*",
        destination: `${target}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
