/**
 * Live2D Cubism SDK bridge.
 */

import * as PIXI from 'pixi.js'
import { loadScript } from '@/utils/loadScript'

export const EMOTION_MOTIONS: Record<string, { group: string; index: number }> = {
  happy: { group: 'TapBody', index: 0 },
  friendly: { group: 'TapBody', index: 0 },
  excited: { group: 'TapBody', index: 0 },
  surprise: { group: 'TapBody', index: 1 },
  think: { group: 'Idle', index: 0 },
  neutral: { group: 'Idle', index: 0 },
  professional: { group: 'Idle', index: 0 },
}

export interface Live2DModelHandle {
  setParameterValueById(id: string, value: number): void
  startMotion(group: string, index: number, priority?: number): void
  update(deltaMs: number): void
  destroy(): void
}

let runtimeReady = false

async function ensureCubismCore() {
  if (runtimeReady) return
  ;(window as any).PIXI = PIXI
  await loadScript('/live2d/live2dcubismcore.min.js')
  runtimeReady = true
}

export async function createLive2DModel(
  canvas: HTMLCanvasElement,
  modelPath = '/live2d/models/Haru/Haru.model3.json',
): Promise<Live2DModelHandle> {
  await ensureCubismCore()
  const { Live2DModel, MotionPreloadStrategy } = await import('pixi-live2d-display/cubism4')

  const app = new PIXI.Application({
    view: canvas,
    transparent: true,
    autoDensity: true,
    autoResize: true,
    antialias: true,
    autoUpdate: false,
    width: canvas.width,
    height: canvas.height,
  })

  const model = await Live2DModel.from(modelPath, {
    motionPreload: MotionPreloadStrategy.NONE,
  })

  app.stage.addChild(model)
  model.scale.set(0.55)
  model.x = canvas.width * 0.5
  model.y = canvas.height * 0.95
  ;(model as any).anchor?.set?.(0.5, 1)

  model.interactive = false
  model.eventMode = 'none' as any

  function setParameterValueById(id: string, value: number) {
    model.internalModel.coreModel.setParameterValueById(id, Math.max(0, Math.min(1, value)))
  }

  function startMotion(group: string, index: number, priority = 2) {
    model.motion(group, index, priority)
  }

  function update(deltaMs: number) {
    model.update(deltaMs)
    app.renderer.render(app.stage)
  }

  function destroy() {
    model.destroy()
    app.destroy(true, { children: true, texture: true, baseTexture: true })
  }

  return {
    setParameterValueById,
    startMotion,
    update,
    destroy,
  }
}

export const MOUTH_PARAM = 'ParamMouthOpenY'
