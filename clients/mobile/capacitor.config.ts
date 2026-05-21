import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.carlos.laboratorio",
  appName: "Laboratorio",
  webDir: "../web/dist",
  server: {
    androidScheme: "https",
  },
};

export default config;
