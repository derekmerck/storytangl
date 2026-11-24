import { expect, test, type Locator } from '@playwright/test'

import { choose, startWorld, watchErrors } from './witness'

const box = async (locator: Locator) => (await locator.boundingBox())!

/** A figure's box relative to its 320px-wide stage, read at one instant. */
const placement = (figure: Locator) =>
  figure.evaluate((img) => {
    const frame = img.closest('[data-testid="stage"]')!.getBoundingClientRect()
    const own = img.getBoundingClientRect()
    return {
      scale: frame.width / 320,
      aspect: frame.height / frame.width,
      left: own.left - frame.left,
      right: frame.right - own.right,
      bottom: frame.bottom - own.bottom,
      width: own.width,
      height: own.height,
    }
  })

test('repartee_loop stages its backdrop once and places its figures', async ({ page }, info) => {
  const errors = watchErrors(page)
  await startWorld(page, 'repartee_loop', 'Marmoset Island')
  const stage = page.getByTestId('stage')
  const backdrop = stage.locator('img[data-stage-role="narrative_im"]')
  await expect(backdrop).toHaveAttribute('src', /quai_bg\.png$/)
  await expect.poll(() => backdrop.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(320)

  await choose(page, 'Step into the practice court')
  await expect(page.locator('img[src$="quai_bg.png"]')).toHaveCount(1)
  const clerk = stage.locator('img[data-stage-role="dialog_im"]')
  await expect(clerk).toHaveAttribute('src', /clerk_sprite\.png$/)
  await expect.poll(() => clerk.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(102)

  // A 320x200 stage scaled as a whole: the 102x112 clerk stands at the left
  // station, a 10px gutter in, on the floor, mirrored -- not a full-width image.
  const figure = await placement(clerk)
  expect(figure.aspect).toBeCloseTo(200 / 320, 2)
  expect(figure.width).toBeCloseTo(102 * figure.scale, 0)
  expect(figure.height).toBeCloseTo(112 * figure.scale, 0)
  expect(figure.left).toBeCloseTo(10 * figure.scale, 0)
  expect(figure.bottom).toBeCloseTo(0, 0)
  expect(await clerk.evaluate((img) => getComputedStyle(img).transform)).toBe(
    'matrix(-1, 0, 0, 1, 0, 0)'
  )
  expect(await clerk.evaluate((img) => getComputedStyle(img).imageRendering)).toBe('pixelated')
  await info.attach('clerk-on-quay', { body: await stage.screenshot(), contentType: 'image/png' })

  // The map plate states no room, so the quay stays staged above it.
  await choose(page, 'Step out onto the quay')
  await expect(backdrop).toHaveAttribute('src', /quai_bg\.png$/)
  await expect(stage).toBeInViewport()
  await page.getByText('The district runs from the water').scrollIntoViewIfNeeded()
  await expect(page.locator('.story-scene').last().locator('img[src$="quay_map.png"]')).toBeVisible()

  await choose(page, 'Go to The Practice Yard')
  await expect(backdrop).toHaveAttribute('src', /warehouse_bg\.png$/)
  // The turn scrolls to its room, clear of the fixed app bar.
  const bar = await box(page.locator('.v-app-bar'))
  await expect.poll(async () => (await box(stage)).y).toBeGreaterThanOrEqual(bar.y + bar.height)
  await expect(stage).toBeInViewport({ ratio: 1 })
  const worker = stage.locator('img[data-stage-role="dialog_im"]')
  await expect(worker).toHaveAttribute('src', /worker_sprite\.png$/)
  await expect.poll(() => worker.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0)
  const right = await placement(worker)
  expect(right.right).toBeCloseTo(10 * right.scale, 0)
  expect(right.bottom).toBeCloseTo(0, 0)
  await expect(page.locator('img[src$="quai_bg.png"]')).toHaveCount(0)
  await info.attach('worker-in-yard', { body: await stage.screenshot(), contentType: 'image/png' })

  // Continue restores the journal as one flat envelope. Folded at its journal
  // steps, it stages the yard as live play did, without the court's clerk.
  await page.reload()
  await expect(backdrop).toHaveAttribute('src', /warehouse_bg\.png$/)
  await expect(stage.locator('img')).toHaveCount(2)
  await expect(worker).toHaveAttribute('src', /worker_sprite\.png$/)
  expect(errors).toEqual([])
})
