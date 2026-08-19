/**
 * Live2D Sample 桥接脚本 — 参考模板
 *
 * 实际使用时请基于 Cubism SDK 官方 TypeScript Demo 构建，
 * 或在此模板基础上接入 LAppModel / LAppDelegate。
 *
 * 本文件仅为接口示例，默认不会被加载（需重命名为 live2d-app.js 并实现 init）。
 */
/* global Live2DCubismCore */

window.Live2DApp = {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {{ modelPath: string, width?: number, height?: number }} options
   */
  async init(canvas, options) {
    console.warn(
      '[Live2D] 使用的是 stub 桥接脚本，请替换为基于官方 Sample 的 live2d-app.js',
    )

    const ctx = canvas.getContext('2d')
    let mouthOpen = 0
    let destroyed = false

    function draw() {
      if (destroyed || !ctx) return
      ctx.fillStyle = '#ecfdf5'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#0d9488'
      ctx.font = '14px sans-serif'
      ctx.fillText('Live2D Stub — 请放置正式 SDK', 20, 40)
      // 简易口型指示条
      ctx.fillStyle = '#14b8a6'
      ctx.fillRect(20, canvas.height - 40, mouthOpen * (canvas.width - 40), 12)
      requestAnimationFrame(draw)
    }
    draw()

    return {
      setParameterValueById(id, value) {
        if (id === 'ParamMouthOpenY') mouthOpen = value
      },
      startMotion(_group, _index, _priority) {
        console.log('[Live2D stub] startMotion', _group, _index)
      },
      update(_deltaMs) {},
      destroy() {
        destroyed = true
      },
    }
  },
}
