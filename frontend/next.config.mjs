/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: [
      "127.0.0.1",
      "localhost",
      "www.hidelifestyle.co.uk",
      "www.hidelifestyle.au",
      "api.hidelifestyle.co.uk",
      "www.test4.wardah.in",
      "api.test4.wardah.in",
      "api.iconperfumes.in",
    ], // Add your hostname here
  },
  env: {
    API_URL: process.env.API_URL,
    IMAGE_URL: process.env.IMAGE_URL,
    PAYMENT_SECRET: process.env.PAYMENT_SECRET,
    COOKIE_SECRET: process.env.COOKIE_SECRET,
    STRIPE_KEY: process.env.STRIPE_KEY,
    STRAPI_API: process.env.STRAPI_API,
    BANNER_IMAGE_URL: process.env.BANNER_IMAGE_URL,
    DOMAIN: process.env.DOMAIN
  },
  trailingSlash: true,
  experimental: {
    serverActions: {
      allowedOrigins: ["secure.payu.in", "www.iconperfumes.in"],
    },
  },
};

export default nextConfig;
