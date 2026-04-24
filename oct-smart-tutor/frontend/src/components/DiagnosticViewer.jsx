import { useState, useRef, useCallback, useEffect } from 'react'

export default function DiagnosticViewer({ imageUrl, loading, onStartTraining }) {
    const [zoom, setZoom] = useState(1)
    const [offset, setOffset] = useState({ x: 0, y: 0 })
    const [dragging, setDragging] = useState(false)
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

    // Use refs for brightness/contrast to avoid re-renders on every slider tick
    const brightnessRef = useRef(100)
    const contrastRef = useRef(100)
    const imgRef = useRef(null)
    const containerRef = useRef(null)
    const brightnessDisplayRef = useRef(null)
    const contrastDisplayRef = useRef(null)

    // Apply filter directly to the image DOM element (no re-render needed)
    const applyFilter = useCallback(() => {
        if (imgRef.current) {
            imgRef.current.style.filter =
                `brightness(${brightnessRef.current}%) contrast(${contrastRef.current}%)`
        }
    }, [])

    const handleBrightnessChange = (e) => {
        brightnessRef.current = Number(e.target.value)
        applyFilter()
        if (brightnessDisplayRef.current) {
            brightnessDisplayRef.current.textContent = `${brightnessRef.current}%`
        }
    }

    const handleContrastChange = (e) => {
        contrastRef.current = Number(e.target.value)
        applyFilter()
        if (contrastDisplayRef.current) {
            contrastDisplayRef.current.textContent = `${contrastRef.current}%`
        }
    }

    const handleZoomIn = () => setZoom(z => Math.min(z + 0.25, 5))
    const handleZoomOut = () => setZoom(z => Math.max(z - 0.25, 0.5))
    const handleReset = () => {
        setZoom(1)
        setOffset({ x: 0, y: 0 })
        brightnessRef.current = 100
        contrastRef.current = 100
        applyFilter()
        // Update slider positions directly
        const sliders = document.querySelectorAll('.contrast-slider')
        if (sliders[0]) sliders[0].value = 100
        if (sliders[1]) sliders[1].value = 100
        if (brightnessDisplayRef.current) brightnessDisplayRef.current.textContent = '100%'
        if (contrastDisplayRef.current) contrastDisplayRef.current.textContent = '100%'
    }

    // Use a native (non-passive) wheel listener so preventDefault works
    useEffect(() => {
        const container = containerRef.current
        if (!container) return

        const onWheel = (e) => {
            e.preventDefault()
            const delta = e.deltaY > 0 ? -0.15 : 0.15
            setZoom(z => Math.max(0.5, Math.min(5, z + delta)))
        }

        container.addEventListener('wheel', onWheel, { passive: false })
        return () => container.removeEventListener('wheel', onWheel)
    }, [])

    const handleMouseDown = (e) => {
        setDragging(true)
        setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
    }
    const handleMouseMove = (e) => {
        if (!dragging) return
        setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
    }
    const handleMouseUp = () => setDragging(false)

    if (!imageUrl) {
        return (
            <div className="center-panel">
                <div className="viewer-container">
                    <div className="start-training-container">
                        <div className="viewer-empty-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                <circle cx="8.5" cy="8.5" r="1.5"/>
                                <polyline points="21 15 16 10 5 21"/>
                            </svg>
                        </div>
                        {loading ? (
                            <div className="loading-container" style={{ height: 'auto' }}>
                                <div className="loading-spinner" />
                                <span className="loading-text">Fetching image from Kaggle...</span>
                            </div>
                        ) : (
                            <>
                                <p className="viewer-empty-text">Ready to begin your training session</p>
                                <p className="viewer-empty-sub">Click below to load your first OCT scan</p>
                                <button className="next-case-btn" onClick={onStartTraining} style={{ marginTop: 12 }}>
                                    Start Training
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="center-panel">
            <div className="viewer-toolbar">
                <button className="toolbar-btn" onClick={handleZoomIn} title="Zoom In">+</button>
                <button className="toolbar-btn" onClick={handleZoomOut} title="Zoom Out">&minus;</button>
                <button className="toolbar-btn" onClick={handleReset} title="Reset View">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                        <polyline points="1 4 1 10 7 10"/>
                        <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
                    </svg>
                </button>
            </div>

            <div
                ref={containerRef}
                className="viewer-container"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                <img
                    ref={imgRef}
                    className="viewer-image"
                    src={imageUrl}
                    alt="OCT Scan"
                    draggable={false}
                    style={{
                        transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
                        filter: `brightness(${brightnessRef.current}%) contrast(${contrastRef.current}%)`,
                    }}
                />
            </div>

            <div className="contrast-slider-container">
                <span className="contrast-label">Brightness</span>
                <input
                    className="contrast-slider"
                    type="range"
                    min="30"
                    max="200"
                    defaultValue={100}
                    onInput={handleBrightnessChange}
                />
                <span className="contrast-value" ref={brightnessDisplayRef}>100%</span>

                <span className="contrast-label" style={{ marginLeft: 8 }}>Contrast</span>
                <input
                    className="contrast-slider"
                    type="range"
                    min="30"
                    max="200"
                    defaultValue={100}
                    onInput={handleContrastChange}
                />
                <span className="contrast-value" ref={contrastDisplayRef}>100%</span>
            </div>
        </div>
    )
}
