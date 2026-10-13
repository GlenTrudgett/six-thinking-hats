import type { NextConfig } from "next";

// The browser talks only to this Next server; /api is forwarded to the Python API.
// The model key lives with the Python API and never reaches the browser.
const API_URL = process.env.SIXHATS_API_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default config;
