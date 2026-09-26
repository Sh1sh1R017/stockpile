/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  compress: true,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
