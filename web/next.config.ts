import type { NextConfig } from "next";

// The browser talks only to this Next server; /api is forwarded to the Python API.
// The model key lives with the Python API and never reaches the browser.
const API_URL = process.env.SIXHATS_API_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  // A run can take minutes and is streamed. Next's rewrite proxy cuts a response after 30 seconds by
  // default, which showed up as "Error in input stream". Allow 15 minutes.
  experimental: { proxyTimeout: 15 * 60 * 1000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default config;
