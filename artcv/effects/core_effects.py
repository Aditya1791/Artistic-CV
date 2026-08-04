"""
ArtCV 2.0 Pro Effects Engine - Advanced Computer Vision & Artistic Processing
High-fidelity artistic algorithms, texture synthesis, color grading, and edge-aware diffusion filters.
"""
import time
import math
import random
from collections import defaultdict

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from sklearn.cluster import KMeans
from scipy import stats, spatial


# Helper Utility: Generate synthetic paper texture overlay
def _apply_paper_texture(img: np.ndarray, strength: float = 0.15) -> np.ndarray:
    h, w = img.shape[:2]
    noise = np.random.normal(128, 20, (h, w)).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (3, 3), 0)
    noise_3ch = cv2.cvtColor(noise, cv2.COLOR_GRAY2BGR)
    
    img_f = img.astype(np.float32)
    blended = cv2.addWeighted(img_f, 1.0 - strength, noise_3ch * (img_f / 255.0), strength, 0)
    return np.clip(blended, 0, 255).astype(np.uint8)


# Helper Utility: Add radial vignette
def _apply_vignette(img: np.ndarray, strength: float = 0.6) -> np.ndarray:
    h, w = img.shape[:2]
    kernel_x = cv2.getGaussianKernel(w, w * strength)
    kernel_y = cv2.getGaussianKernel(h, h * strength)
    kernel = kernel_y * kernel_x.T
    mask = kernel / kernel.max()
    
    img_f = img.astype(np.float32)
    for i in range(3):
        img_f[:, :, i] *= mask
    return np.clip(img_f, 0, 255).astype(np.uint8)


# 1. ENHANCED PENCIL SKETCH (Multi-scale Difference of Gaussians + Graphite Hatching)
def pencil_sketch(img: np.ndarray, mode: str = "gray", sigma_s: int = 60, sigma_r: float = 0.07, shade_factor: float = 0.05) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    g1 = cv2.GaussianBlur(gray, (3, 3), 0)
    g2 = cv2.GaussianBlur(gray, (15, 15), 0)
    dog = cv2.subtract(g2, g1)
    
    dog_inv = cv2.bitwise_not(dog)
    dog_boost = cv2.normalize(dog_inv, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    
    inv_gray = 255 - gray
    blur_inv = cv2.GaussianBlur(inv_gray, (25, 25), 0)
    dodge = cv2.divide(gray, 255 - blur_inv, scale=256)
    
    sketch_gray = cv2.addWeighted(dog_boost, 0.4, dodge, 0.6, 0)
    sketch_gray = cv2.equalizeHist(sketch_gray)
    sketch_gray = cv2.addWeighted(sketch_gray, 0.85, cv2.GaussianBlur(sketch_gray, (3, 3), 0), 0.15, 0)
    
    if mode == "color":
        color_smooth = cv2.bilateralFilter(img, 9, 75, 75)
        sketch_3ch = cv2.cvtColor(sketch_gray, cv2.COLOR_GRAY2BGR)
        blended = cv2.multiply(color_smooth.astype(np.float32) / 255.0, sketch_3ch.astype(np.float32) / 255.0) * 255.0
        return np.clip(blended, 0, 255).astype(np.uint8)
        
    return cv2.cvtColor(sketch_gray, cv2.COLOR_GRAY2BGR)


# 2. ENHANCED OIL PAINTING (Anisotropic Flow + Impasto Texture)
def oil_painting(img: np.ndarray, size: int = 4, dyn_ratio: int = 2) -> np.ndarray:
    size = max(1, min(int(size), 10))
    dyn_ratio = max(1, min(int(dyn_ratio), 10))
    
    try:
        if hasattr(cv2, 'xphoto') and hasattr(cv2.xphoto, 'oilPainting'):
            oil = cv2.xphoto.oilPainting(img, size, dyn_ratio)
            gray = cv2.cvtColor(oil, cv2.COLOR_BGR2GRAY)
            sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            relief = cv2.addWeighted(sobelx, 0.1, sobely, 0.1, 128).astype(np.uint8)
            relief_3ch = cv2.cvtColor(relief, cv2.COLOR_GRAY2BGR)
            return cv2.addWeighted(oil, 0.85, relief_3ch, 0.15, 0)
    except Exception:
        pass
    
    blur1 = cv2.bilateralFilter(img, 9, 80, 80)
    blur2 = cv2.medianBlur(blur1, 7)
    edge = cv2.Canny(blur2, 50, 150)
    contours, _ = cv2.findContours(edge, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    res = cv2.pyrMeanShiftFiltering(blur2, 10, 30)
    cv2.drawContours(res, contours, -1, (20, 20, 20), 1)
    return res


# 3. ENHANCED WATERCOLOR (Pigment Dispersion & Dark Edge Contours)
def water_coloring(img: np.ndarray, sigma_s: int = 60, sigma_r: float = 0.4) -> np.ndarray:
    s_val = max(10, int(sigma_s))
    r_val = max(10, int(float(sigma_r) * 100))
    
    wash = cv2.bilateralFilter(img, 15, r_val, s_val)
    wash = cv2.bilateralFilter(wash, 15, r_val, s_val)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_g = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Laplacian(blur_g, cv2.CV_8U, ksize=3)
    _, wet_edges = cv2.threshold(edges, 20, 255, cv2.THRESH_BINARY_INV)
    wet_edges_3ch = cv2.cvtColor(wet_edges, cv2.COLOR_GRAY2BGR)
    
    watercolor = cv2.multiply(wash.astype(np.float32) / 255.0, wet_edges_3ch.astype(np.float32) / 255.0) * 255.0
    watercolor = np.clip(watercolor, 0, 255).astype(np.uint8)
    return _apply_paper_texture(watercolor, strength=0.12)


# 4. ENHANCED CARTOON (LAB Color Quantization + Bold Vector Ink Outlines)
def cartoon_effect(img: np.ndarray, blur_k: int = 5, num_colors: int = 8) -> np.ndarray:
    blur_k_odd = max(3, int(blur_k) | 1)
    num_colors = max(2, min(int(num_colors), 24))
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.medianBlur(gray, blur_k_odd)
    edges = cv2.adaptiveThreshold(gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 5)
    
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.erode(edges, kernel, iterations=1)
    
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    pixels = lab.reshape((-1, 3)).astype(np.float32)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    quant_lab = centers[labels.flatten()].reshape(lab.shape).astype(np.uint8)
    quant_bgr = cv2.cvtColor(quant_lab, cv2.COLOR_LAB2BGR)
    
    smooth_d = max(5, blur_k_odd * 2)
    smooth_sigma = max(20, blur_k * 15)
    quant_bgr = cv2.bilateralFilter(quant_bgr, smooth_d, smooth_sigma, smooth_sigma)
    
    edges_3ch = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cartoon = cv2.bitwise_and(quant_bgr, edges_3ch)
    return cartoon


# 5. ENHANCED COMIC BOOK ART (Pop Comic Halftone Dots & High Contrast Ink)
def comic_cartoon_effect(img: np.ndarray) -> np.ndarray:
    shifted = cv2.pyrMeanShiftFiltering(img, 7, 30)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_g = cv2.medianBlur(gray, 5)
    edges = cv2.Canny(blur_g, 50, 150)
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges_inv = cv2.bitwise_not(edges)
    edges_3ch = cv2.cvtColor(edges_inv, cv2.COLOR_GRAY2BGR)
    
    hsv = cv2.cvtColor(shifted, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.4, 0, 255)
    boosted_color = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    return cv2.bitwise_and(boosted_color, edges_3ch)


# 6. ENHANCED ANIME / RETRO SYNTHWAVE VINTAGE
def anime_effect(img: np.ndarray, style: str = "vintage") -> np.ndarray:
    smooth = cv2.bilateralFilter(img, 9, 60, 60)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    edges_inv = cv2.cvtColor(cv2.bitwise_not(edges), cv2.COLOR_GRAY2BGR)
    
    if style == "vintage":
        hsv = cv2.cvtColor(smooth, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 0] = (hsv[:, :, 0] + 5) % 180
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
        retro = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        bloom = cv2.GaussianBlur(retro, (15, 15), 0)
        blended = cv2.addWeighted(retro, 0.75, bloom, 0.25, 0)
        final_img = cv2.bitwise_and(blended, edges_inv)
        return _apply_vignette(final_img, strength=0.5)

    elif style == "cyberpunk":
        f_img = smooth.astype(np.float32) / 255.0
        r, g, b = f_img[:, :, 2], f_img[:, :, 1], f_img[:, :, 0]
        
        neon_r = np.clip(r * 1.3 + 0.1, 0, 1)
        neon_g = np.clip(g * 0.9, 0, 1)
        neon_b = np.clip(b * 1.4 + 0.15, 0, 1)
        
        neon = cv2.merge([neon_b, neon_g, neon_r]) * 255.0
        neon_img = cv2.bitwise_and(neon.astype(np.uint8), edges_inv)
        return neon_img
        
    elif style == "blue":
        return cv2.cvtColor(smooth, cv2.COLOR_BGR2XYZ)
    elif style == "predator":
        return cv2.cvtColor(smooth, cv2.COLOR_BGR2HLS)
        
    return cv2.bitwise_and(smooth, edges_inv)


# 7. ENHANCED GLITCH ART (RGB Chromatic Aberration + Stripe Pixel Sorting)
def glitch_art(img: np.ndarray, step_size: int = 8) -> np.ndarray:
    h, w, c = img.shape
    step_size = max(4, int(step_size))
    
    shift_x = random.randint(6, 16)
    b, g, r = cv2.split(img)
    r_shifted = np.roll(r, shift_x, axis=1)
    b_shifted = np.roll(b, -shift_x, axis=1)
    
    chromatic = cv2.merge([b_shifted, g, r_shifted])
    
    num_stripes = max(1, h // step_size)
    stripes = np.array_split(chromatic, num_stripes, axis=0)
    
    sorted_stripes = []
    for idx, stripe in enumerate(stripes):
        if idx % 3 == 0:
            sorted_stripes.append(np.sort(stripe, axis=1))
        else:
            sorted_stripes.append(stripe)
            
    glitch_res = np.vstack(sorted_stripes)[:h, :w, :]
    
    scanlines = np.ones((h, w, 3), dtype=np.float32)
    scanlines[::4, :, :] = 0.7
    glitched_final = (glitch_res.astype(np.float32) * scanlines)
    return np.clip(glitched_final, 0, 255).astype(np.uint8)


# 8. ENHANCED LOW POLY ART (Delaunay Gem Triangulation)
def low_poly(img: np.ndarray, num_points: int = 600) -> np.ndarray:
    h, w, c = img.shape
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    corners = cv2.goodFeaturesToTrack(gray, maxCorners=int(num_points), qualityLevel=0.02, minDistance=8)
    
    points = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (0, h // 2), (w - 1, h // 2), (w // 2, h - 1)]
    if corners is not None:
        for pt in corners:
            px, py = pt.ravel()
            points.append((int(px), int(py)))
            
    rect = (0, 0, w, h)
    subdiv = cv2.Subdiv2D(rect)
    for p in points:
        subdiv.insert((p[0], p[1]))
        
    triangle_list = subdiv.getTriangleList()
    canvas = np.zeros((h, w, c), dtype=np.uint8)
    
    for t in triangle_list:
        pt1 = (int(t[0]), int(t[1]))
        pt2 = (int(t[2]), int(t[3]))
        pt3 = (int(t[4]), int(t[5]))
        
        pts = np.array([pt1, pt2, pt3], dtype=np.int32)
        cx = int((pt1[0] + pt2[0] + pt3[0]) / 3)
        cy = int((pt1[1] + pt2[1] + pt3[1]) / 3)
        
        if 0 <= cx < w and 0 <= cy < h:
            color = img[cy, cx].tolist()
            cv2.fillConvexPoly(canvas, pts, color)
            cv2.polylines(canvas, [pts], isClosed=True, color=[max(0, col - 20) for col in color], thickness=1)
            
    return canvas


# 9. ENHANCED POINTILLISM (Seurat Neo-Impressionist Brush Dots)
def pointillism(img: np.ndarray, stroke_scale: int = 3) -> np.ndarray:
    h, w, c = img.shape
    canvas = np.full((h, w, c), 245, dtype=np.uint8)
    factor = max(1, int(stroke_scale))
    step = max(3, factor * 2)
    
    for y in range(0, h, step):
        for x in range(0, w, step):
            base_color = img[y, x].astype(np.int32)
            jitter_color = np.clip(base_color + np.random.randint(-25, 25, size=3), 0, 255).tolist()
            
            radius = random.randint(factor + 1, factor * 2 + 2)
            offset_x = x + random.randint(-factor, factor)
            offset_y = y + random.randint(-factor, factor)
            
            cv2.circle(canvas, (offset_x, offset_y), radius, jitter_color, -1, lineType=cv2.LINE_AA)
            
    return _apply_paper_texture(canvas, strength=0.1)


# 10. ENHANCED NEON CYBERPUNK EDGE DETECTOR
def sobel_filter(img: np.ndarray, ksize: int = 3) -> np.ndarray:
    ksize = max(3, int(ksize) | 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
    magnitude = np.sqrt(sobelx**2 + sobely**2)
    magnitude = np.uint8(np.clip(magnitude, 0, 255))
    
    mag_f = magnitude.astype(np.float32) / 255.0
    neon_b = (np.sin(mag_f * np.pi) * 255).astype(np.uint8)
    neon_g = (mag_f * 180).astype(np.uint8)
    neon_r = (np.cos(mag_f * np.pi * 0.5) * 255).astype(np.uint8)
    
    neon_bgr = cv2.merge([neon_b, neon_g, neon_r])
    glow = cv2.GaussianBlur(neon_bgr, (9, 9), 0)
    return cv2.addWeighted(neon_bgr, 0.7, glow, 0.3, 0)


# 11. CANNY GLOW EDGE DETECTOR
def canny_edge(img: np.ndarray, threshold1: int = 100, threshold2: int = 200) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, int(threshold1), int(threshold2))
    
    edges_3ch = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cyan_mask = np.zeros_like(img)
    cyan_mask[:, :, 0] = 254
    cyan_mask[:, :, 1] = 242
    cyan_mask[:, :, 2] = 0
    
    neon_edges = cv2.bitwise_and(cyan_mask, edges_3ch)
    glow = cv2.GaussianBlur(neon_edges, (7, 7), 0)
    return cv2.addWeighted(neon_edges, 0.8, glow, 0.4, 0)


# 12. SEPIA VINTAGE FILM
def sepia_effect(img: np.ndarray) -> np.ndarray:
    kernel = np.array([
        [0.272, 0.534, 0.131],
        [0.349, 0.686, 0.168],
        [0.393, 0.769, 0.189]
    ])
    sepia = cv2.transform(img, kernel)
    sepia = np.clip(sepia, 0, 255).astype(np.uint8)
    vignette = _apply_vignette(sepia, strength=0.5)
    return _apply_paper_texture(vignette, strength=0.08)


# 13. EMBOSS 3D BAS-RELIEF
def emboss_effect(img: np.ndarray, mode: str = "color") -> np.ndarray:
    kernel = np.array([
        [-2, -1, 0],
        [-1,  1, 1],
        [ 0,  1, 2]
    ])
    if mode == "grayscale":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        emb = cv2.filter2D(gray, -1, kernel) + 128
        return cv2.cvtColor(np.clip(emb, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    
    emb = cv2.filter2D(img, -1, kernel) + 128
    return np.clip(emb, 0, 255).astype(np.uint8)


# 14. NEGATIVE FILM ROLL
def negative_effect(img: np.ndarray) -> np.ndarray:
    return cv2.bitwise_not(img)


# 15. DIRECTIONAL MOTION BLUR
def motion_blur(img: np.ndarray, direction: str = "horizontal", kernel_size: int = 15) -> np.ndarray:
    kernel_size = max(3, int(kernel_size))
    kernel = np.zeros((kernel_size, kernel_size))
    if direction == "horizontal":
        kernel[int((kernel_size - 1) / 2), :] = 1.0
    elif direction == "vertical":
        kernel[:, int((kernel_size - 1) / 2)] = 1.0
    else: # diagonal
        np.fill_diagonal(kernel, 1.0)
    
    kernel /= kernel_size
    return cv2.filter2D(img, -1, kernel)


# 16. COLOR DIVISION (LAB K-MEANS QUANTIZATION)
def color_division(img: np.ndarray, k: int = 4) -> np.ndarray:
    k = max(2, min(int(k), 16))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    data = lab.reshape((-1, 3)).astype(np.float32)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, label, center = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    center = np.uint8(center)
    res_lab = center[label.flatten()].reshape(lab.shape)
    res_bgr = cv2.cvtColor(res_lab, cv2.COLOR_LAB2BGR)
    return cv2.bilateralFilter(res_bgr, 7, 40, 40)


# 17. STIPPLING HALFTONE DOT ART
def stipple_effect(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    canvas = np.full((h, w), 255, dtype=np.uint8)
    
    step = 4
    for y in range(0, h, step):
        for x in range(0, w, step):
            val = gray[y, x]
            if random.randint(0, 255) > val:
                cv2.circle(canvas, (x, y), 1, 0, -1)
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


# 18. ASCII ART GENERATOR
def ascii_art(img: np.ndarray, cols: int = 90) -> np.ndarray:
    gscale = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert('L')
    W, H = pil_img.size
    cols = max(30, min(int(cols), 180))
    w_tile = W / cols
    h_tile = w_tile / 0.5
    rows = int(H / h_tile)
    
    if rows <= 0 or cols <= 0:
        return img
    
    lines = []
    for j in range(rows):
        y1 = int(j * h_tile)
        y2 = int((j + 1) * h_tile) if j < rows - 1 else H
        row_str = ""
        for i in range(cols):
            x1 = int(i * w_tile)
            x2 = int((i + 1) * w_tile) if i < cols - 1 else W
            crop = pil_img.crop((x1, y1, x2, y2))
            avg = int(np.average(np.array(crop)))
            row_str += gscale[int((avg * (len(gscale) - 1)) / 255)]
        lines.append(row_str)
    
    char_w = 8
    char_h = 14
    canvas_w = cols * char_w
    canvas_h = len(lines) * char_h
    ascii_canvas = Image.new('RGB', (canvas_w, canvas_h), (11, 15, 23))
    draw = ImageDraw.Draw(ascii_canvas)
    
    for idx, line in enumerate(lines):
        draw.text((0, idx * char_h), line, fill=(0, 242, 254))
        
    res_bgr = cv2.cvtColor(np.array(ascii_canvas), cv2.COLOR_RGB2BGR)
    return cv2.resize(res_bgr, (W, H))


# 19. CHARCOAL DARK SKETCH
def charcoal_sketch(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inv = 255 - gray
    blur = cv2.GaussianBlur(inv, (33, 33), 0)
    dodge = cv2.divide(gray, 255 - blur, scale=256)
    
    charcoal = cv2.addWeighted(dodge, 0.7, cv2.GaussianBlur(dodge, (5, 5), 0), 0.3, 0)
    charcoal = np.clip(charcoal.astype(np.float32) * 0.85, 0, 255).astype(np.uint8)
    return cv2.cvtColor(charcoal, cv2.COLOR_GRAY2BGR)


# 20. POP ART WARHOL QUAD
def pop_art_warhol(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    half_h, half_w = h // 2, w // 2
    small = cv2.resize(img, (half_w, half_h))
    
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    mask_inv = cv2.bitwise_not(mask)

    def colorize(bg_color, fg_color):
        bg = np.full_like(small, bg_color, dtype=np.uint8)
        fg = np.full_like(small, fg_color, dtype=np.uint8)
        bg_part = cv2.bitwise_and(bg, bg, mask=mask_inv)
        fg_part = cv2.bitwise_and(fg, fg, mask=mask)
        return cv2.add(bg_part, fg_part)

    q1 = colorize([0, 242, 254], [255, 8, 200])
    q2 = colorize([254, 242, 0], [0, 0, 255])
    q3 = colorize([255, 0, 255], [0, 255, 0])
    q4 = colorize([255, 128, 0], [0, 165, 255])

    top_row = np.hstack([q1, q2])
    bot_row = np.hstack([q3, q4])
    quad = np.vstack([top_row, bot_row])
    return cv2.resize(quad, (w, h))


# 21. LICHTENSTEIN POP COMIC HALFTONE
def halftone_dots(img: np.ndarray, dot_size: int = 6) -> np.ndarray:
    h, w, c = img.shape
    canvas = np.full((h, w, c), 255, dtype=np.uint8)
    step = max(3, int(dot_size))

    for y in range(step // 2, h, step):
        for x in range(step // 2, w, step):
            bgr = img[y, x].tolist()
            gray_val = int(0.299 * bgr[2] + 0.587 * bgr[1] + 0.114 * bgr[0])
            radius = int((1.0 - (gray_val / 255.0)) * (step / 2.0))
            if radius > 0:
                cv2.circle(canvas, (x, y), radius, bgr, -1, lineType=cv2.LINE_AA)
                
    return canvas


# 22. PIXEL ART 8-BIT
def pixel_art(img: np.ndarray, pixel_size: int = 10) -> np.ndarray:
    h, w, c = img.shape
    pixel_size = max(2, min(int(pixel_size), 50))
    
    small_w = max(4, w // pixel_size)
    small_h = max(4, h // pixel_size)
    
    small = cv2.resize(img, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    
    pixels = small.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(pixels, 12, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    quant_small = centers[labels.flatten()].reshape(small.shape).astype(np.uint8)
    return cv2.resize(quant_small, (w, h), interpolation=cv2.INTER_NEAREST)


# --- INSTAGRAM & SNAPCHAT ICONIC FILTERS ---

# 23. INSTAGRAM CLARENDON (High Contrast, Cool Blues, Warm Skin Tone Boost)
def instagram_clarendon(img: np.ndarray) -> np.ndarray:
    res = img.astype(np.float32)
    # High contrast gain
    res = (res - 128.0) * 1.25 + 128.0
    res = np.clip(res, 0, 255)
    
    # Boost blue channel in shadows & red channel in highlights
    res[:, :, 0] = np.clip(res[:, :, 0] * 1.15 + 10, 0, 255) # Blue
    res[:, :, 2] = np.clip(res[:, :, 2] * 1.10 + 5, 0, 255)  # Red
    
    vignette = _apply_vignette(res.astype(np.uint8), strength=0.45)
    return vignette


# 24. INSTAGRAM VALENCIA (Warm Golden Sunset Glow & Faded Blacks)
def instagram_valencia(img: np.ndarray) -> np.ndarray:
    res = img.astype(np.float32)
    # Warm shift (Increase Red & Green, decrease Blue)
    res[:, :, 0] = res[:, :, 0] * 0.85 + 20 # Blue
    res[:, :, 1] = res[:, :, 1] * 1.05 + 10 # Green
    res[:, :, 2] = res[:, :, 2] * 1.15 + 15 # Red
    
    # Lift blacks (faded film look)
    res = res * 0.85 + 30.0
    res = np.clip(res, 0, 255).astype(np.uint8)
    return _apply_vignette(res, strength=0.35)


# 25. INSTAGRAM NASHVILLE (Soft Pastel Pink/Magenta Retro Tint)
def instagram_nashville(img: np.ndarray) -> np.ndarray:
    res = img.astype(np.float32)
    # Pinkish magenta tint
    res[:, :, 0] = res[:, :, 0] * 1.1 + 25 # Blue/Magenta
    res[:, :, 1] = res[:, :, 1] * 0.9 + 10 # Green
    res[:, :, 2] = res[:, :, 2] * 1.2 + 20 # Red
    
    # Soft low contrast
    res = (res - 128.0) * 0.9 + 128.0
    return np.clip(res, 0, 255).astype(np.uint8)


# 26. INSTAGRAM LO-FI (Rich Saturated Shadows & High Contrast)
def instagram_lofi(img: np.ndarray) -> np.ndarray:
    res = img.astype(np.float32)
    # Boost contrast significantly
    res = (res - 128.0) * 1.35 + 128.0
    res = np.clip(res, 0, 255)
    
    # Saturate colors
    hsv = cv2.cvtColor(res.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.4, 0, 255)
    lofi = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return _apply_vignette(lofi, strength=0.6)


# 27. INSTAGRAM JUNO (Warm Reds/Yellows & Cool Blue Shadows)
def instagram_juno(img: np.ndarray) -> np.ndarray:
    res = img.astype(np.float32)
    res[:, :, 1] = np.clip(res[:, :, 1] * 1.15, 0, 255) # Green
    res[:, :, 2] = np.clip(res[:, :, 2] * 1.25, 0, 255) # Red
    res = np.clip(res, 0, 255).astype(np.uint8)
    
    smooth = cv2.bilateralFilter(res, 7, 50, 50)
    return _apply_vignette(smooth, strength=0.3)


# 28. SNAPCHAT BEAUTY GLOW LENS (Skin Smoothing, Soft Light Aura & Warm Cheek Rosy Glow)
def snapchat_beauty_glow(img: np.ndarray) -> np.ndarray:
    # 1. Bilateral skin smoothing
    smooth = cv2.bilateralFilter(img, 11, 75, 75)
    
    # 2. Soft aura glow overlay
    blur = cv2.GaussianBlur(smooth, (21, 21), 0)
    glow = cv2.addWeighted(smooth, 0.7, blur, 0.3, 0)
    
    # 3. Soft warm color grading & slight brightness boost
    res = glow.astype(np.float32)
    res[:, :, 0] = np.clip(res[:, :, 0] * 0.95, 0, 255)       # Blue
    res[:, :, 1] = np.clip(res[:, :, 1] * 1.05 + 5, 0, 255)   # Green
    res[:, :, 2] = np.clip(res[:, :, 2] * 1.12 + 10, 0, 255)  # Red (warm rosy cheek tone)
    
    return np.clip(res, 0, 255).astype(np.uint8)


# 29. SNAPCHAT NEON LENS (Dual-Tone Electric Violet & Cyan Lens)
def snapchat_neon_lens(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    h, w = gray.shape
    
    # Dual tone gradient overlay (Cyan left -> Violet right)
    grid_x = np.tile(np.linspace(0, 1, w), (h, 1))
    
    cyan_bg = np.zeros((h, w, 3), dtype=np.float32)
    cyan_bg[:, :, 0] = 1.0 # Blue
    cyan_bg[:, :, 1] = 0.9 # Green
    
    violet_bg = np.zeros((h, w, 3), dtype=np.float32)
    violet_bg[:, :, 0] = 0.9 # Blue
    violet_bg[:, :, 2] = 1.0 # Red
    
    grad = cyan_bg * (1.0 - grid_x[:, :, None]) + violet_bg * grid_x[:, :, None]
    
    img_f = img.astype(np.float32) / 255.0
    neon_lens = (img_f * grad) * 255.0 * 1.3
    return np.clip(neon_lens, 0, 255).astype(np.uint8)


# 30. SNAPCHAT DRAMATIC NOIR (High Contrast B&W Lens with Deep Vignette)
def snapchat_dramatic_noir(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # High contrast S-curve
    noir = (gray - 128.0) * 1.5 + 128.0
    noir = np.clip(noir, 0, 255).astype(np.uint8)
    noir_3ch = cv2.cvtColor(noir, cv2.COLOR_GRAY2BGR)
    return _apply_vignette(noir_3ch, strength=0.75)
