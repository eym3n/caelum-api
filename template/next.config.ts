import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'builder-agent.storage.googleapis.com',
      },
    ],
  },
};

export default nextConfig;
