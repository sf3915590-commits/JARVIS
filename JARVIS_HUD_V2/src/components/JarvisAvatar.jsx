import React, { useEffect, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { Float, Sparkles, useGLTF } from "@react-three/drei";

const MODEL = "/jarvis_avatar/Superhero_Male_FullBody.gltf";

function HumanModel({ state = "idle" }) {
  const root = useRef();
  const { scene } = useGLTF(MODEL);

  useEffect(() => {
    scene.traverse((obj) => {
      if (obj.isMesh) {
        obj.castShadow = true;
        obj.receiveShadow = true;

        if (obj.material) {
          obj.material.metalness = 0.25;
          obj.material.roughness = 0.32;
        }
      }
    });

    // JARVIS relaxed standing pose.
    // The GLTF has a 65-bone skeleton, so pose the existing bones directly.
    const bones = {};

    scene.traverse((obj) => {
      if (obj.isBone && obj.name) {
        bones[obj.name] = obj;
      }
    });

    // Shoulders / upper arms: bring both arms down from T-pose.
    if (bones.clavicle_l) bones.clavicle_l.rotation.z = -0.10;
    if (bones.clavicle_r) bones.clavicle_r.rotation.z = 0.10;

    if (bones.upperarm_l) bones.upperarm_l.rotation.z = -1.15;
    if (bones.upperarm_r) bones.upperarm_r.rotation.z = 1.15;

    // Slight natural elbow bend.
    if (bones.lowerarm_l) bones.lowerarm_l.rotation.z = -0.12;
    if (bones.lowerarm_r) bones.lowerarm_r.rotation.z = 0.12;

    // Relax the hands.
    if (bones.hand_l) bones.hand_l.rotation.z = -0.05;
    if (bones.hand_r) bones.hand_r.rotation.z = 0.05;

    // Slight natural head/neck orientation.
    if (bones.neck_01) bones.neck_01.rotation.x = 0.02;
    if (bones.Head) bones.Head.rotation.x = -0.03;
  }, [scene]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (!root.current) return;

      const t = performance.now() * 0.001;

      if (state === "idle") {
        root.current.position.y = Math.sin(t * 1.8) * 0.012;
        root.current.rotation.y = Math.sin(t * 0.55) * 0.035;
      }

      if (state === "thinking") {
        root.current.position.y = Math.sin(t * 2.5) * 0.02;
        root.current.rotation.y = Math.sin(t * 1.2) * 0.07;
      }

      if (state === "speaking") {
        root.current.position.y = Math.sin(t * 6) * 0.015;
      }

      if (state === "success") {
        root.current.position.y = Math.abs(Math.sin(t * 4)) * 0.04;
      }
    }, 16);

    return () => clearInterval(timer);
  }, [state]);

  return (
    <group
      ref={root}
      position={[0, -1.48, 0]}
      rotation={[0, 0, 0]}
      scale={1.02}
    >
      <primitive object={scene} />

      {/* JARVIS chest reactor */}
      <mesh position={[0, 1.27, 0.42]}>
        <sphereGeometry args={[0.045, 24, 24]} />
        <meshStandardMaterial
          color="#bffaff"
          emissive="#00d9ff"
          emissiveIntensity={8}
          toneMapped={false}
        />
      </mesh>

      {/* Chest energy ring */}
      <mesh position={[0, 1.27, 0.415]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.075, 0.009, 12, 32]} />
        <meshStandardMaterial
          color="#62efff"
          emissive="#00cfff"
          emissiveIntensity={6}
          toneMapped={false}
        />
      </mesh>

      {/* Head HUD sensor */}
      <mesh position={[0, 1.73, 0.47]}>
        <sphereGeometry args={[0.035, 20, 20]} />
        <meshStandardMaterial
          color="#dfffff"
          emissive="#18d9ff"
          emissiveIntensity={7}
          toneMapped={false}
        />
      </mesh>

      {state === "clicking" && (
        <mesh position={[0.7, 1.2, 0.35]}>
          <torusGeometry args={[0.13, 0.012, 12, 40]} />
          <meshStandardMaterial
            color="#70efff"
            emissive="#13cfff"
            emissiveIntensity={7}
            toneMapped={false}
          />
        </mesh>
      )}

      {state === "success" && (
        <mesh position={[0, 1.2, 0]}>
          <torusGeometry args={[0.72, 0.01, 8, 64]} />
          <meshStandardMaterial
            color="#70efff"
            emissive="#13cfff"
            emissiveIntensity={5}
            transparent
            opacity={0.8}
            toneMapped={false}
          />
        </mesh>
      )}
    </group>
  );
}

useGLTF.preload(MODEL);

export default function JarvisAvatar({
  state = "idle",
  width = 170,
  height = 205
}) {
  return (
    <div
      style={{
        width,
        height,
        background: "transparent",
        pointerEvents: "none"
      }}
    >
      <Canvas
        camera={{
          position: [0, 1.05, 6.2],
          fov: 32
        }}
        gl={{
          alpha: true,
          antialias: true
        }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={1.35} />

        <directionalLight
          position={[3, 5, 4]}
          intensity={2.8}
        />

        <directionalLight
          position={[-3, 2, 2]}
          intensity={1.4}
        />

        <pointLight
          position={[0, 2, 2]}
          intensity={4}
          distance={7}
        />

        <pointLight
          position={[0, 0, -1]}
          intensity={1.5}
          distance={5}
        />

        <Float
          speed={state === "thinking" ? 2 : 1}
          rotationIntensity={0.04}
          floatIntensity={0.08}
        >
          <HumanModel state={state} />
        </Float>

        <Sparkles
          count={28}
          scale={[2, 3, 1.8]}
          size={0.8}
          speed={0.3}
        />
      </Canvas>
    </div>
  );
}

