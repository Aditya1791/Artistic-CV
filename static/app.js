// ArtCV Studio - All-in-One Computer Vision & Creative Suite Controller

let catalog = {};
let activeEffectKey = "pencil_sketch";
let currentMode = "photo";
let activeTool = "filters";

let baseFile = null;
let currentFile = null;
let currentVideoFile = null;
let currentParams = {};

let activeStickerType = "emoji";
let activeEmojiSticker = "🎨";
let customStickerImg = null;
let customPatternFrameFile = null;

let videoClips = []; // [{ id, file, startTime: 0, endTime: null }]
let videoStickerList = []; // [{ type, emoji, x, y, width, height, rotation, start_time, end_time }]

let debounceTimer = null;

// History Undo / Redo Stack State
let historyStack = [];
let redoStack = [];

// Drawing & Interactive Sticker Overlay State
let isDrawing = false;
let drawCanvas, drawCtx;
let inpaintMaskCanvas, inpaintMaskCtx;
let stickerCommittedCanvas, stickerCommittedCtx;

// Active Transformable Sticker Object State
let activeStickerObj = null;
let activeTransformMode = null; // 'move' | 'resize' | 'rotate'
let transformStartCoords = { x: 0, y: 0 };
let transformStartObjState = null;

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  await fetchEffectsCatalog();
  setupEvents();
  setupModeSwitcher();
  setupSidebarToggle();
  setupToolTabs();
  setupDrawingCanvas();
  setupEnhancerControls();
  setupStickerGrid();
  setupFrameControls();
  setupResizerControls();
  setupVideoSequenceControls();
  setupVideoTimelineControls();
  setupUndoRedo();
}

async function fetchEffectsCatalog() {
  try {
    const res = await fetch("/api/effects");
    catalog = await res.json();
    renderCategoryTabs();
    renderEffectsGrid("All");
    selectEffect(Object.keys(catalog)[0]);
  } catch (err) {
    console.error("Failed to load ArtCV catalog:", err);
  }
}

function setupSidebarToggle() {
  const toggleBtn = document.getElementById("sidebarToggleBtn");
  const workspace = document.getElementById("workspace");

  toggleBtn.addEventListener("click", () => {
    workspace.classList.toggle("collapsed");
    if (workspace.classList.contains("collapsed")) {
      toggleBtn.innerText = "▶";
      toggleBtn.title = "Expand Sidebar";
    } else {
      toggleBtn.innerText = "◀";
      toggleBtn.title = "Collapse Sidebar";
    }
  });
}

function pushHistoryState() {
  if (!currentFile || !drawCanvas) return;

  const canvasSnapshot = drawCtx.getImageData(0, 0, drawCanvas.width, drawCanvas.height);
  const state = {
    file: currentFile,
    originalSrc: document.getElementById("originalImg").src,
    styledSrc: document.getElementById("styledImg").src,
    canvasData: canvasSnapshot,
    committedData: stickerCommittedCtx ? stickerCommittedCtx.getImageData(0, 0, drawCanvas.width, drawCanvas.height) : null
  };
  historyStack.push(state);
  redoStack = [];
  updateUndoRedoUI();
}

function setupUndoRedo() {
  const undoBtn = document.getElementById("undoBtn");
  const redoBtn = document.getElementById("redoBtn");

  if (undoBtn) undoBtn.addEventListener("click", () => undo());
  if (redoBtn) redoBtn.addEventListener("click", () => redo());
  updateUndoRedoUI();
}

function updateUndoRedoUI() {
  const undoBtn = document.getElementById("undoBtn");
  const redoBtn = document.getElementById("redoBtn");
  if (undoBtn) undoBtn.disabled = historyStack.length <= 1;
  if (redoBtn) redoBtn.disabled = redoStack.length === 0;
}

function undo() {
  if (historyStack.length <= 1) return;
  
  const currentState = historyStack.pop();
  redoStack.push(currentState);

  const previousState = historyStack[historyStack.length - 1];
  currentFile = previousState.file;
  document.getElementById("originalImg").src = previousState.originalSrc;
  document.getElementById("styledImg").src = previousState.styledSrc;
  document.getElementById("downloadBtn").href = previousState.styledSrc;

  activeStickerObj = null;

  if (previousState.committedData) {
    stickerCommittedCtx.putImageData(previousState.committedData, 0, 0);
  } else {
    stickerCommittedCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  }

  redrawOverlayCanvas();
  updateUndoRedoUI();
}

function redo() {
  if (redoStack.length === 0) return;

  const nextState = redoStack.pop();
  historyStack.push(nextState);

  currentFile = nextState.file;
  document.getElementById("originalImg").src = nextState.originalSrc;
  document.getElementById("styledImg").src = nextState.styledSrc;
  document.getElementById("downloadBtn").href = nextState.styledSrc;

  activeStickerObj = null;

  if (nextState.committedData) {
    stickerCommittedCtx.putImageData(nextState.committedData, 0, 0);
  } else {
    stickerCommittedCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  }

  redrawOverlayCanvas();
  updateUndoRedoUI();
}

function setupToolTabs() {
  const toolBtns = document.querySelectorAll(".tool-btn");
  toolBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      toolBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      activeTool = btn.getAttribute("data-tool");
      document.querySelectorAll(".tool-view").forEach(v => v.style.display = "none");

      if (activeTool === "filters") document.getElementById("viewFilters").style.display = "block";
      else if (activeTool === "enhancer") document.getElementById("viewEnhancer").style.display = "block";
      else if (activeTool === "brush") document.getElementById("viewBrush").style.display = "block";
      else if (activeTool === "eraser") document.getElementById("viewEraser").style.display = "block";
      else if (activeTool === "stickers") document.getElementById("viewStickers").style.display = "block";
      else if (activeTool === "frames") document.getElementById("viewFrames").style.display = "block";
      else if (activeTool === "resizer") document.getElementById("viewResizer").style.display = "block";

      const timingBox = document.getElementById("videoStickerTimingContainer");
      if (timingBox) {
        timingBox.style.display = (currentMode === "video" && activeTool === "stickers") ? "block" : "none";
      }

      const drawingCanvas = document.getElementById("drawingCanvas");
      if (activeTool === "brush" || activeTool === "eraser" || activeTool === "stickers") {
        drawingCanvas.style.display = "block";
      } else {
        drawingCanvas.style.display = "none";
        commitActiveSticker();
      }
    });
  });
}

function setupModeSwitcher() {
  const photoBtn = document.getElementById("photoModeBtn");
  const videoBtn = document.getElementById("videoModeBtn");

  photoBtn.addEventListener("click", () => switchMode("photo"));
  videoBtn.addEventListener("click", () => switchMode("video"));
}

function switchMode(mode) {
  currentMode = mode;
  document.querySelectorAll(".mode-btn").forEach(btn => btn.classList.remove("active"));

  const photoFrameContainer = document.getElementById("photoFrameContainer");
  const videoSequenceContainer = document.getElementById("videoSequenceContainer");
  const presetFramesSection = document.getElementById("presetFramesSection");
  const timingBox = document.getElementById("videoStickerTimingContainer");

  const resizerHeading = document.getElementById("resizerTitleHeading");
  const resizerBtn = document.getElementById("triggerResizeBtn");

  if (timingBox) {
    timingBox.style.display = (mode === "video" && activeTool === "stickers") ? "block" : "none";
  }

  if (mode === "photo") {
    document.getElementById("photoModeBtn").classList.add("active");
    document.getElementById("videoDropzone").style.display = "none";
    document.getElementById("videoCanvasContainer").style.display = "none";

    if (photoFrameContainer) photoFrameContainer.style.display = "block";
    if (videoSequenceContainer) videoSequenceContainer.style.display = "none";
    if (presetFramesSection) presetFramesSection.style.display = "block";

    if (resizerHeading) resizerHeading.innerText = "Photo Canvas Resizer";
    if (resizerBtn) resizerBtn.innerText = "Apply Image Resize 📐";

    if (currentFile) {
      document.getElementById("dropzone").style.display = "none";
      document.getElementById("canvasContainer").style.display = "flex";
    } else {
      document.getElementById("dropzone").style.display = "block";
      document.getElementById("canvasContainer").style.display = "none";
    }
  } else {
    document.getElementById("videoModeBtn").classList.add("active");
    document.getElementById("dropzone").style.display = "none";
    document.getElementById("canvasContainer").style.display = "none";

    if (photoFrameContainer) photoFrameContainer.style.display = "none";
    if (videoSequenceContainer) videoSequenceContainer.style.display = "block";
    if (presetFramesSection) presetFramesSection.style.display = "none";

    if (resizerHeading) resizerHeading.innerText = "Video & GIF Media Resizer";
    if (resizerBtn) resizerBtn.innerText = "Apply Video / GIF Resize 🎥";

    if (currentVideoFile || videoClips.length > 0) {
      document.getElementById("videoDropzone").style.display = "none";
      document.getElementById("videoCanvasContainer").style.display = "flex";
    } else {
      document.getElementById("videoDropzone").style.display = "block";
      document.getElementById("videoCanvasContainer").style.display = "none";
    }
  }
}

function setupDrawingCanvas() {
  drawCanvas = document.getElementById("drawingCanvas");
  drawCtx = drawCanvas.getContext("2d");

  inpaintMaskCanvas = document.createElement("canvas");
  inpaintMaskCtx = inpaintMaskCanvas.getContext("2d");

  stickerCommittedCanvas = document.createElement("canvas");
  stickerCommittedCtx = stickerCommittedCanvas.getContext("2d");

  const startDraw = (x, y) => {
    if (activeTool === "stickers") {
      if (activeStickerObj) {
        const hit = hitTestStickerTransformControls(x, y, activeStickerObj);
        if (hit) {
          activeTransformMode = hit;
          transformStartCoords = { x, y };
          transformStartObjState = { ...activeStickerObj };
          return;
        }
      }

      commitActiveSticker();

      const scale = parseInt(document.getElementById("sliderStickerScale").value);
      const cropShape = document.getElementById("stickerCropSelect").value;

      let w = scale;
      let h = scale;
      if (activeStickerType === "custom" && customStickerImg) {
        h = (customStickerImg.height / customStickerImg.width) * w;
      }

      activeStickerObj = {
        x: x,
        y: y,
        width: w,
        height: h,
        rotation: 0,
        type: activeStickerType,
        emoji: activeEmojiSticker || "🎨",
        img: customStickerImg,
        cropShape: cropShape
      };

      activeTransformMode = 'move';
      transformStartCoords = { x, y };
      transformStartObjState = { ...activeStickerObj };

      redrawOverlayCanvas();
      return;
    }

    isDrawing = true;
    commitActiveSticker();

    stickerCommittedCtx.beginPath();
    stickerCommittedCtx.moveTo(x, y);

    if (activeTool === "eraser") {
      inpaintMaskCtx.beginPath();
      inpaintMaskCtx.moveTo(x, y);
    }
  };

  const drawMove = (x, y) => {
    if (activeTool === "stickers" && activeTransformMode && activeStickerObj) {
      const dx = x - transformStartCoords.x;
      const dy = y - transformStartCoords.y;

      if (activeTransformMode === "move") {
        activeStickerObj.x = transformStartObjState.x + dx;
        activeStickerObj.y = transformStartObjState.y + dy;

      } else if (activeTransformMode === "resize") {
        const distCenter = Math.hypot(x - activeStickerObj.x, y - activeStickerObj.y);
        const newScale = Math.max(20, Math.min(300, distCenter * 2));
        activeStickerObj.width = newScale;
        
        if (activeStickerObj.type === "custom" && activeStickerObj.img) {
          activeStickerObj.height = (activeStickerObj.img.height / activeStickerObj.img.width) * newScale;
        } else {
          activeStickerObj.height = newScale;
        }

        document.getElementById("sliderStickerScale").value = Math.round(newScale);
        document.getElementById("valStickerScale").innerText = `${Math.round(newScale)}px`;

      } else if (activeTransformMode === "rotate") {
        const angle = Math.atan2(y - activeStickerObj.y, x - activeStickerObj.x);
        activeStickerObj.rotation = angle + Math.PI / 2;
      }

      redrawOverlayCanvas();
      return;
    }

    if (!isDrawing) return;

    if (activeTool === "brush") {
      const color = document.getElementById("brushColorPicker").value;
      const size = parseInt(document.getElementById("sliderBrushSize").value);
      const style = document.getElementById("brushStyleSelect").value;

      stickerCommittedCtx.save();

      if (style === "round") {
        stickerCommittedCtx.strokeStyle = color;
        stickerCommittedCtx.lineWidth = size;
        stickerCommittedCtx.lineCap = "round";
        stickerCommittedCtx.lineJoin = "round";
        stickerCommittedCtx.lineTo(x, y);
        stickerCommittedCtx.stroke();
      } else if (style === "neon") {
        stickerCommittedCtx.shadowColor = color;
        stickerCommittedCtx.shadowBlur = size * 1.5;
        stickerCommittedCtx.strokeStyle = "#ffffff";
        stickerCommittedCtx.lineWidth = size * 0.7;
        stickerCommittedCtx.lineCap = "round";
        stickerCommittedCtx.lineTo(x, y);
        stickerCommittedCtx.stroke();
      } else if (style === "chisel") {
        stickerCommittedCtx.fillStyle = color;
        for (let i = 0; i < 5; i++) {
          stickerCommittedCtx.fillRect(x + i * 2, y - i * 2, size * 0.4, size);
        }
      } else if (style === "spray") {
        stickerCommittedCtx.fillStyle = color;
        const radius = size * 1.2;
        for (let i = 0; i < 15; i++) {
          const offsetX = (Math.random() - 0.5) * radius * 2;
          const offsetY = (Math.random() - 0.5) * radius * 2;
          stickerCommittedCtx.fillRect(x + offsetX, y + offsetY, 2, 2);
        }
      } else if (style === "marker") {
        stickerCommittedCtx.globalAlpha = 0.4;
        stickerCommittedCtx.strokeStyle = color;
        stickerCommittedCtx.lineWidth = size * 1.5;
        stickerCommittedCtx.lineCap = "square";
        stickerCommittedCtx.lineTo(x, y);
        stickerCommittedCtx.stroke();
      }

      stickerCommittedCtx.restore();
      redrawOverlayCanvas();

    } else if (activeTool === "eraser") {
      const size = parseInt(document.getElementById("sliderEraserSize").value);
      
      stickerCommittedCtx.strokeStyle = "rgba(255, 0, 68, 0.7)";
      stickerCommittedCtx.lineWidth = size;
      stickerCommittedCtx.lineCap = "round";
      stickerCommittedCtx.lineTo(x, y);
      stickerCommittedCtx.stroke();

      inpaintMaskCtx.strokeStyle = "#ffffff";
      inpaintMaskCtx.lineWidth = size;
      inpaintMaskCtx.lineCap = "round";
      inpaintMaskCtx.lineTo(x, y);
      inpaintMaskCtx.stroke();

      redrawOverlayCanvas();
    }
  };

  const stopDraw = () => {
    if (activeTransformMode) {
      activeTransformMode = null;
      pushHistoryState();
    }
    if (isDrawing && activeTool === "brush") {
      pushHistoryState();
    }
    isDrawing = false;
  };

  const getCanvasCoords = (e) => {
    const rect = drawCanvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: (clientX - rect.left) * (drawCanvas.width / rect.width),
      y: (clientY - rect.top) * (drawCanvas.height / rect.height)
    };
  };

  drawCanvas.addEventListener("mousedown", (e) => {
    const coords = getCanvasCoords(e);
    startDraw(coords.x, coords.y);
  });
  drawCanvas.addEventListener("mousemove", (e) => {
    const coords = getCanvasCoords(e);
    drawMove(coords.x, coords.y);
  });
  window.addEventListener("mouseup", stopDraw);

  drawCanvas.addEventListener("touchstart", (e) => {
    const coords = getCanvasCoords(e);
    startDraw(coords.x, coords.y);
  });
  drawCanvas.addEventListener("touchmove", (e) => {
    const coords = getCanvasCoords(e);
    drawMove(coords.x, coords.y);
  });
  window.addEventListener("touchend", stopDraw);

  document.getElementById("clearBrushBtn").addEventListener("click", () => {
    stickerCommittedCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    activeStickerObj = null;
    redrawOverlayCanvas();
    pushHistoryState();
  });

  document.getElementById("clearEraserMaskBtn").addEventListener("click", () => {
    stickerCommittedCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    inpaintMaskCtx.fillStyle = "#000000";
    inpaintMaskCtx.fillRect(0, 0, inpaintMaskCanvas.width, inpaintMaskCanvas.height);
    activeStickerObj = null;
    redrawOverlayCanvas();
  });

  document.getElementById("commitStickerBtn").addEventListener("click", () => {
    commitActiveSticker();
  });

  document.getElementById("deleteStickerBtn").addEventListener("click", () => {
    activeStickerObj = null;
    redrawOverlayCanvas();
    pushHistoryState();
  });

  document.getElementById("triggerInpaintBtn").addEventListener("click", () => {
    triggerInpaintEraser();
  });
}

function redrawOverlayCanvas() {
  drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  drawCtx.drawImage(stickerCommittedCanvas, 0, 0);

  if (activeStickerObj) {
    drawStickerObjectWithTransformControls(drawCtx, activeStickerObj);
  }
}

function commitActiveSticker() {
  if (!activeStickerObj) return;

  renderStickerContentOnly(stickerCommittedCtx, activeStickerObj);

  if (currentMode === "video") {
    const startSec = parseFloat(document.getElementById("stickerStartSec")?.value || "0");
    const endSecVal = document.getElementById("stickerEndSec")?.value;
    const endSec = (endSecVal !== undefined && endSecVal !== "" && endSecVal !== null) ? parseFloat(endSecVal) : null;

    videoStickerList.push({
      type: activeStickerObj.type,
      emoji: activeStickerObj.emoji,
      x: activeStickerObj.x,
      y: activeStickerObj.y,
      width: activeStickerObj.width,
      height: activeStickerObj.height,
      rotation: activeStickerObj.rotation,
      cropShape: activeStickerObj.cropShape,
      start_time: startSec,
      end_time: endSec
    });
  }

  activeStickerObj = null;
  redrawOverlayCanvas();
  pushHistoryState();
}

function renderStickerContentOnly(ctx, obj) {
  ctx.save();
  ctx.translate(obj.x, obj.y);
  ctx.rotate(obj.rotation);

  const halfW = obj.width / 2;
  const halfH = obj.height / 2;

  if (obj.type === "custom" && obj.img) {
    if (obj.cropShape === "circle") {
      ctx.beginPath();
      ctx.arc(0, 0, halfW, 0, Math.PI * 2);
      ctx.clip();
    } else if (obj.cropShape === "square") {
      ctx.beginPath();
      ctx.rect(-halfW, -halfW, obj.width, obj.width);
      ctx.clip();
    } else if (obj.cropShape === "diamond") {
      ctx.beginPath();
      ctx.moveTo(0, -halfH);
      ctx.lineTo(halfW, 0);
      ctx.lineTo(0, halfH);
      ctx.lineTo(-halfW, 0);
      ctx.closePath();
      ctx.clip();
    }
    ctx.drawImage(obj.img, -halfW, -halfH, obj.width, obj.height);

  } else {
    ctx.font = `${obj.width}px serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(obj.emoji, 0, 0);
  }

  ctx.restore();
}

function drawStickerObjectWithTransformControls(ctx, obj) {
  renderStickerContentOnly(ctx, obj);

  ctx.save();
  ctx.translate(obj.x, obj.y);
  ctx.rotate(obj.rotation);

  const halfW = obj.width / 2;
  const halfH = obj.height / 2;
  const pad = 8;

  ctx.strokeStyle = "#00f2fe";
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 4]);
  ctx.strokeRect(-halfW - pad, -halfH - pad, obj.width + pad * 2, obj.height + pad * 2);

  ctx.setLineDash([]);
  ctx.fillStyle = "#00f2fe";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;

  const corners = [
    { x: -halfW - pad, y: -halfH - pad },
    { x: halfW + pad, y: -halfH - pad },
    { x: -halfW - pad, y: halfH + pad },
    { x: halfW + pad, y: halfH + pad }
  ];

  corners.forEach(c => {
    ctx.beginPath();
    ctx.arc(c.x, c.y, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  });

  const rotLineY = -halfH - pad - 25;
  ctx.beginPath();
  ctx.moveTo(0, -halfH - pad);
  ctx.lineTo(0, rotLineY);
  ctx.strokeStyle = "#00f2fe";
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(0, rotLineY, 7, 0, Math.PI * 2);
  ctx.fillStyle = "#ff0844";
  ctx.fill();
  ctx.stroke();

  ctx.restore();
}

function hitTestStickerTransformControls(px, py, obj) {
  const dx = px - obj.x;
  const dy = py - obj.y;

  const cos = Math.cos(-obj.rotation);
  const sin = Math.sin(-obj.rotation);
  const lx = dx * cos - dy * sin;
  const ly = dx * sin + dy * cos;

  const halfW = obj.width / 2;
  const halfH = obj.height / 2;
  const pad = 8;

  const rotY = -halfH - pad - 25;
  if (Math.hypot(lx - 0, ly - rotY) <= 15) {
    return "rotate";
  }

  const corners = [
    { x: -halfW - pad, y: -halfH - pad },
    { x: halfW + pad, y: -halfH - pad },
    { x: -halfW - pad, y: halfH + pad },
    { x: halfW + pad, y: halfH + pad }
  ];

  for (const c of corners) {
    if (Math.hypot(lx - c.x, ly - c.y) <= 15) {
      return "resize";
    }
  }

  if (lx >= -halfW - pad && lx <= halfW + pad && ly >= -halfH - pad && ly <= halfH + pad) {
    return "move";
  }

  return null;
}

function resizeDrawingCanvas(width, height) {
  drawCanvas.width = width;
  drawCanvas.height = height;
  inpaintMaskCanvas.width = width;
  inpaintMaskCanvas.height = height;

  stickerCommittedCanvas.width = width;
  stickerCommittedCanvas.height = height;

  inpaintMaskCtx.fillStyle = "#000000";
  inpaintMaskCtx.fillRect(0, 0, width, height);

  redrawOverlayCanvas();
}

function setupStickerGrid() {
  document.querySelectorAll(".sticker-item").forEach(item => {
    item.addEventListener("click", () => {
      document.querySelectorAll(".sticker-item").forEach(i => i.classList.remove("active"));
      item.classList.add("active");
      activeStickerType = "emoji";
      activeEmojiSticker = item.innerText;
    });
  });

  const stickerScaleSlider = document.getElementById("sliderStickerScale");
  stickerScaleSlider.addEventListener("input", (e) => {
    document.getElementById("valStickerScale").innerText = `${e.target.value}px`;
    if (activeStickerObj) {
      const scale = parseInt(e.target.value);
      activeStickerObj.width = scale;
      if (activeStickerObj.type === "custom" && activeStickerObj.img) {
        activeStickerObj.height = (activeStickerObj.img.height / activeStickerObj.img.width) * scale;
      } else {
        activeStickerObj.height = scale;
      }
      redrawOverlayCanvas();
    }
  });

  const stickerCropSelect = document.getElementById("stickerCropSelect");
  stickerCropSelect.addEventListener("change", (e) => {
    if (activeStickerObj) {
      activeStickerObj.cropShape = e.target.value;
      redrawOverlayCanvas();
    }
  });

  const customStickerInput = document.getElementById("customStickerInput");
  customStickerInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => {
          customStickerImg = img;
          activeStickerType = "custom";
          document.querySelectorAll(".sticker-item").forEach(i => i.classList.remove("active"));
          document.getElementById("uploadStickerBtn").innerText = `Media Sticker Loaded ✓ (${file.name})`;
        };
        img.src = event.target.result;
      };
      reader.readAsDataURL(file);
    }
  });
}

function setupFrameControls() {
  const sliderGap = document.getElementById("sliderFrameGap");
  const sliderItemSize = document.getElementById("sliderFrameItemSize");
  const sliderPadding = document.getElementById("sliderFramePadding");

  sliderGap.addEventListener("input", (e) => {
    document.getElementById("valFrameGap").innerText = `${e.target.value}px`;
  });
  sliderItemSize.addEventListener("input", (e) => {
    document.getElementById("valFrameItemSize").innerText = `${e.target.value}px`;
  });
  sliderPadding.addEventListener("input", (e) => {
    document.getElementById("valFramePadding").innerText = `${e.target.value}px`;
  });

  const patternInput = document.getElementById("patternFrameFileInput");
  patternInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      customPatternFrameFile = e.target.files[0];
      document.getElementById("uploadPatternFrameBtn").innerText = `Pattern Loaded ✓ (${customPatternFrameFile.name})`;
    }
  });

  document.getElementById("applyPatternFrameBtn").addEventListener("click", () => {
    triggerCustomPatternFrame();
  });
}

function setupVideoSequenceControls() {
  const clipInput = document.getElementById("videoClipInput");
  const renderBtn = document.getElementById("renderVideoSequenceBtn");

  clipInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      for (let i = 0; i < e.target.files.length; i++) {
        videoClips.push({
          id: Date.now() + i,
          file: e.target.files[i],
          startTime: 0,
          endTime: ""
        });
      }
      renderVideoClipList();

      if (!currentVideoFile && videoClips.length > 0) {
        handleVideoSelect(videoClips[0].file);
      }
    }
  });

  renderBtn.addEventListener("click", () => {
    renderVideoSequence();
  });
}

function renderVideoClipList() {
  const listEl = document.getElementById("videoClipList");
  listEl.innerHTML = "";

  if (videoClips.length === 0) {
    listEl.innerHTML = `<p style="font-size: 0.75rem; color: var(--text-muted); text-align: center;">No video clips added yet.</p>`;
    return;
  }

  videoClips.forEach((clip, idx) => {
    const card = document.createElement("div");
    card.className = "params-container";
    card.style.padding = "0.6rem";
    card.style.gap = "0.4rem";

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 0.8rem; font-weight: 600; color: var(--accent-cyan);">Clip ${idx + 1}: ${clip.file.name}</span>
        <div style="display: flex; gap: 0.2rem;">
          <button class="btn secondary" style="padding: 0.2rem 0.4rem; font-size: 0.7rem;" onclick="moveVideoClip(${idx}, -1)">⬆️</button>
          <button class="btn secondary" style="padding: 0.2rem 0.4rem; font-size: 0.7rem;" onclick="moveVideoClip(${idx}, 1)">⬇️</button>
          <button class="btn secondary" style="padding: 0.2rem 0.4rem; font-size: 0.7rem;" onclick="deleteVideoClip(${idx})">🗑️</button>
        </div>
      </div>
      <div style="display: flex; gap: 0.4rem;">
        <div class="param-field" style="flex: 1;">
          <label style="font-size: 0.72rem;">Start Trim (s)</label>
          <input type="number" step="0.5" min="0" value="${clip.startTime}" style="background: rgba(15,23,42,0.9); color:#fff; border:1px solid var(--panel-border); padding:0.25rem; border-radius:4px; font-size:0.75rem;" onchange="updateClipTrim(${idx}, 'startTime', this.value)">
        </div>
        <div class="param-field" style="flex: 1;">
          <label style="font-size: 0.72rem;">End Trim (s)</label>
          <input type="number" step="0.5" min="0" placeholder="Full" value="${clip.endTime}" style="background: rgba(15,23,42,0.9); color:#fff; border:1px solid var(--panel-border); padding:0.25rem; border-radius:4px; font-size:0.75rem;" onchange="updateClipTrim(${idx}, 'endTime', this.value)">
        </div>
      </div>
    `;

    listEl.appendChild(card);
  });
}

function moveVideoClip(idx, direction) {
  const targetIdx = idx + direction;
  if (targetIdx < 0 || targetIdx >= videoClips.length) return;
  const temp = videoClips[idx];
  videoClips[idx] = videoClips[targetIdx];
  videoClips[targetIdx] = temp;
  renderVideoClipList();
}

function deleteVideoClip(idx) {
  videoClips.splice(idx, 1);
  renderVideoClipList();
  renderTimelineTracks();
}

function updateClipTrim(idx, key, val) {
  if (videoClips[idx]) {
    videoClips[idx][key] = val;
  }
}

async function renderVideoSequence() {
  if (videoClips.length === 0) {
    alert("Please add at least one video clip first!");
    return;
  }

  const indicator = document.getElementById("videoStatusIndicator");
  const progressContainer = document.getElementById("videoProgressContainer");
  const progressBar = document.getElementById("videoProgressBar");
  const progressText = document.getElementById("videoProgressText");

  indicator.innerText = "Stitching & Rendering Video Sequence...";
  indicator.style.color = "var(--accent-cyan)";
  progressContainer.style.display = "block";
  progressBar.style.width = "40%";
  progressText.innerText = "Stitching multi-clip video timeline...";

  const formData = new FormData();
  const clipsMeta = [];

  videoClips.forEach((clip) => {
    formData.append("files", clip.file);
    clipsMeta.push({
      start_time: parseFloat(clip.startTime || 0.0),
      end_time: clip.endTime !== "" && clip.endTime !== null ? parseFloat(clip.endTime) : null
    });
  });

  formData.append("clips_meta", JSON.stringify(clipsMeta));
  formData.append("effect", activeEffectKey);
  formData.append("params", JSON.stringify(currentParams));
  formData.append("stickers", JSON.stringify(videoStickerList));

  try {
    const res = await fetch("/api/process-video-sequence", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Video sequence stitching failed: ${errText}`);
    }

    progressBar.style.width = "90%";
    progressText.innerText = "Encoding final stitched MP4 sequence...";

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    const styledVideoPlayer = document.getElementById("styledVideoPlayer");
    const styledGifPlayer = document.getElementById("styledGifPlayer");
    const downloadBtn = document.getElementById("videoDownloadBtn");

    styledGifPlayer.style.display = "none";
    styledVideoPlayer.style.display = "block";
    styledVideoPlayer.src = objectUrl;
    styledVideoPlayer.load();
    styledVideoPlayer.play().catch(() => {});

    downloadBtn.download = `artcv_stitched_sequence_${activeEffectKey}.mp4`;
    downloadBtn.href = objectUrl;

    progressBar.style.width = "100%";
    progressText.innerText = "Sequence Stitching Complete!";

    setTimeout(() => {
      progressContainer.style.display = "none";
    }, 1200);

    indicator.innerText = "Completed ✓";
    indicator.style.color = "#10b981";
  } catch (err) {
    console.error(err);
    indicator.innerText = "Sequence Error ❌";
    indicator.style.color = "var(--accent-pink)";
    progressText.innerText = err.message || "Video sequence error";
  }
}

async function triggerCustomPatternFrame() {
  if (!currentFile) return;

  if (!customPatternFrameFile) {
    alert("Please upload a pattern image file first!");
    return;
  }

  const indicator = document.getElementById("statusIndicator");
  indicator.innerText = "Generating Pattern Frame...";
  indicator.style.color = "var(--accent-cyan)";

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("pattern", customPatternFrameFile);
  formData.append("gap_spacing", document.getElementById("sliderFrameGap").value);
  formData.append("item_size", document.getElementById("sliderFrameItemSize").value);
  formData.append("padding", document.getElementById("sliderFramePadding").value);

  try {
    const res = await fetch("/api/pattern-frame", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Pattern frame generation failed");

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    currentFile = new File([blob], currentFile.name, { type: "image/jpeg" });
    document.getElementById("styledImg").src = objectUrl;
    document.getElementById("downloadBtn").href = objectUrl;

    pushHistoryState();

    indicator.innerText = "Pattern Frame Applied ✓";
    indicator.style.color = "#10b981";
  } catch (err) {
    console.error(err);
    indicator.innerText = "Pattern Frame Error ❌";
    indicator.style.color = "var(--accent-pink)";
  }
}

function setupEnhancerControls() {
  const sliders = [
    { id: "sliderBrightness", label: "valBrightness" },
    { id: "sliderContrast", label: "valContrast" },
    { id: "sliderSaturation", label: "valSaturation" },
    { id: "sliderSharpness", label: "valSharpness" },
    { id: "sliderWarmth", label: "valWarmth" }
  ];

  sliders.forEach(s => {
    const el = document.getElementById(s.id);
    const lbl = document.getElementById(s.label);
    el.addEventListener("input", (e) => {
      lbl.innerText = e.target.value;
    });
  });

  document.getElementById("applyEnhanceBtn").addEventListener("click", () => {
    triggerEnhancer();
  });

  document.getElementById("revertEnhanceBtn").addEventListener("click", () => {
    revertEnhancements();
  });

  document.getElementById("sliderBrushSize").addEventListener("input", (e) => {
    document.getElementById("valBrushSize").innerText = `${e.target.value}px`;
  });

  document.getElementById("sliderEraserSize").addEventListener("input", (e) => {
    document.getElementById("valEraserSize").innerText = `${e.target.value}px`;
  });

  const sliderInpaintRadius = document.getElementById("sliderInpaintRadius");
  if (sliderInpaintRadius) {
    sliderInpaintRadius.addEventListener("input", (e) => {
      document.getElementById("valInpaintRadius").innerText = `${e.target.value}px`;
    });
  }

  const sliderMaskDilation = document.getElementById("sliderMaskDilation");
  if (sliderMaskDilation) {
    sliderMaskDilation.addEventListener("input", (e) => {
      document.getElementById("valMaskDilation").innerText = `${e.target.value}px`;
    });
  }
}

function revertEnhancements() {
  if (!baseFile) return;

  const sliderIds = ["sliderBrightness", "sliderContrast", "sliderSaturation", "sliderSharpness", "sliderWarmth"];
  const valIds = ["valBrightness", "valContrast", "valSaturation", "valSharpness", "valWarmth"];

  sliderIds.forEach((id, idx) => {
    document.getElementById(id).value = 0;
    document.getElementById(valIds[idx]).innerText = "0";
  });

  currentFile = baseFile;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById("originalImg").src = e.target.result;
    document.getElementById("styledImg").src = e.target.result;
    document.getElementById("downloadBtn").href = e.target.result;
    pushHistoryState();

    const indicator = document.getElementById("statusIndicator");
    indicator.innerText = "Reverted 🔄";
    indicator.style.color = "var(--accent-cyan)";
  };
  reader.readAsDataURL(baseFile);
}

async function triggerEnhancer() {
  if (!currentFile) return;

  const indicator = document.getElementById("statusIndicator");
  indicator.innerText = "Enhancing...";
  indicator.style.color = "var(--accent-cyan)";

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("brightness", document.getElementById("sliderBrightness").value);
  formData.append("contrast", document.getElementById("sliderContrast").value);
  formData.append("saturation", document.getElementById("sliderSaturation").value);
  formData.append("sharpness", document.getElementById("sliderSharpness").value);
  formData.append("warmth", document.getElementById("sliderWarmth").value);

  try {
    const res = await fetch("/api/enhance", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Enhancement failed");

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    currentFile = new File([blob], currentFile.name, { type: "image/jpeg" });
    document.getElementById("originalImg").src = objectUrl;
    document.getElementById("styledImg").src = objectUrl;
    document.getElementById("downloadBtn").href = objectUrl;

    pushHistoryState();

    indicator.innerText = "Enhanced ✓";
    indicator.style.color = "#10b981";
  } catch (err) {
    console.error(err);
    indicator.innerText = "Error ❌";
    indicator.style.color = "var(--accent-pink)";
  }
}

async function triggerInpaintEraser() {
  if (!currentFile) return;

  const indicator = document.getElementById("statusIndicator");
  indicator.innerText = "Erasing Object...";
  indicator.style.color = "var(--accent-cyan)";

  inpaintMaskCanvas.toBlob(async (maskBlob) => {
    const formData = new FormData();
    formData.append("file", currentFile);
    formData.append("mask", maskBlob, "mask.png");
    formData.append("radius", document.getElementById("sliderInpaintRadius").value);
    formData.append("method", document.getElementById("eraserMethodSelect").value);
    formData.append("dilation", document.getElementById("sliderMaskDilation").value);

    try {
      const res = await fetch("/api/inpaint", { method: "POST", body: formData });
      if (!res.ok) {
        const errTxt = await res.text();
        throw new Error(`Inpainting failed: ${errTxt}`);
      }

      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);

      currentFile = new File([blob], currentFile.name, { type: "image/jpeg" });
      document.getElementById("originalImg").src = objectUrl;
      document.getElementById("styledImg").src = objectUrl;
      document.getElementById("downloadBtn").href = objectUrl;

      stickerCommittedCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
      inpaintMaskCtx.fillStyle = "#000000";
      inpaintMaskCtx.fillRect(0, 0, inpaintMaskCanvas.width, inpaintMaskCanvas.height);
      activeStickerObj = null;

      redrawOverlayCanvas();
      pushHistoryState();

      indicator.innerText = "Object Erased ✓";
      indicator.style.color = "#10b981";
    } catch (err) {
      console.error(err);
      indicator.innerText = "Eraser Error ❌";
      indicator.style.color = "var(--accent-pink)";
    }
  }, "image/png");
}

async function applyFrameChoice(frameType) {
  if (!currentFile) return;

  const indicator = document.getElementById("statusIndicator");
  indicator.innerText = "Applying Frame...";
  indicator.style.color = "var(--accent-cyan)";

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("frame_type", frameType);

  try {
    const res = await fetch("/api/frame", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Frame application failed");

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    currentFile = new File([blob], currentFile.name, { type: "image/jpeg" });
    document.getElementById("styledImg").src = objectUrl;
    document.getElementById("downloadBtn").href = objectUrl;

    pushHistoryState();

    indicator.innerText = "Frame Applied ✓";
    indicator.style.color = "#10b981";
  } catch (err) {
    console.error(err);
    indicator.innerText = "Frame Error ❌";
    indicator.style.color = "var(--accent-pink)";
  }
}

function renderCategoryTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const category = tab.getAttribute("data-cat");
      renderEffectsGrid(category);
    });
  });
}

function renderEffectsGrid(category) {
  const grid = document.getElementById("effectsGrid");
  grid.innerHTML = "";

  Object.entries(catalog).forEach(([key, info]) => {
    if (category !== "All" && info.category !== category) return;

    const card = document.createElement("div");
    card.className = `effect-card ${key === activeEffectKey ? 'active' : ''}`;
    card.innerHTML = `
      <div class="effect-card-preview">
        <img src="/previews/${key}.jpg" alt="${info.name}" onerror="this.src='/previews/pencil_sketch.jpg'">
      </div>
      <h4>${info.name}</h4>
      <p>${info.description}</p>
    `;
    card.addEventListener("click", () => selectEffect(key));
    grid.appendChild(card);
  });
}

function selectEffect(key) {
  if (!catalog[key]) return;
  activeEffectKey = key;
  currentParams = {};

  document.querySelectorAll(".effect-card").forEach(card => {
    card.classList.remove("active");
  });
  renderEffectsGrid(document.querySelector(".tab-btn.active")?.getAttribute("data-cat") || "All");

  document.getElementById("currentEffectName").innerText = catalog[key].name;
  document.getElementById("videoCurrentEffectName").innerText = catalog[key].name;
  renderParamsUI(catalog[key].params);

  if (currentMode === "photo" && currentFile && activeTool === "filters") {
    processImage();
  } else if (currentMode === "video" && currentVideoFile) {
    processVideo();
  }
}

function renderParamsUI(paramsSpec) {
  const container = document.getElementById("paramsContainer");
  container.innerHTML = "";

  const keys = Object.keys(paramsSpec);
  if (keys.length === 0) return;

  keys.forEach(pKey => {
    const spec = paramsSpec[pKey];
    currentParams[pKey] = spec.default;

    const field = document.createElement("div");
    field.className = "param-field";

    if (spec.type === "int" || spec.type === "float") {
      const valLabel = document.createElement("span");
      valLabel.innerText = spec.default;

      const label = document.createElement("label");
      label.innerText = spec.label;
      label.appendChild(valLabel);

      const input = document.createElement("input");
      input.type = "range";
      input.min = spec.min;
      input.max = spec.max;
      input.step = spec.type === "float" ? "0.1" : "1";
      input.value = spec.default;

      input.addEventListener("input", (e) => {
        const val = spec.type === "float" ? parseFloat(e.target.value) : parseInt(e.target.value);
        valLabel.innerText = val;
        currentParams[pKey] = val;

        if (currentMode === "photo" && currentFile) {
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
            processImage();
          }, 150);
        }
      });

      field.appendChild(label);
      field.appendChild(input);
    } else if (spec.type === "select") {
      const label = document.createElement("label");
      label.innerText = spec.label;

      const select = document.createElement("select");
      spec.options.forEach(opt => {
        const option = document.createElement("option");
        option.value = opt;
        option.innerText = opt;
        if (opt === spec.default) option.selected = true;
        select.appendChild(option);
      });

      select.addEventListener("change", (e) => {
        currentParams[pKey] = e.target.value;
        if (currentMode === "photo" && currentFile) {
          processImage();
        } else if (currentMode === "video" && currentVideoFile) {
          processVideo();
        }
      });

      field.appendChild(label);
      field.appendChild(select);
    }

    container.appendChild(field);
  });
}

function setupEvents() {
  const fileInput = document.getElementById("fileInput");
  const dropzone = document.getElementById("dropzone");
  const reuploadBtn = document.getElementById("reuploadBtn");

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--accent-cyan)";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
  });

  reuploadBtn.addEventListener("click", () => {
    document.getElementById("canvasContainer").style.display = "none";
    document.getElementById("dropzone").style.display = "block";
    fileInput.value = "";
    currentFile = null;
    baseFile = null;
    historyStack = [];
    redoStack = [];
    activeStickerObj = null;
    updateUndoRedoUI();
  });

  // Video/GIF events
  const videoFileInput = document.getElementById("videoFileInput");
  const videoDropzone = document.getElementById("videoDropzone");
  const videoReuploadBtn = document.getElementById("videoReuploadBtn");

  videoFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleVideoSelect(e.target.files[0]);
  });

  videoDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    videoDropzone.style.borderColor = "var(--accent-cyan)";
  });

  videoDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) handleVideoSelect(e.dataTransfer.files[0]);
  });

  videoReuploadBtn.addEventListener("click", () => {
    document.getElementById("videoCanvasContainer").style.display = "none";
    document.getElementById("videoDropzone").style.display = "block";
    videoFileInput.value = "";
    currentVideoFile = null;
  });

  setupComparisonSlider();
}

function handleFileSelect(file) {
  baseFile = file;
  currentFile = file;
  historyStack = [];
  redoStack = [];
  activeStickerObj = null;

  const reader = new FileReader();
  reader.onload = (e) => {
    const imgEl = document.getElementById("originalImg");
    imgEl.src = e.target.result;
    
    imgEl.onload = () => {
      resizeDrawingCanvas(imgEl.naturalWidth || 800, imgEl.naturalHeight || 600);
      pushHistoryState();
    };

    document.getElementById("dropzone").style.display = "none";
    document.getElementById("canvasContainer").style.display = "flex";
    processImage();
  };
  reader.readAsDataURL(file);
}

function handleVideoSelect(file) {
  currentVideoFile = file;
  const objectUrl = URL.createObjectURL(file);
  const isGif = file.name.toLowerCase().endsWith(".gif") || file.type === "image/gif";

  const origVideo = document.getElementById("originalVideoPlayer");
  const origGif = document.getElementById("originalGifPlayer");

  if (isGif) {
    origVideo.style.display = "none";
    origGif.style.display = "block";
    origGif.src = objectUrl;
  } else {
    origGif.style.display = "none";
    origVideo.style.display = "block";
    origVideo.src = objectUrl;
    origVideo.load();
  }

  document.getElementById("videoDropzone").style.display = "none";
  document.getElementById("videoCanvasContainer").style.display = "flex";
  processVideo();
}

async function processImage() {
  if (!currentFile) return;

  const indicator = document.getElementById("statusIndicator");
  indicator.innerText = "Processing...";
  indicator.style.color = "var(--accent-cyan)";

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("effect", activeEffectKey);
  formData.append("params", JSON.stringify(currentParams));

  try {
    const res = await fetch("/api/process", {
      method: "POST",
      body: formData
    });

    if (!res.ok) throw new Error("Image processing failed");

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    
    document.getElementById("styledImg").src = objectUrl;
    document.getElementById("downloadBtn").href = objectUrl;

    pushHistoryState();

    indicator.innerText = "Completed ✓";
    indicator.style.color = "#10b981";
  } catch (err) {
    console.error(err);
    indicator.innerText = "Error ❌";
    indicator.style.color = "var(--accent-pink)";
  }
}

async function processVideo() {
  if (!currentVideoFile) return;

  const indicator = document.getElementById("videoStatusIndicator");
  const progressContainer = document.getElementById("videoProgressContainer");
  const progressBar = document.getElementById("videoProgressBar");
  const progressText = document.getElementById("videoProgressText");

  const isGif = currentVideoFile.name.toLowerCase().endsWith(".gif") || currentVideoFile.type === "image/gif";

  indicator.innerText = isGif ? "Rendering Animated GIF..." : "Rendering Video Frames...";
  indicator.style.color = "var(--accent-cyan)";
  progressContainer.style.display = "block";
  progressBar.style.width = "40%";
  progressText.innerText = isGif ? "Processing GIF frames..." : "Applying frame-by-frame filter synthesis...";

  const formData = new FormData();
  formData.append("file", currentVideoFile);
  formData.append("effect", activeEffectKey);
  formData.append("params", JSON.stringify(currentParams));
  formData.append("stickers", JSON.stringify(videoStickerList));

  try {
    const res = await fetch("/api/process-video", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Video processing failed: ${errText}`);
    }

    progressBar.style.width = "90%";
    progressText.innerText = isGif ? "Assembling animated GIF..." : "Encoding video...";

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    const styledVideoPlayer = document.getElementById("styledVideoPlayer");
    const styledGifPlayer = document.getElementById("styledGifPlayer");
    const downloadBtn = document.getElementById("videoDownloadBtn");

    if (isGif || blob.type === "image/gif") {
      styledVideoPlayer.style.display = "none";
      styledGifPlayer.style.display = "block";
      styledGifPlayer.src = objectUrl;
      downloadBtn.download = `artcv_styled_${currentVideoFile.name}`;
    } else {
      styledGifPlayer.style.display = "none";
      styledVideoPlayer.style.display = "block";
      styledVideoPlayer.src = objectUrl;
      styledVideoPlayer.load();
      styledVideoPlayer.play().catch(() => {});
      downloadBtn.download = `artcv_styled_${currentVideoFile.name}`;
    }

    downloadBtn.href = objectUrl;

    progressBar.style.width = "100%";
    progressText.innerText = "Rendering Complete!";

    setTimeout(() => {
      progressContainer.style.display = "none";
    }, 1200);

    indicator.innerText = "Completed ✓";
    indicator.style.color = "#10b981";
  } catch (err) {
    console.error(err);
    indicator.innerText = "Media Error ❌";
    indicator.style.color = "var(--accent-pink)";
    progressText.innerText = err.message || "Media processing error";
  }
}

function setupComparisonSlider() {
  const slider = document.getElementById("comparisonSlider");
  const styledWrapper = document.getElementById("styledWrapper");
  const divider = document.getElementById("sliderDivider");
  let isDragging = false;

  const updateSplit = (clientX) => {
    const rect = slider.getBoundingClientRect();
    let offset = clientX - rect.left;
    offset = Math.max(0, Math.min(offset, rect.width));
    const percentage = (offset / rect.width) * 100;
    styledWrapper.style.width = `${percentage}%`;
    divider.style.left = `${percentage}%`;
  };

  divider.addEventListener("mousedown", () => isDragging = true);
  window.addEventListener("mouseup", () => isDragging = false);
  window.addEventListener("mousemove", (e) => {
    if (isDragging) updateSplit(e.clientX);
  });

  divider.addEventListener("touchstart", () => isDragging = true);
  window.addEventListener("touchend", () => isDragging = false);
  window.addEventListener("touchmove", (e) => {
    if (isDragging && e.touches.length > 0) {
      updateSplit(e.touches[0].clientX);
    }
  });
}

function setupVideoTimelineControls() {
  const styledVideo = document.getElementById("styledVideoPlayer");
  const origVideo = document.getElementById("originalVideoPlayer");
  const playhead = document.getElementById("timelinePlayhead");
  const currentTimeEl = document.getElementById("timelineCurrentTime");
  const durationEl = document.getElementById("timelineDuration");
  const trackContainer = document.getElementById("timelineTrackContainer");

  const playPauseBtn = document.getElementById("timelinePlayPauseBtn");
  const stepBackBtn = document.getElementById("timelineStepBackBtn");
  const stepFwdBtn = document.getElementById("timelineStepFwdBtn");
  const splitBtn = document.getElementById("timelineSplitBtn");

  const formatTime = (secs) => {
    if (!secs || isNaN(secs)) return "00:00.0";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 10);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
  };

  const updatePlayhead = () => {
    const video = styledVideo.style.display !== "none" ? styledVideo : origVideo;
    if (!video || !video.duration) return;

    const current = video.currentTime;
    const dur = video.duration;
    const pct = Math.max(0, Math.min(100, (current / dur) * 100));

    if (playhead) playhead.style.left = `${pct}%`;
    if (currentTimeEl) currentTimeEl.innerText = formatTime(current);
    if (durationEl) durationEl.innerText = formatTime(dur);
  };

  [styledVideo, origVideo].forEach(v => {
    if (v) {
      v.addEventListener("timeupdate", updatePlayhead);
      v.addEventListener("loadedmetadata", () => {
        updatePlayhead();
        renderTimelineTracks();
      });
    }
  });

  if (playPauseBtn) {
    playPauseBtn.addEventListener("click", () => {
      const video = styledVideo.style.display !== "none" ? styledVideo : origVideo;
      if (video.paused) {
        video.play();
        playPauseBtn.innerText = "⏸️ Pause";
      } else {
        video.pause();
        playPauseBtn.innerText = "▶ Play";
      }
    });
  }

  if (stepBackBtn) {
    stepBackBtn.addEventListener("click", () => {
      const video = styledVideo.style.display !== "none" ? styledVideo : origVideo;
      video.currentTime = Math.max(0, video.currentTime - 1.0);
    });
  }

  if (stepFwdBtn) {
    stepFwdBtn.addEventListener("click", () => {
      const video = styledVideo.style.display !== "none" ? styledVideo : origVideo;
      video.currentTime = Math.min(video.duration || 0, video.currentTime + 1.0);
    });
  }

  if (splitBtn) {
    splitBtn.addEventListener("click", () => {
      const video = styledVideo.style.display !== "none" ? styledVideo : origVideo;
      if (!video || !video.duration) return;
      const splitTime = video.currentTime;
      alert(`Clip split point added at ${formatTime(splitTime)} ✓`);
    });
  }

  if (trackContainer) {
    let isSeeking = false;
    const handleSeek = (e) => {
      const rect = trackContainer.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(1, clickX / rect.width));

      const video = styledVideo.style.display !== "none" ? styledVideo : origVideo;
      if (video && video.duration) {
        video.currentTime = pct * video.duration;
        updatePlayhead();
      }
    };

    trackContainer.addEventListener("mousedown", (e) => {
      if (e.target.classList.contains("trim-handle")) return;
      isSeeking = true;
      handleSeek(e);
    });
    window.addEventListener("mousemove", (e) => {
      if (isSeeking) handleSeek(e);
    });
    window.addEventListener("mouseup", () => isSeeking = false);
  }
}

function renderTimelineTracks() {
  const rulerTicks = document.getElementById("rulerTicksContainer");
  const clipsTrack = document.getElementById("timelineClipsTrack");
  const stickersTrack = document.getElementById("timelineStickersTrack");
  const fxTrack = document.getElementById("timelineFxTrack");

  const styledVideo = document.getElementById("styledVideoPlayer");
  const origVideo = document.getElementById("originalVideoPlayer");

  const video = styledVideo.style.display !== "none" ? styledVideo : origVideo;
  const totalDur = (video && video.duration && !isNaN(video.duration)) ? video.duration : 10.0;

  // 1. Render Timecode Ruler Ticks
  if (rulerTicks) {
    rulerTicks.innerHTML = "";
    const tickCount = Math.max(5, Math.ceil(totalDur));
    for (let i = 0; i <= tickCount; i++) {
      const pct = (i / totalDur) * 100;
      if (pct > 100) break;

      const tick = document.createElement("div");
      tick.className = "ruler-tick";
      tick.style.left = `${pct}%`;
      tick.innerText = `${i}s`;
      rulerTicks.appendChild(tick);
    }
  }

  // 2. Render V1 Video Clips Track
  if (clipsTrack) {
    clipsTrack.querySelectorAll(".timeline-segment").forEach(el => el.remove());
    if (videoClips.length > 0) {
      let accumTime = 0.0;
      videoClips.forEach((clip, idx) => {
        const seg = document.createElement("div");
        seg.className = "timeline-segment clip-seg";
        const segDur = (clip.endTime !== "" && clip.endTime !== null) ? (parseFloat(clip.endTime) - parseFloat(clip.startTime)) : (totalDur / videoClips.length);
        const startPct = (accumTime / totalDur) * 100;
        const widthPct = Math.max(6, (segDur / totalDur) * 100);

        seg.style.left = `${startPct}%`;
        seg.style.width = `${widthPct}%`;

        seg.innerHTML = `
          <div class="trim-handle left" title="Drag to trim start time"></div>
          <span style="pointer-events:none;">🎬 Clip ${idx + 1}: ${clip.file.name}</span>
          <div class="trim-handle right" title="Drag to trim end time"></div>
        `;

        clipsTrack.appendChild(seg);
        accumTime += segDur;
      });
    } else {
      const seg = document.createElement("div");
      seg.className = "timeline-segment clip-seg";
      seg.style.left = "0%";
      seg.style.width = "100%";
      seg.innerHTML = `<span style="pointer-events:none;">🎬 Main Video Track (${totalDur.toFixed(1)}s)</span>`;
      clipsTrack.appendChild(seg);
    }
  }

  // 3. Render S1 Stickers Track
  if (stickersTrack) {
    stickersTrack.querySelectorAll(".timeline-segment").forEach(el => el.remove());
    videoStickerList.forEach((st, idx) => {
      const seg = document.createElement("div");
      seg.className = "timeline-segment sticker-seg";

      const startT = st.start_time || 0.0;
      const endT = (st.end_time !== null && st.end_time !== "") ? st.end_time : totalDur;
      const startPct = (startT / totalDur) * 100;
      const durPct = Math.max(6, ((endT - startT) / totalDur) * 100);

      seg.style.left = `${startPct}%`;
      seg.style.width = `${durPct}%`;

      seg.innerHTML = `
        <div class="trim-handle left"></div>
        <span style="pointer-events:none;">⭐ ${st.emoji || 'Sticker'} (${startT}s-${endT}s)</span>
        <div class="trim-handle right"></div>
      `;

      stickersTrack.appendChild(seg);
    });
  }

  // 4. Render FX Filter Track
  if (fxTrack) {
    fxTrack.querySelectorAll(".timeline-segment").forEach(el => el.remove());
    const seg = document.createElement("div");
    seg.className = "timeline-segment fx-seg";
    seg.style.left = "0%";
    seg.style.width = "100%";
    const effectName = catalog[activeEffectKey]?.name || "Graphite Pencil Sketch";
    seg.innerHTML = `<span style="pointer-events:none;">🎨 FX: ${effectName}</span>`;
    fxTrack.appendChild(seg);
  }
}

function setupResizerControls() {
  const wInput = document.getElementById("resizeWidthInput");
  const hInput = document.getElementById("resizeHeightInput");
  const aspectLock = document.getElementById("aspectRatioLock");
  const triggerBtn = document.getElementById("triggerResizeBtn");

  let origRatio = 16 / 9;

  const updateHeightFromWidth = () => {
    if (aspectLock && aspectLock.checked && wInput && wInput.value && origRatio) {
      hInput.value = Math.round(parseInt(wInput.value) / origRatio);
    }
  };

  const updateWidthFromHeight = () => {
    if (aspectLock && aspectLock.checked && hInput && hInput.value && origRatio) {
      wInput.value = Math.round(parseInt(hInput.value) * origRatio);
    }
  };

  if (wInput) wInput.addEventListener("input", updateHeightFromWidth);
  if (hInput) hInput.addEventListener("input", updateWidthFromHeight);

  if (triggerBtn) {
    triggerBtn.addEventListener("click", () => triggerImageResize());
  }
}

async function triggerImageResize() {
  const width = document.getElementById("resizeWidthInput").value;
  const height = document.getElementById("resizeHeightInput").value;
  const interpolation = document.getElementById("resizeInterpolationSelect").value;

  if (currentMode === "video") {
    if (!currentVideoFile) {
      alert("Please upload a video or GIF media file first!");
      return;
    }

    const indicator = document.getElementById("videoStatusIndicator");
    const progressContainer = document.getElementById("videoProgressContainer");
    const progressBar = document.getElementById("videoProgressBar");
    const progressText = document.getElementById("videoProgressText");

    indicator.innerText = "Resizing Video Frames...";
    indicator.style.color = "var(--accent-cyan)";
    progressContainer.style.display = "block";
    progressBar.style.width = "40%";
    progressText.innerText = `Resizing video frames to ${width}×${height}px...`;

    const formData = new FormData();
    formData.append("file", currentVideoFile);
    formData.append("width", width);
    formData.append("height", height);
    formData.append("interpolation", interpolation);

    try {
      const res = await fetch("/api/resize-video", { method: "POST", body: formData });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Video resize failed: ${errText}`);
      }

      progressBar.style.width = "90%";
      progressText.innerText = "Encoding resized video media...";

      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);

      const isGif = currentVideoFile.name.toLowerCase().endsWith(".gif") || currentVideoFile.type === "image/gif";
      const styledVideoPlayer = document.getElementById("styledVideoPlayer");
      const styledGifPlayer = document.getElementById("styledGifPlayer");
      const downloadBtn = document.getElementById("videoDownloadBtn");

      if (isGif || blob.type === "image/gif") {
        styledVideoPlayer.style.display = "none";
        styledGifPlayer.style.display = "block";
        styledGifPlayer.src = objectUrl;
        downloadBtn.download = `artcv_resized_${width}x${height}_${currentVideoFile.name}`;
      } else {
        styledGifPlayer.style.display = "none";
        styledVideoPlayer.style.display = "block";
        styledVideoPlayer.src = objectUrl;
        styledVideoPlayer.load();
        styledVideoPlayer.play().catch(() => {});
        downloadBtn.download = `artcv_resized_${width}x${height}_${currentVideoFile.name}`;
      }

      downloadBtn.href = objectUrl;

      progressBar.style.width = "100%";
      progressText.innerText = "Video Resize Complete!";

      setTimeout(() => { progressContainer.style.display = "none"; }, 1200);

      indicator.innerText = `Video Resized to ${width}×${height}px ✓`;
      indicator.style.color = "#10b981";
    } catch (err) {
      console.error(err);
      indicator.innerText = "Video Resize Error ❌";
      indicator.style.color = "var(--accent-pink)";
      progressText.innerText = err.message || "Video resize error";
    }
    return;
  }

  if (!currentFile) {
    alert("Please upload an image file first!");
    return;
  }

  const indicator = document.getElementById("statusIndicator");
  indicator.innerText = "Resizing Image...";
  indicator.style.color = "var(--accent-cyan)";

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("width", width);
  formData.append("height", height);
  formData.append("interpolation", interpolation);

  try {
    const res = await fetch("/api/resize", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Image resize failed");

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    currentFile = new File([blob], currentFile.name, { type: "image/jpeg" });
    const imgEl = document.getElementById("styledImg");
    imgEl.src = objectUrl;
    document.getElementById("originalImg").src = objectUrl;
    document.getElementById("downloadBtn").href = objectUrl;

    imgEl.onload = () => {
      resizeDrawingCanvas(imgEl.naturalWidth, imgEl.naturalHeight);
      pushHistoryState();
    };

    indicator.innerText = `Resized to ${width}×${height}px ✓`;
    indicator.style.color = "#10b981";
  } catch (err) {
    console.error(err);
    indicator.innerText = "Resize Error ❌";
    indicator.style.color = "var(--accent-pink)";
  }
}

function applyPresetResize(w, h) {
  const wInput = document.getElementById("resizeWidthInput");
  const hInput = document.getElementById("resizeHeightInput");
  if (wInput) wInput.value = w;
  if (hInput) hInput.value = h;
  triggerImageResize();
}
