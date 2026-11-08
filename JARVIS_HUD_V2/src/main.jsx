import React from "react";
import { createRoot } from "react-dom/client";
import App from "./Core.jsx";
import "./hud.css";
import MobileCompanion from "./MobileCompanion.jsx";

const isJarvisMobile = new URLSearchParams(window.location.search).get("mobile") === "1";
if (isJarvisMobile) {
  const manifest = document.createElement("link");
  manifest.rel = "manifest";
  manifest.href = "/jarvis.webmanifest";
  document.head.appendChild(manifest);

  const appleIcon = document.createElement("link");
  appleIcon.rel = "apple-touch-icon";
  appleIcon.href = "/jarvis-icon-180.png";
  document.head.appendChild(appleIcon);

  const appleCapable = document.createElement("meta");
  appleCapable.name = "apple-mobile-web-app-capable";
  appleCapable.content = "yes";
  document.head.appendChild(appleCapable);

  const theme = document.createElement("meta");
  theme.name = "theme-color";
  theme.content = "#030811";
  document.head.appendChild(theme);

  document.documentElement.classList.add("jarvis-mobile-pwa");

}

createRoot(document.getElementById("root")).render(isJarvisMobile ? <MobileCompanion /> : <App />);

