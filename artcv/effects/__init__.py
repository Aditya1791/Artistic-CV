"""
ArtCV Effects Registry & Parameter Spec Metadata Catalog
Exposes 30+ pro computer vision, artistic, Instagram, and Snapchat filters.
"""

from artcv.effects.core_effects import (
    pencil_sketch,
    oil_painting,
    water_coloring,
    cartoon_effect,
    comic_cartoon_effect,
    anime_effect,
    glitch_art,
    low_poly,
    pointillism,
    sobel_filter,
    canny_edge,
    sepia_effect,
    emboss_effect,
    negative_effect,
    motion_blur,
    color_division,
    stipple_effect,
    ascii_art,
    charcoal_sketch,
    pop_art_warhol,
    halftone_dots,
    pixel_art,
    instagram_clarendon,
    instagram_valencia,
    instagram_nashville,
    instagram_lofi,
    instagram_juno,
    snapchat_beauty_glow,
    snapchat_neon_lens,
    snapchat_dramatic_noir
)

EFFECT_MAP = {
    # --- INSTAGRAM & SNAPCHAT ICONIC FILTERS ---
    "snapchat_beauty_glow": {
        "fn": snapchat_beauty_glow,
        "name": "Snapchat Beauty Smooth Glow",
        "category": "Filters",
        "description": "Bilateral skin smoothing, soft light aura glow, and warm rosy blush tone boost.",
        "params": {}
    },
    "instagram_clarendon": {
        "fn": instagram_clarendon,
        "name": "Instagram Clarendon",
        "category": "Filters",
        "description": "High contrast, boosted cool blue shadows, and warm highlight skin tones.",
        "params": {}
    },
    "instagram_valencia": {
        "fn": instagram_valencia,
        "name": "Instagram Valencia",
        "category": "Filters",
        "description": "Soft golden sunset glow with warm tones and faded film blacks.",
        "params": {}
    },
    "snapchat_neon_lens": {
        "fn": snapchat_neon_lens,
        "name": "Snapchat Dual Neon Lens",
        "category": "Digital Art",
        "description": "Dual-tone electric cyan-to-violet gradient light lens overlay.",
        "params": {}
    },
    "instagram_lofi": {
        "fn": instagram_lofi,
        "name": "Instagram Lo-Fi",
        "category": "Filters",
        "description": "Rich saturated shadows, vivid color saturation, and punchy contrast.",
        "params": {}
    },
    "instagram_nashville": {
        "fn": instagram_nashville,
        "name": "Instagram Nashville",
        "category": "Filters",
        "description": "Soft pastel pinkish-magenta vintage tint with gentle low contrast.",
        "params": {}
    },
    "snapchat_dramatic_noir": {
        "fn": snapchat_dramatic_noir,
        "name": "Snapchat Dramatic Noir Lens",
        "category": "Filters",
        "description": "High-contrast monochrome portrait lens with deep dramatic radial vignette.",
        "params": {}
    },
    "instagram_juno": {
        "fn": instagram_juno,
        "name": "Instagram Juno",
        "category": "Filters",
        "description": "Vivid warm red and yellow color boost with cool blue shadow tones.",
        "params": {}
    },

    # --- ARTISTIC & SKETCH FILTERS ---
    "pencil_sketch": {
        "fn": pencil_sketch,
        "name": "DoG Graphite Pencil Sketch",
        "category": "Sketches",
        "description": "Difference of Gaussians contour extraction with cross-hatch shading.",
        "params": {
            "mode": {"type": "select", "options": ["gray", "color"], "default": "gray", "label": "Sketch Mode"},
            "sigma_s": {"type": "int", "min": 10, "max": 200, "default": 60, "label": "Smoothness (sigma_s)"},
            "sigma_r": {"type": "float", "min": 0.01, "max": 0.5, "default": 0.07, "label": "Edge Range (sigma_r)"},
            "shade_factor": {"type": "float", "min": 0.01, "max": 0.2, "default": 0.05, "label": "Shade Density"}
        }
    },
    "charcoal": {
        "fn": charcoal_sketch,
        "name": "Dark Charcoal Sketch",
        "category": "Sketches",
        "description": "Rich dark charcoal pencil texture with high-contrast edge strokes.",
        "params": {}
    },
    "oil_painting": {
        "fn": oil_painting,
        "name": "Impasto Oil Painting",
        "category": "Paintings",
        "description": "Anisotropic flow painting with raised brush stroke impasto texture.",
        "params": {
            "size": {"type": "int", "min": 1, "max": 10, "default": 4, "label": "Brush Radius"},
            "dyn_ratio": {"type": "int", "min": 1, "max": 10, "default": 2, "label": "Pigment Quantization"}
        }
    },
    "water_coloring": {
        "fn": water_coloring,
        "name": "Watercolor Wash",
        "category": "Paintings",
        "description": "Fluid pigment diffusion wash with paper grain texture overlay.",
        "params": {
            "sigma_s": {"type": "int", "min": 10, "max": 150, "default": 60, "label": "Pigment Wash Smoothness"},
            "sigma_r": {"type": "float", "min": 0.1, "max": 0.8, "default": 0.4, "label": "Color Diffusion"}
        }
    },
    "cartoon": {
        "fn": cartoon_effect,
        "name": "LAB Vector Cartoon",
        "category": "Cartoons",
        "description": "LAB color space K-Means quantization with bold adaptive ink outlines.",
        "params": {
            "blur_k": {"type": "int", "min": 3, "max": 15, "default": 5, "label": "Line Smoothness"},
            "num_colors": {"type": "int", "min": 2, "max": 24, "default": 8, "label": "Color Palette Size"}
        }
    },
    "comic_cartoon": {
        "fn": comic_cartoon_effect,
        "name": "Pop Comic Ink",
        "category": "Cartoons",
        "description": "Saturated HSV color channels with heavy comic book ink outlines.",
        "params": {}
    },
    "anime_effect": {
        "fn": anime_effect,
        "name": "Retro Synthwave Anime",
        "category": "Cartoons",
        "description": "Stylized retro anime filter with neon bloom and vintage color grading.",
        "params": {
            "style": {"type": "select", "options": ["vintage", "cyberpunk", "blue", "predator"], "default": "vintage", "label": "Anime Style"}
        }
    },
    "pop_art": {
        "fn": pop_art_warhol,
        "name": "Pop Art Warhol Quad",
        "category": "Digital Art",
        "description": "Classic 4-panel Pop Art grid inspired by Andy Warhol screen prints.",
        "params": {}
    },
    "halftone": {
        "fn": halftone_dots,
        "name": "Lichtenstein Halftone Dots",
        "category": "Digital Art",
        "description": "Simulates retro comic book printing halftone dot screens.",
        "params": {
            "dot_size": {"type": "int", "min": 3, "max": 20, "default": 6, "label": "Dot Grid Size"}
        }
    },
    "pixel_art": {
        "fn": pixel_art,
        "name": "Pixel Art 8-Bit",
        "category": "Digital Art",
        "description": "Downsamples resolution and quantizes color palette for 8-bit retro arcade gaming.",
        "params": {
            "pixel_size": {"type": "int", "min": 2, "max": 30, "default": 10, "label": "Pixel Scale"}
        }
    },
    "glitch": {
        "fn": glitch_art,
        "name": "RGB Chromatic Glitch Art",
        "category": "Digital Art",
        "description": "RGB chromatic aberration offset with horizontal stripe pixel sorting.",
        "params": {
            "step_size": {"type": "int", "min": 4, "max": 20, "default": 8, "label": "Stripe Slice Height"}
        }
    },
    "low_poly": {
        "fn": low_poly,
        "name": "Delaunay Gem Low Poly",
        "category": "Digital Art",
        "description": "Shi-Tomasi corner detection triangulated into Delaunay low-poly gem facets.",
        "params": {
            "num_points": {"type": "int", "min": 100, "max": 1500, "default": 600, "label": "Facet Count"}
        }
    },
    "pointillism": {
        "fn": pointillism,
        "name": "Pointillism Dot Painting",
        "category": "Paintings",
        "description": "Seurat Neo-Impressionist paint dabs with color jitter.",
        "params": {
            "stroke_scale": {"type": "int", "min": 1, "max": 10, "default": 3, "label": "Dot Radius"}
        }
    },
    "stipple": {
        "fn": stipple_effect,
        "name": "Ink Stippling Dots",
        "category": "Sketches",
        "description": "Hand-drawn ink stippling dot art pattern.",
        "params": {}
    },
    "sepia": {
        "fn": sepia_effect,
        "name": "Vintage Sepia Film",
        "category": "Filters",
        "description": "Classic warm sepia tone matrix with vintage paper grain and vignette.",
        "params": {}
    },
    "emboss": {
        "fn": emboss_effect,
        "name": "3D Bas-Relief Emboss",
        "category": "Digital Art",
        "description": "Directional convolution matrix producing 3D stamped paper bas-relief.",
        "params": {
            "mode": {"type": "select", "options": ["color", "grayscale"], "default": "color", "label": "Mode"}
        }
    },
    "negative": {
        "fn": negative_effect,
        "name": "Negative Roll",
        "category": "Filters",
        "description": "Inverts RGB channels to simulate photographic negative film.",
        "params": {}
    },
    "motion_blur": {
        "fn": motion_blur,
        "name": "Motion Blur",
        "category": "Filters",
        "description": "Simulates camera movement blur in horizontal, vertical, or diagonal directions.",
        "params": {
            "direction": {"type": "select", "options": ["horizontal", "vertical", "diagonal"], "default": "horizontal", "label": "Direction"},
            "kernel_size": {"type": "int", "min": 3, "max": 31, "default": 15, "label": "Blur Intensity"}
        }
    },
    "color_division": {
        "fn": color_division,
        "name": "Color Division (LAB K-Means)",
        "category": "Digital Art",
        "description": "LAB color space K-Means quantization with edge-preserving bilateral filtering.",
        "params": {
            "k": {"type": "int", "min": 2, "max": 16, "default": 4, "label": "Color Count (K)"}
        }
    },
    "sobel": {
        "fn": sobel_filter,
        "name": "Neon Cyberpunk Sobel",
        "category": "Edge Filters",
        "description": "Cyan-to-pink gradient colorized glowing Sobel contours.",
        "params": {
            "ksize": {"type": "int", "min": 3, "max": 7, "default": 3, "label": "Kernel Size"}
        }
    },
    "canny": {
        "fn": canny_edge,
        "name": "Neon Glow Canny Edge",
        "category": "Edge Filters",
        "description": "Glowing electric cyan boundary contour detector.",
        "params": {
            "threshold1": {"type": "int", "min": 10, "max": 200, "default": 100, "label": "Low Threshold"},
            "threshold2": {"type": "int", "min": 50, "max": 300, "default": 200, "label": "High Threshold"}
        }
    },
    "ascii_art": {
        "fn": ascii_art,
        "name": "Cyberpunk ASCII Art",
        "category": "Digital Art",
        "description": "Converts image pixels into styled electric-cyan ASCII characters.",
        "params": {
            "cols": {"type": "int", "min": 30, "max": 180, "default": 90, "label": "Columns"}
        }
    }
}
