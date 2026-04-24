import { useRef, useEffect } from 'react'

const CLASS_NAMES = ['CNV', 'DME', 'DRUSEN', 'NORMAL']
const COLORS = {
    CNV: '#ff7e5f',
    DME: '#5fa8ff',
    DRUSEN: '#ffc857',
    NORMAL: '#00d4aa',
}

export default function MasteryRadar({ stats }) {
    const canvasRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        const W = canvas.width
        const H = canvas.height
        const cx = W / 2
        const cy = H / 2
        const R = Math.min(W, H) / 2 - 28

        ctx.clearRect(0, 0, W, H)

        // Grid circles
        for (let i = 1; i <= 4; i++) {
            const r = (R * i) / 4
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, Math.PI * 2)
            ctx.strokeStyle = `rgba(0, 212, 170, ${i === 4 ? 0.18 : 0.06})`
            ctx.lineWidth = 1
            ctx.stroke()
        }

        // Axes and labels
        const n = CLASS_NAMES.length
        const angleStep = (Math.PI * 2) / n
        const startAngle = -Math.PI / 2

        for (let i = 0; i < n; i++) {
            const angle = startAngle + i * angleStep
            const x = cx + R * Math.cos(angle)
            const y = cy + R * Math.sin(angle)

            ctx.beginPath()
            ctx.moveTo(cx, cy)
            ctx.lineTo(x, y)
            ctx.strokeStyle = 'rgba(0, 212, 170, 0.08)'
            ctx.lineWidth = 1
            ctx.stroke()

            const lx = cx + (R + 16) * Math.cos(angle)
            const ly = cy + (R + 16) * Math.sin(angle)
            ctx.font = '10px Inter, sans-serif'
            ctx.fillStyle = COLORS[CLASS_NAMES[i]]
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText(CLASS_NAMES[i], lx, ly)
        }

        // Data polygon
        const values = CLASS_NAMES.map(cls => {
            const s = stats?.[cls]
            return s ? s.accuracy : 0
        })

        ctx.beginPath()
        for (let i = 0; i < n; i++) {
            const angle = startAngle + i * angleStep
            const r = R * values[i]
            const x = cx + r * Math.cos(angle)
            const y = cy + r * Math.sin(angle)
            if (i === 0) ctx.moveTo(x, y)
            else ctx.lineTo(x, y)
        }
        ctx.closePath()
        ctx.fillStyle = 'rgba(0, 212, 170, 0.12)'
        ctx.fill()
        ctx.strokeStyle = '#00d4aa'
        ctx.lineWidth = 2
        ctx.stroke()

        // Data points
        for (let i = 0; i < n; i++) {
            const angle = startAngle + i * angleStep
            const r = R * values[i]
            const x = cx + r * Math.cos(angle)
            const y = cy + r * Math.sin(angle)
            ctx.beginPath()
            ctx.arc(x, y, 3.5, 0, Math.PI * 2)
            ctx.fillStyle = COLORS[CLASS_NAMES[i]]
            ctx.fill()
            ctx.strokeStyle = '#0a1628'
            ctx.lineWidth = 2
            ctx.stroke()
        }

        // Percentage labels
        for (let i = 0; i < n; i++) {
            const angle = startAngle + i * angleStep
            const r = R * values[i]
            if (values[i] > 0) {
                const lx = cx + (r + 12) * Math.cos(angle)
                const ly = cy + (r + 12) * Math.sin(angle)
                ctx.font = 'bold 9px Inter, sans-serif'
                ctx.fillStyle = '#e0f0f5'
                ctx.textAlign = 'center'
                ctx.textBaseline = 'middle'
                ctx.fillText(`${Math.round(values[i] * 100)}%`, lx, ly)
            }
        }
    }, [stats])

    return (
        <div className="radar-canvas-container">
            <canvas ref={canvasRef} width={200} height={200} />
        </div>
    )
}
