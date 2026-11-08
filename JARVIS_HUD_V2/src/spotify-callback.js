import { handleSpotifyCallback } from "./spotify.js";

if (
  window.location.pathname === "/callback" &&
  new URLSearchParams(window.location.search).has("code")
) {
  handleSpotifyCallback()
    .then(() => window.location.replace("/"))
    .catch((error) => {
      console.error("Spotify callback error:", error);
    });
}
