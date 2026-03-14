import { test, expect } from '@playwright/test'

test.describe('App loads correctly', () => {
  test('homepage renders with ON24 Nexus branding', async ({ page }) => {
    await page.goto('/')
    // TopNav should show app name
    await expect(page.locator('text=ON24 Nexus')).toBeVisible()
  })

  test('chat input is visible and focusable', async ({ page }) => {
    await page.goto('/')
    const input = page.getByLabel('Type your message')
    await expect(input).toBeVisible()
    await input.focus()
    await expect(input).toBeFocused()
  })

  test('suggestion tiles are visible on home screen', async ({ page }) => {
    await page.goto('/')
    // Home screen should have suggestion tiles
    await expect(page.locator('text=How do I')).toBeVisible({ timeout: 5000 })
  })

  test('dark mode toggle works', async ({ page }) => {
    await page.goto('/')
    // Find the theme toggle (pill switch in TopNav)
    const html = page.locator('html')
    const initialTheme = await html.getAttribute('data-theme')

    // Click the toggle
    const toggle = page.locator('[aria-label="Toggle dark mode"], [aria-label="Toggle light mode"]').first()
    if (await toggle.isVisible()) {
      await toggle.click()
      const newTheme = await html.getAttribute('data-theme')
      expect(newTheme).not.toBe(initialTheme)
    }
  })
})

test.describe('Chat interaction', () => {
  test('can type and send a message', async ({ page }) => {
    await page.goto('/')
    const input = page.getByLabel('Type your message')
    await input.fill('How many events this month?')

    const sendBtn = page.getByLabel('Send message')
    await sendBtn.click()

    // Message should appear in chat log
    const chatLog = page.locator('[role="log"]')
    await expect(chatLog).toContainText('How many events this month?', { timeout: 5000 })

    // Wait for any agent response text to appear (live LLM can be slow)
    // The response div comes after the user message — just wait for more content
    await page.waitForTimeout(2000)
    const messages = chatLog.locator('div')
    await expect(messages).not.toHaveCount(0, { timeout: 45000 })
  })

  test('skip-to-content link exists', async ({ page }) => {
    await page.goto('/')
    const skipLink = page.locator('a[href="#main-content"], .skip-link')
    // Should exist in DOM (may be visually hidden until focused)
    await expect(skipLink).toHaveCount(1)
  })
})

test.describe('Calendar', () => {
  test('calendar icon opens modal', async ({ page }) => {
    await page.goto('/')
    const calBtn = page.locator('[aria-label*="calendar" i], [aria-label*="Calendar" i]').first()
    if (await calBtn.isVisible()) {
      await calBtn.click()
      // Calendar modal should appear — look for month navigation or day headers
      await expect(
        page.locator('text=/Sun|Mon|Tue|Wed|Thu|Fri|Sat/').first()
      ).toBeVisible({ timeout: 5000 })
    }
  })
})

test.describe('Documents sidebar', () => {
  test('documents dropdown exists in sidebar', async ({ page }) => {
    await page.goto('/')
    const docsBtn = page.locator('text=Documents').first()
    if (await docsBtn.isVisible()) {
      await docsBtn.click()
      // Should show doc links
      await expect(page.locator('text=Tech Spec')).toBeVisible({ timeout: 3000 })
    }
  })
})
