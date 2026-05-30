import type { NextConfig } from "next";

const API_PATH_PREFIX = "/api";

function backendOrigin(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) return "http://localhost:8000";
  return raw.replace(/\/+$/, "").replace(/\/api$/i, "");
}

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = backendOrigin();
    return [
      {
        source: "/api/:path*",
        destination: `${backend}${API_PATH_PREFIX}/:path*`,
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
