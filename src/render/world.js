// Loads the Blender-exported world GLB, applies the Canal District viewer's material treatment
// (water, foliage sway, instancing collapse) and extracts the static collision triangles.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { TriGrid, WALK, SHOT } from "../sim/grid.js";

export const uTime = { value: 0 };
const FOLIAGE = /^(leaf_|palm_frond|grass)/;
const NOSOLID = /^(leaf_|palm_frond|grass|water|patchwork|rope|lamp_glow|hill|distant|copper_far|cypress)/;
const SHOT_ONLY = /^awning_/;

export function setupScene(renderer, meta) {
  const scene = new THREE.Scene();
  const SUN = new THREE.Vector3(...meta.sun_dir).normalize();
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { sunDir: { value: SUN } },
    vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); gl_Position.z = gl_Position.w; }`,
    fragmentShader: `varying vec3 vDir; uniform vec3 sunDir;
      void main(){
        float h = clamp(vDir.y, -0.2, 1.0);
        vec3 zenith = vec3(0.30, 0.42, 0.60), horizon = vec3(0.93, 0.78, 0.64), ground = vec3(0.55, 0.47, 0.38);
        vec3 c = mix(horizon, zenith, pow(max(h, 0.0), 0.55));
        c = mix(c, ground, smoothstep(0.0, -0.15, h));
        float s = max(dot(normalize(vDir), sunDir), 0.0);
        c += vec3(1.0, 0.72, 0.42) * (pow(s, 24.0) * 0.28 + pow(s, 4000.0) * 2.5);
        gl_FragColor = vec4(c, 1.0);
      }`,
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(1500, 32, 16), skyMat);
  sky.frustumCulled = false;
  scene.add(sky);
  const pm = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  envScene.add(new THREE.Mesh(new THREE.SphereGeometry(100, 32, 16), skyMat));
  scene.environment = pm.fromScene(envScene, 0.02).texture;
  scene.environmentIntensity = 0.55;
  scene.fog = new THREE.FogExp2(0xd9b998, 0.0028);
  const sun = new THREE.DirectionalLight(0xffc690, 3.1);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -45, right: 45, top: 45, bottom: -45, near: 10, far: 220 });
  sun.shadow.bias = -0.0005;
  sun.shadow.normalBias = 0.04;
  scene.add(sun, sun.target);
  scene.add(new THREE.HemisphereLight(0x9fb2cc, 0x7a5a3c, 1.0));
  const followSun = (p) => {
    sun.target.position.copy(p);
    sun.position.copy(p).addScaledVector(SUN, 110);
    sun.target.updateMatrixWorld();
  };
  return { scene, sky, sun, followSun, SUN };
}

function makeWaterNormal(n = 256) {
  const d = new Uint8Array(n * n * 4);
  const h = new Float32Array(n * n);
  const waves = [];
  let s = 7;
  const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 24; i++) waves.push([1 + (i * 7) % 9, (i * 5) % 7 - 3, r() * 6.28, 1 / (1 + i * 0.35)]);
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    let v = 0;
    for (const [kx, ky, ph, a] of waves) v += a * Math.sin(6.2832 * (kx * x + ky * y) / n + ph);
    h[y * n + x] = v;
  }
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const dx = h[y * n + (x + 1) % n] - h[y * n + (x - 1 + n) % n];
    const dy = h[((y + 1) % n) * n + x] - h[((y - 1 + n) % n) * n + x];
    const l = Math.hypot(dx * 0.35, dy * 0.35, 1);
    const i = 4 * (y * n + x);
    d[i] = 128 + 127 * (-dx * 0.35 / l); d[i + 1] = 128 + 127 * (-dy * 0.35 / l); d[i + 2] = 255 / l; d[i + 3] = 255;
  }
  const t = new THREE.DataTexture(d, n, n);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter;
  t.needsUpdate = true;
  return t;
}

const swayChunk = `#include <begin_vertex>
  {
    vec4 org = vec4(0.0, 0.0, 0.0, 1.0);
    #ifdef USE_INSTANCING
      org = instanceMatrix * org;
    #endif
    org = modelMatrix * org;
    float ph = org.x * 0.37 + org.z * 0.23;
    float k = clamp(position.y, 0.0, 6.0) * 0.012 + 0.006;
    transformed.x += sin(uTime * 1.35 + ph + position.y * 0.9) * k * 2.2;
    transformed.z += cos(uTime * 1.1 + ph * 1.3 + position.x * 0.8) * k * 1.8;
  }`;

export async function loadWorld(url, scene, onProgress) {
  const gltf = await new Promise((res, rej) => new GLTFLoader().load(url, res,
    (e) => { if (e.total) onProgress?.(e.loaded / e.total); }, rej));
  const root = gltf.scene;
  scene.add(root);
  root.updateMatrixWorld(true);
  let airship = null;
  root.traverse((o) => { if (o.name === "Airship") airship = o; });
  const inAirship = (o) => { for (let p = o; p; p = p.parent) if (p === airship) return true; return false; };

  const waterMat = new THREE.MeshStandardMaterial({ color: 0x2f7d78, roughness: 0.06, metalness: 0.0,
    transparent: true, opacity: 0.9, normalMap: makeWaterNormal(), normalScale: new THREE.Vector2(0.55, 0.55) });
  waterMat.onBeforeCompile = (s) => {
    s.uniforms.uTime = uTime;
    s.fragmentShader = "uniform float uTime;\n" + s.fragmentShader.replace(
      "vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;",
      `vec3 n1 = texture2D( normalMap, vNormalMapUv * 0.22 + uTime * vec2(0.011, 0.019) ).xyz * 2.0 - 1.0;
       vec3 n2 = texture2D( normalMap, vNormalMapUv * 0.53 + uTime * vec2(-0.017, 0.007) ).xyz * 2.0 - 1.0;
       vec3 mapN = normalize( vec3( n1.xy + n2.xy, n1.z * n2.z ) );`);
  };
  const patched = new Set();
  root.traverse((o) => {
    if (!o.isMesh) return;
    const m = o.material;
    if (o.name === "water" || m.name === "water") { o.material = waterMat; o.receiveShadow = false; return; }
    if (FOLIAGE.test(m.name) && !patched.has(m)) {
      patched.add(m);
      m.transparent = false; m.alphaTest = 0.45; m.alphaToCoverage = true; m.side = THREE.DoubleSide; m.depthWrite = true;
      m.onBeforeCompile = (s) => { s.uniforms.uTime = uTime; s.vertexShader = "uniform float uTime;\n" + s.vertexShader.replace("#include <begin_vertex>", swayChunk); };
    }
    if (/^awning_|patchwork/.test(m.name)) m.side = THREE.DoubleSide;
    o.castShadow = !/^(hill|distant|copper_far)/.test(m.name) && o.name !== "distant_hills";
    o.receiveShadow = true;
  });
  // collapse linked duplicates into InstancedMesh
  const groups = new Map();
  root.traverse((o) => {
    if (!o.isMesh || inAirship(o)) return;
    const k = o.geometry.uuid + "|" + o.material.uuid;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(o);
  });
  const staticRoot = new THREE.Group();
  scene.add(staticRoot);
  let instanced = 0;
  for (const list of groups.values()) {
    if (list.length < 3) continue;
    const im = new THREE.InstancedMesh(list[0].geometry, list[0].material, list.length);
    im.name = list[0].name + "_inst";
    list.forEach((o, i) => { o.updateWorldMatrix(true, false); im.setMatrixAt(i, o.matrixWorld); o.parent.remove(o); });
    im.castShadow = list[0].castShadow; im.receiveShadow = true;
    im.computeBoundingSphere(); im.computeBoundingBox();
    staticRoot.add(im);
    instanced += list.length;
  }
  root.updateMatrixWorld(true);
  const mixer = new THREE.AnimationMixer(root);
  gltf.animations.forEach((c) => mixer.clipAction(c).play());
  return { root, staticRoot, mixer, instanced, airship, inAirship };
}

// Static collision triangles -> TriGrid. Walls/floors block walking and shots; awnings only block shots.
export function buildGrid(world, bounds) {
  const chunks = [];
  let total = 0;
  const v = new THREE.Vector3();
  const m4 = new THREE.Matrix4(), mi = new THREE.Matrix4();
  const add = (geo, mats, flag) => {
    const pos = geo.attributes.position, idx = geo.index;
    const n = idx ? idx.count / 3 : pos.count / 3;
    const out = new Float32Array(n * 9 * mats.length);
    let o = 0;
    for (const M of mats) {
      for (let t = 0; t < n; t++) {
        for (let k = 0; k < 3; k++) {
          const vi = idx ? idx.getX(t * 3 + k) : t * 3 + k;
          v.fromBufferAttribute(pos, vi).applyMatrix4(M);
          out[o++] = v.x; out[o++] = v.y; out[o++] = v.z;
        }
      }
    }
    chunks.push([out, flag]);
    total += out.length / 9;
  };
  const visit = (o) => {
    if (!(o.isMesh || o.isInstancedMesh) || world.inAirship(o)) return;
    const name = o.material.name || "";
    if (NOSOLID.test(name) || o.material === undefined) return;
    if (o.material.isMeshStandardMaterial && o.material.transparent && o.material.opacity < 0.95) return;
    const flag = SHOT_ONLY.test(name) ? SHOT : WALK | SHOT;
    if (o.isInstancedMesh) {
      // small decor raised up a facade (sills, shutters, upper windows, wall lamps, balcony rails) is left out:
      // nobody walks there and it would triple the triangle count
      if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
      const gb = o.geometry.boundingBox, box = new THREE.Box3(), size = new THREE.Vector3();
      const mats = [];
      for (let i = 0; i < o.count; i++) {
        o.getMatrixAt(i, mi); const M = mi.clone().premultiply(o.matrixWorld);
        box.copy(gb).applyMatrix4(M); box.getSize(size);
        if (Math.max(size.x, size.y, size.z) < 1.8 && box.min.y > 0.9) continue;
        mats.push(M);
      }
      if (mats.length) add(o.geometry, mats, flag);
    } else add(o.geometry, [m4.copy(o.matrixWorld)], flag);
  };
  world.root.traverse(visit);
  world.staticRoot.traverse(visit);
  const tris = new Float32Array(total * 9);
  const flags = new Uint8Array(total);
  let off = 0;
  for (const [arr, f] of chunks) { tris.set(arr, off * 9); flags.fill(f, off, off + arr.length / 9); off += arr.length / 9; }
  const grid = new TriGrid(bounds, 4).build(tris, flags);
  return { grid, tris: total };
}
