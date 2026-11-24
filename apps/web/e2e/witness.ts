import { expect, type Page } from '@playwright/test'

/** What a witness must never see: page or console errors, failed requests, HTTP errors. */
export const watchErrors = (page: Page): string[] => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText
    // A reload cancels an <audio> element's in-flight load; that is not a failure.
    const cancelled = failure === 'net::ERR_ABORTED' && request.resourceType() === 'media'
    if (!cancelled) errors.push(`${request.url()}: ${failure}`)
  })
  page.on('response', (response) => {
    const path = new URL(response.url()).pathname
    if (/^\/(api|media)\//.test(path) && response.status() >= 400) {
      errors.push(`${path}: HTTP ${response.status()}`)
    }
  })
  return errors
}

/** Start a fresh story through the Worlds menu, as a new player would. */
export const startWorld = async (page: Page, worldId: string, title: string) => {
  await page.goto('/')
  await expect(page.getByText('Choose a world from Worlds')).toBeVisible()
  await page.getByRole('button', { name: 'Worlds', exact: true }).click()
  const creation = page.waitForResponse((r) =>
    r.url().endsWith(`/api/v2/story/create?world_id=${worldId}&init_mode=EAGER`)
  )
  await page.getByText(title, { exact: true }).click()
  return (await creation).json()
}

/** Take the offered choice with this label and wait for its step. */
export const choose = async (page: Page, label: string) => {
  const step = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith('/story/do'))
  await page.getByRole('button', { name: label }).click()
  return (await step).json()
}
