import { test, expect } from '@playwright/test'
import fs from 'fs'
import os from 'os'
import path from 'path'

/**
 * Demo end-to-end: register a patient, upload a text report, see flagged labs.
 * Needs the backend (port 8000) and frontend dev server running, plus a
 * Playwright browser (`npx playwright install chromium`).
 * Run: E2E_BASE_URL=http://localhost:3000 npx playwright test
 */
test('register patient, upload text report, see flagged labs', async ({ page }) => {
  const stamp = Date.now()
  const email = `e2e-patient-${stamp}@example.com`
  const password = `E2ePass${stamp % 100000}`

  // Register (Login page register mode).
  await page.goto('/login')
  await page.getByText('New here? Create an account').click()
  await page.getByPlaceholder('Your full name').fill('E2E Patient')
  await page.getByPlaceholder('name@example.com').fill(email)
  await page.getByPlaceholder('Enter your password').fill(password)
  await page.getByRole('button', { name: /Create Patient Account/ }).click()
  await expect(page).toHaveURL(/dashboard/, { timeout: 15000 })

  // Upload a synthetic text report with known low/high values.
  const tmp = path.join(os.tmpdir(), `e2e-report-${stamp}.txt`)
  fs.writeFileSync(tmp, 'Hemoglobin 9.5 g/dL\nWBC 12,000 /cumm\nVitamin D 25 ng/mL\n')
  await page.goto('/reports')
  await page.getByPlaceholder(/Complete Blood Count/).fill('E2E CBC Report')
  await page.locator('input[type="file"]').setInputFiles(tmp)
  await page.getByRole('button', { name: /Upload & Analyze Report/ }).click()
  await expect(page.getByTestId('lab-results-table')).toBeVisible({ timeout: 30000 })

  // Flagged labs are visible with badges.
  const table = page.getByTestId('lab-results-table')
  await expect(table.getByText('Low')).toBeVisible()
  await expect(table.getByText('High')).toBeVisible()
  fs.unlinkSync(tmp)
})
