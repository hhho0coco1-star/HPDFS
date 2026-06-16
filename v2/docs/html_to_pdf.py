import asyncio
from playwright.async_api import async_playwright
from PIL import Image
import io
from pathlib import Path

HTML_PATH = Path(__file__).parent / "final_presentation.html"
OUTPUT_PDF = Path(__file__).parent / "HPDFS_presentation.pdf"
WIDTH, HEIGHT = 1280, 720


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})

        await page.goto(HTML_PATH.resolve().as_uri())
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(800)

        slides_count = await page.evaluate("slides.length")
        print(f"슬라이드 수: {slides_count}")

        images = []
        for i in range(slides_count):
            await page.evaluate(f"showSlide({i})")
            await page.wait_for_timeout(400)
            data = await page.screenshot(type="png", full_page=False)
            img = Image.open(io.BytesIO(data)).convert("RGB")
            images.append(img)
            print(f"  [{i+1}/{slides_count}] 캡처 완료")

        await browser.close()

    images[0].save(
        OUTPUT_PDF,
        save_all=True,
        append_images=images[1:],
        resolution=150,
    )
    print(f"\nPDF 저장 완료: {OUTPUT_PDF}")


asyncio.run(main())
