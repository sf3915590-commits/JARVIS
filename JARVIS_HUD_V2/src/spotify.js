const CLIENT_ID = "22cddfc3d00c4aed8693a177006d26ee";
const REDIRECT_URI = "http://127.0.0.1:5173/callback";

const SCOPES = [
  "streaming",
  "user-read-private",
  "user-read-email",
  "user-read-playback-state",
  "user-modify-playback-state",
  "user-read-currently-playing"
].join(" ");

function randomString(length = 64) {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

  const values = crypto.getRandomValues(new Uint8Array(length));

  return Array.from(values, value => chars[value % chars.length]).join("");
}

function base64url(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function sha256(value) {
  const data = new TextEncoder().encode(value);
  return crypto.subtle.digest("SHA-256", data);
}

export async function loginSpotify() {
  const verifier = randomString();
  const state = randomString(32);

  const challenge = base64url(await sha256(verifier));

  localStorage.setItem("jarvis_spotify_verifier", verifier);
  localStorage.setItem("jarvis_spotify_state", state);

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    redirect_uri: REDIRECT_URI,
    state,
    scope: SCOPES,
    code_challenge_method: "S256",
    code_challenge: challenge
  });

  window.location.href =
    "https://accounts.spotify.com/authorize?" + params.toString();
}

export async function handleSpotifyCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  const returnedState = params.get("state");

  if (!code) return false;

  const savedState =
    localStorage.getItem("jarvis_spotify_state");

  const verifier =
    localStorage.getItem("jarvis_spotify_verifier");

  if (!savedState || savedState !== returnedState || !verifier) {
    throw new Error("Spotify authorization verification failed.");
  }

  const response = await fetch(
    "https://accounts.spotify.com/api/token",
    {
      method: "POST",
      headers: {
        "Content-Type":
          "application/x-www-form-urlencoded"
      },
      body: new URLSearchParams({
        client_id: CLIENT_ID,
        grant_type: "authorization_code",
        code,
        redirect_uri: REDIRECT_URI,
        code_verifier: verifier
      })
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.error_description ||
      "Spotify token exchange failed."
    );
  }

  localStorage.setItem(
    "jarvis_spotify_access_token",
    data.access_token
  );

  if (data.refresh_token) {
    localStorage.setItem(
      "jarvis_spotify_refresh_token",
      data.refresh_token
    );
  }

  localStorage.setItem(
    "jarvis_spotify_expires_at",
    String(
      Date.now() +
      data.expires_in * 1000
    )
  );

  localStorage.removeItem(
    "jarvis_spotify_verifier"
  );

  localStorage.removeItem(
    "jarvis_spotify_state"
  );

  window.history.replaceState(
    {},
    document.title,
    "/"
  );

  return true;
}

export function getSpotifyToken() {
  return localStorage.getItem(
    "jarvis_spotify_access_token"
  );
}

export async function spotifyFetch(
  path,
  options = {}
) {
  const token = getSpotifyToken();

  if (!token) {
    throw new Error(
      "Spotify is not connected."
    );
  }

  const response = await fetch(
    "https://api.spotify.com/v1" + path,
    {
      ...options,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(options.headers || {})
      }
    }
  );

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.error?.message ||
      "Spotify API request failed."
    );
  }

  return data;
}

export async function searchSpotifyTrack(query) {
  const data = await spotifyFetch(
    "/search?type=track&limit=1&q=" +
      encodeURIComponent(query)
  );

  return data.tracks?.items?.[0] || null;
}

export async function getSpotifyPlayback() {
  return spotifyFetch("/me/player");
}

export async function playSpotifyTrack(uri) {
  return spotifyFetch("/me/player/play", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      uris: [uri]
    })
  });
}

export async function pauseSpotify() {
  return spotifyFetch("/me/player/pause", {
    method: "PUT"
  });
}

export async function nextSpotify() {
  return spotifyFetch("/me/player/next", {
    method: "POST"
  });
}

export async function previousSpotify() {
  return spotifyFetch("/me/player/previous", {
    method: "POST"
  });
}
