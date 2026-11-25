import { expect, test } from '@playwright/test'

import { choose, startWorld, watchErrors } from './witness'

test('repartee_loop preferences toggle bound art locally, with no story step', async ({
  page,
}) => {
  const errors = watchErrors(page)
  const writes: string[] = []
  page.on('request', (request) => {
    if (request.method() !== 'GET') writes.push(new URL(request.url()).pathname)
  })
  await startWorld(page, 'repartee_loop', 'Marmoset Island')
  const court = await choose(page, 'Step into the practice court')
  const stage = page.getByTestId('stage')
  const clerk = stage.locator('img[data-stage-role="dialog_im"]')
  const prefs = page.getByTestId('world-preferences')
  await expect(clerk).toHaveAttribute('data-clip', 'idle')
  writes.length = 0

  await prefs.locator('[data-preference="clerk-motion"]').getByRole('button', { name: 'call' }).click()
  await expect(clerk).toHaveAttribute('data-clip', 'call')
  await prefs.getByLabel('Decorative sprites').uncheck()
  await expect(clerk).toHaveCount(0)
  await expect(stage.locator('img[data-stage-role="narrative_im"]')).toBeVisible()
  expect(writes).toEqual([])
  expect(
    await page.evaluate(() => localStorage.getItem('storytangl.ui-preferences.repartee_loop'))
  ).toBe(JSON.stringify({ 'sprites-visible': false, 'clerk-motion': 'call' }))

  // The choice stays where the story left it, and the values outlive a reload.
  const resumed = page.waitForResponse((r) => new URL(r.url()).searchParams.has('since_step'))
  await page.reload()
  expect((await (await resumed).json()).step).toBe(court.step)
  await expect(prefs.getByLabel('Decorative sprites')).not.toBeChecked()
  await expect(stage.locator('img[data-stage-role="narrative_im"]')).toBeVisible()
  await expect(clerk).toHaveCount(0)
  await prefs.getByLabel('Decorative sprites').check()
  await expect(clerk).toHaveAttribute('data-clip', 'call')
  expect(writes).toEqual([])
  expect(errors).toEqual([])
})
