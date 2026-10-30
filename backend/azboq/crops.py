"""Turn a PDF point or a drawing coordinate into a pixel on the image the viewer shows.

PDF text is in points, origin at the top left, and the page image is 110 dpi.
A drawing's y axis points up. A region tile may be letterboxed, so the scale and
the offset are the ones the renderer used, not a second guess in the browser.
"""
PDF_DPI = 110


def pdf_to_px(bbox: list[float], dpi: int = PDF_DPI) -> list[float]:
    """[x0, y0, x1, y1] in points → the same box on the page image."""
    return [v * dpi / 72 for v in bbox]


def pdf_transform(dpi: int = PDF_DPI) -> dict:
    return {"kind": "pdf", "dpi": dpi, "scale": dpi / 72}


def region_transform(bbox: list[float], png_w: int, png_h: int) -> dict:
    """World bbox fitted into the tile. Y is flipped. A leftover margin is the offset."""
    x0, y0, x1, y1 = bbox
    width, height = x1 - x0, y1 - y0
    if width == 0 or height == 0:
        raise ValueError("a region box has no area")
    scale = min(png_w / width, png_h / height)
    offset_x = (png_w - width * scale) / 2
    offset_y = (png_h - height * scale) / 2
    return {
        "kind": "dxf",
        "scale": scale,
        "offset": [offset_x, offset_y],
        "width": png_w,
        "height": png_h,
        "bbox": [x0, y0, x1, y1],
    }


def dxf_to_px(point: list[float], bbox: list[float], png_w: int, png_h: int) -> list[float]:
    transform = region_transform(bbox, png_w, png_h)
    x, y = point
    x0, _y0, _x1, y1 = bbox
    ox, oy = transform["offset"]
    scale = transform["scale"]
    return [ox + (x - x0) * scale, oy + (y1 - y) * scale]
