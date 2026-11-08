import React, { useEffect, useRef } from "react";
import {
  loginSpotify,
  getSpotifyToken,
  searchSpotifyTrack,
  getSpotifyPlayback,
  playSpotifyTrack,
  pauseSpotify,
  nextSpotify,
  previousSpotify
} from "./spotify.js";

let sdkPromise = null;

function loadSpotifySDK() {
  if (window.Spotify) return Promise.resolve(window.Spotify);
  if (sdkPromise) return sdkPromise;

  sdkPromise = new Promise((resolve, reject) => {
    window.onSpotifyWebPlaybackSDKReady = () => {
      resolve(window.Spotify);
    };

    const script = document.createElement("script");
    script.src = "https://sdk.scdn.co/spotify-player.js";
    script.async = true;
    script.onerror = () =>
      reject(new Error("Spotify Web Playback SDK load failed."));

    document.head.appendChild(script);
  });

  return sdkPromise;
}

export default function SpotifyBridge({
  frameRef,
  musicState
}) {
  const playerRef = useRef(null);
  const deviceRef = useRef(null);
  const lastQuery = useRef("");
  const stateRef = useRef(null);

  const post = (data) => {
    const frame = frameRef?.current;

    if (!frame?.contentWindow) return;

    frame.contentWindow.postMessage(
      data,
      "*"
    );
  };

  const sendState = (state) => {
    if (!state?.track_window?.current_track) return;

    const track =
      state.track_window.current_track;

    stateRef.current = state;

    post({
      type: "JARVIS_SPOTIFY_STATE",
      title: track.name || "Unknown Track",
      artist:
        track.artists
          ?.map((a) => a.name)
          .join(", ") || "Unknown Artist",
      albumArt:
        track.album?.images?.[0]?.url || "",
      position: state.position || 0,
      duration: state.duration || 0,
      playing: !state.paused,
      status: state.paused
        ? "Spotify Music Mode · PAUSED"
        : "Spotify Music Mode · PLAYING"
    });
  };

  const connectPlayer = async () => {
    if (playerRef.current) {
      return playerRef.current;
    }

    if (!getSpotifyToken()) {
      await loginSpotify();
      return null;
    }

    const Spotify = await loadSpotifySDK();

    return new Promise((resolve, reject) => {
      const player = new Spotify.Player({
        name: "JARVIS Music HUD",
        volume: 0.85,

        getOAuthToken: async (cb) => {
          const token = getSpotifyToken();

          if (!token) {
            await loginSpotify();
            return;
          }

          cb(token);
        }
      });

      player.addListener(
        "ready",
        async ({ device_id }) => {
          deviceRef.current = device_id;
          playerRef.current = player;

          try {
            await fetch(
              "https://api.spotify.com/v1/me/player",
              {
                method: "PUT",
                headers: {
                  Authorization:
                    `Bearer ${getSpotifyToken()}`,
                  "Content-Type":
                    "application/json"
                },
                body: JSON.stringify({
                  device_ids: [device_id],
                  play: false
                })
              }
            );
          } catch (e) {
            console.warn(
              "Spotify device transfer:",
              e
            );
          }

          post({
            type: "JARVIS_SPOTIFY_MODE",
            active: true
          });

          resolve(player);
        }
      );

      player.addListener(
        "player_state_changed",
        (state) => {
          if (state) sendState(state);
        }
      );

      player.addListener(
        "initialization_error",
        ({ message }) =>
          reject(new Error(message))
      );

      player.addListener(
        "authentication_error",
        ({ message }) =>
          reject(new Error(message))
      );

      player.addListener(
        "account_error",
        ({ message }) =>
          reject(new Error(message))
      );

      player.connect();
    });
  };

  const playRequestedTrack = async (query) => {
    const player = await connectPlayer();

    if (!player) return;

    const clean =
      String(query || "").trim();

    if (
      !clean ||
      clean.toLowerCase() ===
        "jarvis music" ||
      clean.toLowerCase() ===
        "jarvis music system"
    ) {
      await player.resume();
      return;
    }

    if (lastQuery.current === clean) {
      await player.resume();
      return;
    }

    lastQuery.current = clean;

    const track =
      await searchSpotifyTrack(clean);

    if (!track) {
      post({
        type: "JARVIS_SPOTIFY_STATE",
        status:
          `Spotify: "${clean}" not found`
      });
      return;
    }

    await playSpotifyTrack(
      track.uri
    );
  };

  useEffect(() => {

    if (!frame) return;

    const onMessage = async (event) => {
      if (
        event.source !==
        frame.contentWindow
      ) {
        return;
      }

      const data =
        event.data || {};

      if (
        data.type !==
        "JARVIS_SPOTIFY_CONTROL"
      ) {
        return;
      }

      try {
        const player =
          await connectPlayer();

        if (!player) return;

        switch (data.command) {
          case "play":
            await player.resume();
            break;

          case "pause":
            await player.pause();
            break;

          case "next":
            await player.nextTrack();
            break;

          case "previous":
            await player.previousTrack();
            break;

          case "stop":
            await player.pause();
            break;

          case "volume":
            await player.setVolume(
              Number(data.value || 0.85)
            );
            break;

          default:
            break;
        }
      } catch (error) {
        console.error(
          "Spotify control:",
          error
        );
      }
    };

    window.addEventListener(
      "message",
      onMessage
    );

    const frame = frameRef?.current;
    const announceSpotifyMode = () => {
      post({
        type: "JARVIS_SPOTIFY_MODE",
        active: true
      });
    };

    if (frame) {
      if (frame.contentDocument?.readyState === "complete") {
        announceSpotifyMode();
      } else {
        frame.addEventListener("load", announceSpotifyMode, { once: true });
      }
    }

    connectPlayer().catch(
      console.error
    );

    return () => {
      window.removeEventListener(
        "message",
        onMessage
      );
    };
  }, []);

  useEffect(() => {
    if (!musicState) return;

    if (
      musicState.playing &&
      musicState.title
    ) {
      playRequestedTrack(
        musicState.title
      ).catch(console.error);
    }
  }, [
    musicState?.title,
    musicState?.playing
  ]);

  useEffect(() => {
    const timer =
      setInterval(() => {
        const state =
          stateRef.current;

        if (!state || state.paused) {
          return;
        }

        const elapsed =
          Date.now() -
          (state.__jarvisTime || Date.now());

        const position = Math.min(
          state.duration,
          state.position + elapsed
        );

        post({
          type: "JARVIS_SPOTIFY_STATE",
          title:
            state.track_window
              ?.current_track?.name,
          artist:
            state.track_window
              ?.current_track?.artists
              ?.map((a) => a.name)
              .join(", "),
          albumArt:
            state.track_window
              ?.current_track?.album
              ?.images?.[0]?.url || "",
          position,
          duration: state.duration,
          playing: true,
          status:
            "Spotify Music Mode · PLAYING"
        });
      }, 500);

    return () =>
      clearInterval(timer);
  }, []);

  return null;
}


