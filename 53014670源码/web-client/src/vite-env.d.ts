/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

declare module '*.png' {
  const src: string
  export default src
}

interface Live2DAppGlobal {
  init(
    canvas: HTMLCanvasElement,
    options: { modelPath: string; width?: number; height?: number },
  ): Promise<{
    setParameterValueById(id: string, value: number): void
    startMotion(group: string, index: number, priority?: number): void
    update(deltaMs: number): void
    destroy(): void
  }>
}

interface Window {
  Live2DCubismCore?: unknown
  Live2DApp?: Live2DAppGlobal
}
