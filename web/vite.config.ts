import { defineConfig, loadEnv } from "vite";
import cesium from "vite-plugin-cesium";

export default defineConfig(({ mode }) => {
  loadEnv(mode, process.cwd(), "");
  return {
    plugins: [cesium()],
    server: {
      port: 5173,
      open: true,
    },
  };
});

