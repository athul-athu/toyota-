import type { NextConfig } from "next";

const API_PATH = "/api";

function renderBackend(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!raw) return "http://localhost:8000";
  return raw.replace(/\/+$/, "").replace(/\/api$/i, "");
}

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = renderBackend();
    return [
      {
        source: "/api/:path*",
        destination: `${backend}${API_PATH}/:path*`,
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
