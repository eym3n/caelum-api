/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'builder-agent.storage.googleapis.com',
        pathname: '/assets/**',
      },
    ],
  },
};

module.exports = nextConfig;

