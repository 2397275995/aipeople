/**
 * 动态卡通导游「小导」— Canvas 渲染（增强版）
 * 口型 ParamMouthOpenY · 情感 startMotion
 */
;(function () {
  const MOUTH_PARAM = 'ParamMouthOpenY'

  function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v))
  }

  function lerp(a, b, t) {
    return a + (b - a) * t
  }

  window.Live2DApp = {
    async init(canvas) {
      const ctx = canvas.getContext('2d')
      const w = canvas.width
      const h = canvas.height
      let destroyed = false
      let mouthOpen = 0
      let mouthSmooth = 0
      let emotion = 'friendly'
      let emotionBlend = 1
      let motionKick = 0
      const petals = Array.from({ length: 8 }, (_, i) => ({
        x: Math.random() * w,
        y: Math.random() * h * 0.6,
        r: 2 + Math.random() * 3,
        phase: i * 1.2,
        speed: 0.3 + Math.random() * 0.4,
      }))

      function drawBackground(time) {
        const sky = ctx.createLinearGradient(0, 0, 0, h)
        sky.addColorStop(0, '#bae6fd')
        sky.addColorStop(0.35, '#d1fae5')
        sky.addColorStop(0.7, '#ecfdf5')
        sky.addColorStop(1, '#f0fdfa')
        ctx.fillStyle = sky
        ctx.fillRect(0, 0, w, h)

        // 太阳光晕
        const sunX = w * 0.82
        const sunY = h * 0.12
        const sunG = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, 70)
        sunG.addColorStop(0, 'rgba(253, 224, 71, 0.45)')
        sunG.addColorStop(1, 'rgba(253, 224, 71, 0)')
        ctx.fillStyle = sunG
        ctx.fillRect(0, 0, w, h * 0.45)

        // 远山
        ctx.fillStyle = 'rgba(13, 148, 136, 0.14)'
        ctx.beginPath()
        ctx.moveTo(0, h * 0.74)
        ctx.lineTo(w * 0.15, h * 0.56)
        ctx.lineTo(w * 0.32, h * 0.65)
        ctx.lineTo(w * 0.5, h * 0.5)
        ctx.lineTo(w * 0.68, h * 0.6)
        ctx.lineTo(w * 0.85, h * 0.52)
        ctx.lineTo(w, h * 0.58)
        ctx.lineTo(w, h)
        ctx.lineTo(0, h)
        ctx.closePath()
        ctx.fill()

        // 灵山大佛剪影（远景）
        ctx.fillStyle = 'rgba(15, 118, 110, 0.18)'
        ctx.beginPath()
        ctx.moveTo(w * 0.38, h * 0.58)
        ctx.lineTo(w * 0.42, h * 0.42)
        ctx.lineTo(w * 0.46, h * 0.38)
        ctx.lineTo(w * 0.5, h * 0.42)
        ctx.lineTo(w * 0.54, h * 0.38)
        ctx.lineTo(w * 0.58, h * 0.42)
        ctx.lineTo(w * 0.62, h * 0.58)
        ctx.closePath()
        ctx.fill()

        // 飘落花瓣
        petals.forEach((p) => {
          const px = (p.x + Math.sin(time * 0.001 + p.phase) * 30) % (w + 20)
          const py = (p.y + time * 0.025 * p.speed) % (h * 0.75)
          ctx.fillStyle = `rgba(244, 114, 182, ${0.25 + Math.sin(time * 0.003 + p.phase) * 0.15})`
          ctx.beginPath()
          ctx.ellipse(px - 10, py, p.r, p.r * 0.6, time * 0.002 + p.phase, 0, Math.PI * 2)
          ctx.fill()
        })

        ctx.fillStyle = 'rgba(20, 184, 166, 0.1)'
        ctx.fillRect(0, h * 0.84, w, h * 0.16)
      }

      function drawSoundWaves(cx, cy, time, intensity) {
        if (intensity < 0.1) return
        ctx.strokeStyle = `rgba(13, 148, 136, ${0.15 + intensity * 0.25})`
        ctx.lineWidth = 2
        for (let i = 0; i < 3; i++) {
          const phase = (time * 0.008 + i * 0.8) % 3
          const r = 18 + phase * 12 + intensity * 8
          ctx.globalAlpha = 1 - phase / 3
          ctx.beginPath()
          ctx.arc(cx, cy, r, -0.4, 0.4)
          ctx.stroke()
        }
        ctx.globalAlpha = 1
      }

      function drawCharacter(time) {
        mouthSmooth = lerp(mouthSmooth, mouthOpen, 0.35)
        const speaking = mouthSmooth > 0.1
        const breathe = Math.sin(time * 0.0022) * 4
        const sway = Math.sin(time * 0.0016) * 3
        const headBob = speaking ? Math.sin(time * 0.018) * 4 : Math.sin(time * 0.002) * 1.5
        const headTilt = speaking
          ? Math.sin(time * 0.01) * 0.06
          : Math.sin(time * 0.0012) * 0.03
        const blink = Math.sin(time * 0.0028 + 1.5) > 0.985

        const cx = w * 0.5 + sway
        const bodyY = h * 0.5 + breathe
        const headY = h * 0.31 + breathe + headBob

        ctx.save()
        ctx.translate(cx, 0)

        // 讲解旗（左手）
        const flagWave = Math.sin(time * 0.006) * 0.08
        ctx.save()
        ctx.translate(-58, bodyY + 42)
        ctx.rotate(-0.35 + flagWave)
        ctx.fillStyle = '#92400e'
        ctx.fillRect(-3, 0, 6, 55)
        ctx.fillStyle = '#ef4444'
        ctx.beginPath()
        ctx.moveTo(3, 4)
        ctx.lineTo(38, 14 + Math.sin(time * 0.01) * 4)
        ctx.lineTo(3, 28)
        ctx.closePath()
        ctx.fill()
        ctx.fillStyle = '#fbbf24'
        ctx.font = 'bold 9px sans-serif'
        ctx.fillText('导', 10, 20)
        ctx.restore()

        // 身体 — 景区制服
        const bodyGrad = ctx.createLinearGradient(0, bodyY, 0, bodyY + 160)
        bodyGrad.addColorStop(0, '#0f766e')
        bodyGrad.addColorStop(1, '#115e59')
        ctx.fillStyle = bodyGrad
        ctx.beginPath()
        ctx.moveTo(-50, bodyY + 18)
        ctx.lineTo(50, bodyY + 18)
        ctx.lineTo(44, bodyY + 158)
        ctx.lineTo(-44, bodyY + 158)
        ctx.closePath()
        ctx.fill()

        // 绶带
        ctx.fillStyle = '#f59e0b'
        ctx.beginPath()
        ctx.moveTo(0, bodyY + 22)
        ctx.lineTo(14, bodyY + 95)
        ctx.lineTo(0, bodyY + 88)
        ctx.lineTo(-14, bodyY + 95)
        ctx.closePath()
        ctx.fill()
        ctx.fillStyle = '#fef3c7'
        ctx.font = 'bold 8px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText('灵山', 0, bodyY + 58)
        ctx.fillText('胜景', 0, bodyY + 70)

        // 右小臂 + 平板（讲解时举起）
        const tabletAngle = speaking
          ? -1.1 + Math.sin(time * 0.014) * 0.12
          : -0.5 + Math.sin(time * 0.0018) * 0.05
        ctx.save()
        ctx.translate(46, bodyY + 48)
        ctx.rotate(tabletAngle)
        ctx.fillStyle = '#fcd9b6'
        ctx.fillRect(-7, 0, 14, 38)
        ctx.fillStyle = '#1e293b'
        ctx.fillRect(-14, 38, 28, 36)
        ctx.fillStyle = '#5eead4'
        ctx.fillRect(-11, 42, 22, 16)
        ctx.fillStyle = '#fff'
        ctx.font = '7px sans-serif'
        ctx.fillText('景点', -8, 52)
        ctx.restore()

        // 左臂
        ctx.save()
        ctx.translate(-48, bodyY + 50)
        ctx.rotate(0.25 + flagWave * 0.5)
        ctx.fillStyle = '#fcd9b6'
        ctx.fillRect(-7, 0, 14, 40)
        ctx.beginPath()
        ctx.arc(0, 44, 10, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()

        // 头 + 轻微倾斜
        ctx.save()
        ctx.translate(0, headY)
        ctx.rotate(headTilt)

        // 头发（后发）
        ctx.fillStyle = '#2c1810'
        ctx.beginPath()
        ctx.moveTo(-48, -10)
        ctx.quadraticCurveTo(-55 + Math.sin(time * 0.004) * 5, 40, -38, 55)
        ctx.lineTo(38, 55)
        ctx.quadraticCurveTo(55 + Math.sin(time * 0.004 + 1) * 5, 40, 48, -10)
        ctx.fill()

        // 脸
        const faceGrad = ctx.createRadialGradient(-12, -8, 8, 0, 0, 58)
        faceGrad.addColorStop(0, '#fde8d5')
        faceGrad.addColorStop(1, '#f5cba7')
        ctx.fillStyle = faceGrad
        ctx.beginPath()
        ctx.ellipse(0, 0, 50, 54, 0, 0, Math.PI * 2)
        ctx.fill()

        // 导游帽
        ctx.fillStyle = '#0d9488'
        ctx.fillRect(-58, -68, 116, 16)
        ctx.beginPath()
        ctx.ellipse(0, -60, 34, 26, 0, Math.PI, 0)
        ctx.fill()
        ctx.fillStyle = '#fbbf24'
        ctx.fillRect(-20, -54, 40, 7)
        ctx.fillStyle = '#fef3c7'
        ctx.font = 'bold 8px sans-serif'
        ctx.fillText('导游', -12, -48)

        // 刘海
        ctx.fillStyle = '#2c1810'
        for (let i = -2; i <= 2; i++) {
          ctx.beginPath()
          ctx.ellipse(i * 14, -22, 10, 18, i * 0.15, 0, Math.PI * 2)
          ctx.fill()
        }

        // 眼睛
        const eyeLookX = Math.sin(time * 0.001) * 2
        const eyeY = 4
        ;[-20, 20].forEach((ox) => {
          ctx.save()
          ctx.translate(ox + eyeLookX, eyeY)
          ctx.scale(1, blink ? 0.12 : 1)
          // 眼白
          ctx.fillStyle = '#fff'
          ctx.beginPath()
          ctx.ellipse(0, 0, 11, 13, 0, 0, Math.PI * 2)
          ctx.fill()
          // 虹膜
          ctx.fillStyle = emotion === 'excited' ? '#059669' : '#0f766e'
          ctx.beginPath()
          ctx.arc(eyeLookX * 0.5, 1, 6, 0, Math.PI * 2)
          ctx.fill()
          ctx.fillStyle = '#1f2937'
          ctx.beginPath()
          ctx.arc(eyeLookX * 0.5 + 1, 1, 3.5, 0, Math.PI * 2)
          ctx.fill()
          // 高光
          if (!blink) {
            ctx.fillStyle = '#fff'
            ctx.beginPath()
            ctx.arc(3, -2, 2.5, 0, Math.PI * 2)
            ctx.fill()
          }
          ctx.restore()
        })

        // 眉毛
        ctx.strokeStyle = '#4b5563'
        ctx.lineWidth = 2.5
        ctx.lineCap = 'round'
        const browLift = emotion === 'excited' ? -4 : emotion === 'professional' ? 2 : -2
        ctx.beginPath()
        ctx.moveTo(-32, -12 + browLift)
        ctx.quadraticCurveTo(-20, -20 + browLift, -8, -14 + browLift)
        ctx.moveTo(8, -14 + browLift)
        ctx.quadraticCurveTo(20, -20 + browLift, 32, -12 + browLift)
        ctx.stroke()

        // 嘴巴
        const mouthY = 30
        ctx.fillStyle = speaking ? '#e11d48' : '#c2410c'
        if (speaking) {
          const mw = 12 + mouthSmooth * 8
          const mh = 3 + mouthSmooth * 20
          ctx.beginPath()
          ctx.ellipse(0, mouthY, mw, mh, 0, 0, Math.PI * 2)
          ctx.fill()
          if (mouthSmooth > 0.35) {
            ctx.fillStyle = '#fff'
            ctx.fillRect(-mw * 0.5, mouthY - mh * 0.3, mw, mh * 0.35)
            ctx.fillStyle = '#fda4af'
            ctx.beginPath()
            ctx.ellipse(0, mouthY + mh * 0.35, mw * 0.45, mh * 0.25, 0, 0, Math.PI * 2)
            ctx.fill()
          }
          drawSoundWaves(0, mouthY + 5, time, mouthSmooth)
        } else {
          const smileW = emotion === 'friendly' || emotion === 'excited' ? 1 : 0.5
          ctx.lineWidth = 2.5
          ctx.strokeStyle = '#c2410c'
          ctx.beginPath()
          ctx.arc(0, mouthY - 4 * smileW, 14, 0.2 * Math.PI, 0.8 * Math.PI)
          ctx.stroke()
        }

        // 腮红
        const blushA = emotion === 'excited' ? 0.5 : 0.32
        ctx.fillStyle = `rgba(251, 113, 133, ${blushA})`
        ctx.beginPath()
        ctx.ellipse(-32, 18, 13, 8, 0, 0, Math.PI * 2)
        ctx.ellipse(32, 18, 13, 8, 0, 0, Math.PI * 2)
        ctx.fill()

        // 兴奋星星眼
        if (emotion === 'excited' && !blink && !speaking) {
          ctx.fillStyle = '#fbbf24'
          ctx.font = '10px sans-serif'
          ctx.fillText('✦', -24, 0)
          ctx.fillText('✦', 18, 0)
        }

        ctx.restore() // head tilt

        // 讲解气泡 + 音符
        if (speaking) {
          const bx = -95
          const by = headY - 55 + Math.sin(time * 0.009) * 5
          ctx.fillStyle = 'rgba(255,255,255,0.94)'
          ctx.strokeStyle = 'rgba(13,148,136,0.4)'
          ctx.lineWidth = 2
          roundRect(ctx, bx, by, 90, 34, 12)
          ctx.fill()
          ctx.stroke()
          ctx.beginPath()
          ctx.moveTo(bx + 75, by + 17)
          ctx.lineTo(bx + 88, by + 28)
          ctx.lineTo(bx + 70, by + 34)
          ctx.fill()
          ctx.fillStyle = '#0f766e'
          ctx.font = '600 11px "Noto Sans SC", sans-serif'
          ctx.textAlign = 'left'
          ctx.fillText('正在讲解', bx + 12, by + 21)
          ctx.font = '14px sans-serif'
          ctx.fillText('♪', bx + 72, by - 6 + Math.sin(time * 0.015) * 3)
        }

        // 情感切换弹跳
        if (motionKick > 0) {
          ctx.strokeStyle = `rgba(245, 158, 11, ${motionKick * 0.4})`
          ctx.lineWidth = 3
          ctx.beginPath()
          ctx.arc(0, headY, 62 + (1 - motionKick) * 18, 0, Math.PI * 2)
          ctx.stroke()
          motionKick *= 0.92
          if (motionKick < 0.02) motionKick = 0
        }

        ctx.restore()
      }

      function roundRect(c, x, y, width, height, radius) {
        c.beginPath()
        c.moveTo(x + radius, y)
        c.lineTo(x + width - radius, y)
        c.quadraticCurveTo(x + width, y, x + width, y + radius)
        c.lineTo(x + width, y + height - radius)
        c.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
        c.lineTo(x + radius, y + height)
        c.quadraticCurveTo(x, y + height, x, y + height - radius)
        c.lineTo(x, y + radius)
        c.quadraticCurveTo(x, y, x + radius, y)
        c.closePath()
      }

      function draw(time) {
        if (destroyed || !ctx) return
        drawBackground(time)
        drawCharacter(time)
        requestAnimationFrame(draw)
      }
      requestAnimationFrame(draw)

      return {
        setParameterValueById(id, value) {
          if (id === MOUTH_PARAM) mouthOpen = clamp(value, 0, 1)
        },
        startMotion(group) {
          const map = {
            friendly: 'friendly',
            professional: 'professional',
            excited: 'excited',
            curious: 'friendly',
            surprise: 'excited',
            happy: 'excited',
          }
          emotion = map[group] || 'friendly'
          motionKick = 1
        },
        update() {},
        destroy() {
          destroyed = true
        },
      }
    },
  }
})()
