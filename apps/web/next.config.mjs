/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@silver-voice/shared-types", "@silver-voice/ui"],
  experimental: {
    typedRoutes: false
  }
};

export default nextConfig;

