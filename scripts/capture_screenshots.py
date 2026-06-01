import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def capture_live_screenshots():
    print("🚀 Starting automated high-resolution system capture...")
    
    # Target directory
    output_dir = r"d:\LearnAnyThing\Webapp XML\campaign"
    os.makedirs(output_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch browser
        try:
            browser = await p.chromium.launch(headless=True, channel="chrome")
        except Exception:
            browser = await p.chromium.launch(headless=True)
            
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page = await context.new_page()
        
        # 1. Login
        print("🔑 Logging in to GDT Invoice Hub...")
        await page.goto("http://127.0.0.1:5000/login", wait_until="networkidle")
        await page.fill("input[name='username']", "admin")
        await page.fill("input[name='password']", "admin123")
        
        # If captcha is visible, fill it, otherwise skip
        captcha_input = await page.query_selector("input[name='captcha']")
        if captcha_input and await captcha_input.is_visible():
            try:
                await page.fill("input[name='captcha']", "AUTO", timeout=2000)
                print("   Filled captcha field with 'AUTO'")
            except Exception:
                print("   Could not fill captcha, skipping...")
        else:
            print("   Captcha field is hidden (auto-solved by server). Skipping input...")
            
        await page.click("button[type='submit']")
        await page.wait_for_timeout(3000)
        
        # 2. Main Dashboard (Invoices Tab)
        print("📸 Capturing Invoice Dashboard...")
        # Trigger search to load data
        search_btn = await page.query_selector("button:has-text('Tìm Kiếm')")
        if search_btn:
            await search_btn.click()
            await page.wait_for_timeout(2000)
        
        dashboard_path = os.path.join(output_dir, "dashboard-screenshot.png")
        await page.screenshot(path=dashboard_path)
        print(f"   Saved dashboard to {dashboard_path}")
        
        # 3. T-Score Detail Card
        print("📸 Capturing Compliance T-Score & AI Auditor...")
        detail_btn = await page.query_selector("button:has-text('Chi Tiết')")
        if detail_btn:
            await detail_btn.click()
            await page.wait_for_timeout(2000)
            
            detail_path = os.path.join(output_dir, "detail-screenshot.png")
            await page.screenshot(path=detail_path)
            print(f"   Saved detail panel to {detail_path}")
            
            # Close the detail modal/drawer to clean up the page
            close_btn = await page.query_selector("button:has-text('Đóng'), button:has-text('Close'), .btn-close")
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(500)
        else:
            print("   ⚠️ No invoice detail button found, skipping detail snapshot")
            
        # 4. VAT Declaration Tab
        print("📸 Capturing VAT Declaration Tab...")
        vat_tab = await page.query_selector("#tax-return-tab")
        if vat_tab:
            await vat_tab.click()
            await page.wait_for_timeout(1000)
            
            # Click query button to load the VAT report
            load_vat_btn = await page.query_selector("#btnLoadVatData")
            if load_vat_btn:
                await load_vat_btn.click()
                await page.wait_for_timeout(2000)
                
            # Screenshot the VAT return page
            vat_path = os.path.join(output_dir, "vat-screenshot.png")
            await page.screenshot(path=vat_path)
            print(f"   Saved VAT return to {vat_path}")
        else:
            print("   ⚠️ VAT tab not found!")

        # 5. ARIMA Forecasting Tab
        print("📸 Capturing ARIMA Forecasting Tab...")
        analytics_tab = await page.query_selector("#analytics-pro-tab")
        if analytics_tab:
            await analytics_tab.click()
            await page.wait_for_timeout(1000)
            
            # Click sub-tab for VAT Forecast
            forecast_sub_tab = await page.query_selector("#vat-forecast-sub-tab")
            if forecast_sub_tab:
                await forecast_sub_tab.click()
                await page.wait_for_timeout(4000) # Wait for ARIMA chart to load and animate
                
            forecasting_path = os.path.join(output_dir, "forecasting-screenshot.png")
            await page.screenshot(path=forecasting_path)
            print(f"   Saved forecasting to {forecasting_path}")
        else:
            print("   ⚠️ Analytics tab not found!")
        
        await browser.close()
        print("🎉 Live capture completed successfully!")

if __name__ == "__main__":
    asyncio.run(capture_live_screenshots())
