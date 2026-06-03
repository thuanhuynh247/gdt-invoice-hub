#!/usr/bin/env python3
"""
Export HTML Carousel → PNG slides + PDF
Yêu cầu: pip install playwright Pillow
          playwright install chromium   (hoặc dùng --channel chrome nếu đã cài Google Chrome)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Thiếu playwright. Chạy: pip install playwright")
    sys.exit(1)

try:
    from PIL import Image
    # Explicitly import plugins to guarantee registration of encoders/decoders
    from PIL import JpegImagePlugin, PdfImagePlugin, PngImagePlugin
except ImportError:
    print("❌ Thiếu Pillow. Chạy: pip install Pillow")
    sys.exit(1)


def parse_ratio(ratio_str: str) -> tuple:
    """Parse ratio string like '4:5' into (4, 5)."""
    parts = ratio_str.split(":")
    return int(parts[0]), int(parts[1])


async def export_carousel(
    html_path: str,
    output_dir: str,
    width: int = 1080,
    ratio: str = "1:1",
    scale: int = 2,
    wait_ms: int = 2000,
    channel: str = "chrome",
):
    html_path = os.path.abspath(html_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    ratio_w, ratio_h = parse_ratio(ratio)
    height = int(width * ratio_h / ratio_w)

    print(f"📐 Viewport: {width}x{height} (ratio {ratio})")
    print(f"🔍 Scale factor: {scale}x → Ảnh thực tế: {width * scale}x{height * scale}px")
    print(f"📂 Output: {output_dir}")
    print(f"🌐 Browser: {channel}")
    print()

    file_url = Path(html_path).as_uri()

    async with async_playwright() as p:
        # Thử dùng channel (Google Chrome đã cài trên máy) trước
        # Nếu không có, fallback sang chromium bundled
        try:
            browser = await p.chromium.launch(headless=True, channel=channel)
        except Exception:
            print(f"⚠️  Không tìm thấy '{channel}', thử chromium bundled...")
            browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
        )
        page = await context.new_page()

        print(f"📄 Đang mở: {os.path.basename(html_path)}")
        await page.goto(file_url, wait_until="networkidle")
        # Chờ font load hoàn toàn để chữ hiển thị đẹp, không bị lỗi
        await page.evaluate("document.fonts.ready")
        # Chờ thêm cho Tailwind CDN xử lý hoặc các animation (nếu có)
        await page.wait_for_timeout(wait_ms)

        # Tìm container và đếm slide
        container = await page.query_selector(".slides-container")
        if not container:
            container = await page.query_selector("[class*='slides']")
        if not container:
            container = await page.query_selector(".slide-stack")
        if not container:
            print("❌ Không tìm thấy .slides-container hoặc .slide-stack trong HTML.")
            await browser.close()
            sys.exit(1)

        slides = await container.query_selector_all(".slide")
        total = len(slides)
        if total == 0:
            slides = await container.query_selector_all(".carousel-slide")
            total = len(slides)
        if total == 0:
            slides = await container.query_selector_all(":scope > *")
            total = len(slides)

        print(f"📊 Tìm thấy {total} slides")
        print()

        # Tìm carousel wrapper để chụp
        wrapper = await page.query_selector(".carousel-wrapper")
        if not wrapper:
            wrapper = container

        png_paths = []

        for i in range(total):
            # Cuộn đến slide thứ i (nếu là dạng ngang)
            await page.evaluate(
                """(index) => {
                    const container = document.querySelector('.slides-container');
                    if (container) {
                        const slideWidth = container.clientWidth;
                        container.scrollTo({ left: index * slideWidth, behavior: 'instant' });
                    }
                }""",
                i,
            )
            # Hoặc scroll tới view của slide nếu dạng dọc
            await slides[i].scroll_into_view_if_needed()
            await page.wait_for_timeout(400)

            png_name = f"slide-{i + 1:02d}.png"
            png_path = os.path.join(output_dir, png_name)

            if wrapper == container and total > 1:
                # Dạng danh sách cuộn dọc
                box = await slides[i].bounding_box()
                if box:
                    exact_height = box["width"] * ratio_h / ratio_w
                    clip = {"x": box["x"], "y": box["y"], "width": box["width"], "height": exact_height}
                    await page.screenshot(path=png_path, clip=clip)
                else:
                    await slides[i].screenshot(path=png_path)
            else:
                # Dạng wrapper cuộn ngang
                box = await wrapper.bounding_box()
                if box:
                    exact_height = box["width"] * ratio_h / ratio_w
                    clip = {"x": box["x"], "y": box["y"], "width": box["width"], "height": exact_height}
                    await page.screenshot(path=png_path, clip=clip)
                else:
                    await wrapper.screenshot(path=png_path)
            png_paths.append(png_path)

            file_size_kb = os.path.getsize(png_path) / 1024
            print(f"  ✅ {png_name} ({file_size_kb:.0f} KB)")

        await browser.close()

    # Gộp thành PDF
    print()
    print("📄 Đang tạo PDF...")

    pdf_name = Path(html_path).stem + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)

    images = []
    first_img = None

    # Initialize Image module explicitly to force encoder registration
    Image.init()

    for png_path in png_paths:
        img = Image.open(png_path).convert("RGB")
        if first_img is None:
            first_img = img
        else:
            images.append(img)

    if first_img:
        first_img.save(
            pdf_path,
            save_all=True,
            append_images=images,
            resolution=150,
        )

        pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        print(f"  ✅ {pdf_name} ({pdf_size_mb:.1f} MB)")

    print()
    print("=" * 50)
    print(f"🎉 Hoàn tất! Đã xuất {total} slides.")
    print(f"   📁 Ảnh PNG: {output_dir}")
    print(f"   📄 PDF:     {pdf_path}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Export HTML Carousel → PNG slides + PDF"
    )
    parser.add_argument("--input", "-i", required=True, help="Đường dẫn file HTML carousel")
    parser.add_argument("--output", "-o", default=None, help="Thư mục output (mặc định: <input-dir>/export/)")
    parser.add_argument("--width", "-w", type=int, default=1080, help="Chiều rộng viewport (default: 1080)")
    parser.add_argument("--ratio", "-r", default="1:1", help="Tỉ lệ slide (default: 1:1)")
    parser.add_argument("--scale", "-s", type=int, default=2, help="Device scale factor (default: 2 = retina)")
    parser.add_argument("--wait", type=int, default=2000, help="Thời gian chờ load (ms, default: 2000)")
    parser.add_argument("--channel", default="chrome", help="Browser channel (default: chrome = Google Chrome trên máy)")

    args = parser.parse_args()

    if args.output is None:
        input_dir = os.path.dirname(os.path.abspath(args.input))
        args.output = os.path.join(input_dir, "export")

    asyncio.run(
        export_carousel(
            html_path=args.input,
            output_dir=args.output,
            width=args.width,
            ratio=args.ratio,
            scale=args.scale,
            wait_ms=args.wait,
            channel=args.channel,
        )
    )


if __name__ == "__main__":
    main()
