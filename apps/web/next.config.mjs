const nasApiProxyTarget = process.env.NAS_API_PROXY_TARGET?.replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@silver-voice/shared-types", "@silver-voice/ui"],
  experimental: {
    typedRoutes: false
  },
  async rewrites() {
    if (!nasApiProxyTarget) return [];

    return [
      {
        source: "/nas-api/:path*",
        destination: `${nasApiProxyTarget}/:path*`
      }
    ];
  }
};

export default nextConfig;
