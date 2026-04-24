import { useRef, useEffect } from 'react'

const CLASS_NAMES = ['CNV', 'DME', 'DRUSEN', 'NORMAL']
const COLORS = {
    CNV: '#ff7043',
    DME: '#42a5f5',
    DRUSEN: '#ffca28',
    NORMAL: '#66bb6a',
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
        const R = Math.min(W, H) / 2 - 30

        ctx.clearRect(0, 0, W, H)

        // Draw grid circles
        for (let i = 1; i <= 4; i++) {
            const r = (R * i) / 4
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, Math.PI * 2)
            ctx.strokeStyle = `rgba(0, 230, 118, ${i === 4 ? 0.2 : 0.08})`
            ctx.lineWidth = 1
            ctx.stroke()
        }

        // Draw axes and labels
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
            ctx.strokeStyle = 'rgba(0, 230, 118, 0.1)'
            ctx.lineWidth = 1
            ctx.stroke()

            // Labels
            const lx = cx + (R + 18) * Math.cos(angle)
            const ly = cy + (R + 18) * Math.sin(angle)
            ctx.font = '10px Inter, sans-serif'
            ctx.fillStyle = COLORS[CLASS_NAMES[i]]
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText(CLASS_NAMES[i], lx, ly)
        }

        // Draw data polygon
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
        ctx.fillStyle = 'rgba(0, 230, 118, 0.15)'
        ctx.fill()
        ctx.strokeStyle = '#00e676'
        ctx.lineWidth = 2
        ctx.stroke()

        // Draw data points
        for (let i = 0; i < n; i++) {
            const angle = startAngle + i * angleStep
            const r = R * values[i]
            const x = cx + r * Math.cos(angle)
            const y = cy + r * Math.sin(angle)
            ctx.beginPath()
            ctx.arc(x, y, 4, 0, Math.PI * 2)
            ctx.fillStyle = COLORS[CLASS_NAMES[i]]
            ctx.fill()
            ctx.strokeStyle = '#0a0f0a'
            ctx.lineWidth = 2
            ctx.stroke()
        }

        // Draw percentage labels
        for (let i = 0; i < n; i++) {
            const angle = startAngle + i * angleStep
            const r = R * values[i]
            if (values[i] > 0) {
                const lx = cx + (r + 14) * Math.cos(angle)
                const ly = cy + (r + 14) * Math.sin(angle)
                ctx.font = 'bold 9px Inter, sans-serif'
                ctx.fillStyle = '#e0f2e0'
                ctx.textAlign = 'center'
                ctx.textBaseline = 'middle'
                ctx.fillText(`${Math.round(values[i] * 100)}%`, lx, ly)
            }
        }
    }, [stats])

    return (
        <div className="radar-canvas-container">
            <canvas ref={canvasRef} width={220} height={220} />
        </div>
    )
}
