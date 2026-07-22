import type { NextConfig } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const nextConfig: NextConfig = {
  allowedDevOrigins: ["matthew-arvidson.com", "snie-demo.matthew-arvidson.com"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
