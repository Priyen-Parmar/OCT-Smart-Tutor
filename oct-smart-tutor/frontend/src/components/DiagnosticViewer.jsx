import { useState, useRef, useCallback } from 'react'

export default function DiagnosticViewer({ imageUrl }) {
    const [zoom, setZoom] = useState(1)
    const [brightness, setBrightness] = useState(100)
    const [contrast, setContrast] = useState(100)
    const [offset, setOffset] = useState({ x: 0, y: 0 })
    const [dragging, setDragging] = useState(false)
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
    const containerRef = useRef(null)

    const handleZoomIn = () => setZoom(z => Math.min(z + 0.25, 5))
    const handleZoomOut = () => setZoom(z => Math.max(z - 0.25, 0.5))
    const handleReset = () => {
        setZoom(1)
        setBrightness(100)
        setContrast(100)
        setOffset({ x: 0, y: 0 })
    }

    const handleWheel = useCallback((e) => {
        e.preventDefault()
        setZoom(z => {
            const delta = e.deltaY > 0 ? -0.15 : 0.15
            return Math.max(0.5, Math.min(5, z + delta))
        })
    }, [])

    const handleMouseDown = (e) => {
        setDragging(true)
        setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
    }

    const handleMouseMove = (e) => {
        if (!dragging) return
        setOffset({
            x: e.clientX - dragStart.x,
            y: e.clientY - dragStart.y,
        })
    }

    const handleMouseUp = () => setDragging(false)

    if (!imageUrl) {
        return (
            <div className="center-panel">
                <div className="viewer-container">
                    <div className="viewer-empty">
                        <div className="viewer-empty-icon">📷</div>
                        <p className="viewer-empty-text">Click "Start Training" to load your first case</p>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="center-panel">
            {/* Toolbar */}
            <div className="viewer-toolbar">
                <button className="toolbar-btn" onClick={handleZoomIn} title="Zoom In">🔍+</button>
                <button className="toolbar-btn" onClick={handleZoomOut} title="Zoom Out">🔍−</button>
                <button className="toolbar-btn" onClick={handleReset} title="Reset View">↺</button>
            </div>

            {/* Image Viewer */}
            <div
                ref={containerRef}
                className="viewer-container"
                onWheel={handleWheel}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                <img
                    className="viewer-image"
                    src={imageUrl}
                    alt="OCT Scan"
                    draggable={false}
                    style={{
                        transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
                        filter: `brightness(${brightness}%) contrast(${contrast}%)`,
                    }}
                />
            </div>

            {/* Contrast/Brightness Controls */}
            <div className="contrast-slider-container">
                <span className="contrast-label">☀️ Brightness</span>
                <input
                    className="contrast-slider"
                    type="range"
                    min="30"
                    max="200"
                    value={brightness}
                    onChange={(e) => setBrightness(Number(e.target.value))}
                />
                <span className="contrast-value">{brightness}%</span>

                <span className="contrast-label" style={{ marginLeft: 12 }}>🔲 Contrast</span>
                <input
                    className="contrast-slider"
                    type="range"
                    min="30"
                    max="200"
                    value={contrast}
                    onChange={(e) => setContrast(Number(e.target.value))}
                />
                <span className="contrast-value">{contrast}%</span>
            </div>
        </div>
    )
}
