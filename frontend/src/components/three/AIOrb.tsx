"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial, Icosahedron, Sphere } from "@react-three/drei";
import * as THREE from "three";

function Core() {
  const group = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.18;
  });

  const nodes = useMemo(() => {
    const out: { pos: [number, number, number]; c: string; s: number }[] = [];
    const palette = ["#7b6ef6", "#4f9cff", "#ff7eb6", "#2fd6ac", "#ffb27a"];
    for (let i = 0; i < 14; i++) {
      const phi = Math.acos(-1 + (2 * i) / 14);
      const theta = Math.sqrt(14 * Math.PI) * phi;
      const r = 2.15;
      out.push({ pos: [r * Math.cos(theta) * Math.sin(phi), r * Math.sin(theta) * Math.sin(phi), r * Math.cos(phi)], c: palette[i % palette.length], s: 0.06 + (i % 3) * 0.02 });
    }
    return out;
  }, []);

  return (
    <group ref={group}>
      <Icosahedron args={[1.35, 6]}>
        <MeshDistortMaterial color="#8b7bff" emissive="#4f9cff" emissiveIntensity={0.35} roughness={0.15} metalness={0.35} distort={0.38} speed={1.6} />
      </Icosahedron>
      <Icosahedron args={[1.9, 2]}>
        <meshBasicMaterial color="#a99bff" wireframe transparent opacity={0.18} />
      </Icosahedron>
      {nodes.map((n, i) => (
        <group key={i} position={n.pos}>
          <Sphere args={[n.s, 16, 16]}>
            <meshStandardMaterial color={n.c} emissive={n.c} emissiveIntensity={0.6} roughness={0.3} />
          </Sphere>
        </group>
      ))}
    </group>
  );
}

export default function AIOrb({ className }: { className?: string }) {
  return (
    <div className={className}>
      <Canvas camera={{ position: [0, 0, 6], fov: 45 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.7} />
        <pointLight position={[6, 6, 6]} intensity={1.1} color="#ffffff" />
        <pointLight position={[-6, -4, 2]} intensity={0.8} color="#ff7eb6" />
        <Float speed={1.3} rotationIntensity={0.5} floatIntensity={0.9}>
          <Core />
        </Float>
      </Canvas>
    </div>
  );
}
