import type { NextConfig } from "next";

/** Render Django API — proxied at /api/* so the browser stays same-origin (no CORS). */
const API_BACKEND_URL =
  process.env.API_BACKEND_URL?.replace(/\/$/, "") ??
  "https://toyota-assessment.onrender.com";

const nextConfig: NextConfig = {
  // Avoid 308 strip of trailing slash on /api/* — Django APPEND_SLASH adds it back (redirect loop).
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BACKEND_URL}/api/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
};

export default nextConfig;
