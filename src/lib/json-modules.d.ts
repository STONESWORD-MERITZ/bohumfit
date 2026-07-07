// JSON module declaration for Vite/TypeScript.
// Keep imported JSON values unknown; callers should narrow or validate.
declare module "*.json" {
  const value: unknown;
  export default value;
}
