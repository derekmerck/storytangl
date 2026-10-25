import { expect, test } from '@playwright/test'

test('a fresh player starts reference, chooses twice, inspects status, and reloads', async ({
  page,
}, info) => {
  const errors: string[] = []
  const players: string[] = []
  const requests: Array<{ path: string; method: string; body: unknown }> = []
  const responses: Array<{ path: string; status: number }> = []
  let hasLedger = false
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('requestfailed', (request) =>
    errors.push(`${request.url()}: ${request.failure()?.errorText}`)
  )
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname
    if (!path.startsWith('/api/')) return
    if (/\/story\/(update|info)$/.test(path) && !hasLedger) errors.push(`No ledger: ${path}`)
    requests.push({ path, method: request.method(), body: request.postDataJSON() })
  })
  page.on('response', async (response) => {
    const path = new URL(response.url()).pathname
    if (!/^\/(api|media)\//.test(path)) return
    responses.push({ path, status: response.status() })
    if (response.status() >= 400) errors.push(`${path}: HTTP ${response.status()}`)
    if (path.endsWith('/story/create') && response.ok()) hasLedger = true
    if (path.endsWith('/user/info') && response.ok()) {
      const user = await response.json()
      players.push(user.user_id)
      hasLedger = Boolean(user.current_ledger_id)
    }
  })

  try {
    await page.goto('/')
    await expect(page.getByText('Choose a world from Worlds')).toBeVisible()
    expect(await page.evaluate(() => localStorage.getItem('storytangl.player-secret'))).toBeTruthy()
    expect(
      await page.evaluate(() =>
        navigator.serviceWorker.getRegistrations().then((items) => items.length)
      )
    ).toBe(0)
    await page.getByRole('button', { name: 'Worlds', exact: true }).click()
    const creation = page.waitForResponse((r) =>
      r.url().endsWith('/api/v2/story/create?world_id=reference&init_mode=EAGER')
    )
    await page.getByText('The Crossroads Inn', { exact: true }).click()
    const created = await (await creation).json()
    expect(created.metadata.world_id).toBe('reference')
    expect(created.metadata.ledger_id).toBeTruthy()
    await expect(page.getByText(/The Crossroads Inn sits at the junction/)).toHaveCount(1)
    const tavern = page.locator('img[src$="/media/world/reference/images/tavern.svg"]').last()
    await expect(tavern).toBeVisible()
    await expect
      .poll(() => tavern.evaluate((image) => (image as HTMLImageElement).naturalWidth))
      .toBeGreaterThan(0)

    let current = created
    for (const text of ['Approach the fireplace', "I'm looking for the Northern Pass"]) {
      const offered = current.fragments.find(
        (item: { fragment_type: string; text?: string }) =>
          item.fragment_type === 'choice' && item.text === text
      )
      expect(offered).toBeTruthy()
      const step = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith('/story/do'))
      await page.getByRole('button', { name: new RegExp(text) }).click()
      const response = await step
      expect(response.request().postDataJSON().edge_id).toBe(offered.edge_id)
      const next = await response.json()
      expect(next.step).toBeGreaterThan(current.step)
      expect(next.cursor_id).not.toBe(current.cursor_id)
      current = next
    }
    await expect(page.getByRole('button', { name: /Approach the fireplace/ })).toBeDisabled()
    await expect(page.getByText(/Aria's expression softens/)).toBeVisible()
    await page.locator('button[data-info-channel="ui-sidebar"]').click()
    await expect(page.locator('.v-navigation-drawer')).toContainText('Step')
    await expect(
      page.locator('.story-status-item').filter({
        has: page.getByText('Step', { exact: true }),
      })
    ).toContainText(String(current.step))

    const secret = await page.evaluate(() => localStorage.getItem('storytangl.player-secret'))
    const resumed = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname.endsWith('/story/update') &&
        new URL(r.url()).searchParams.has('since_step')
    )
    await page.reload()
    const frontier = await (await resumed).json()
    expect(frontier.metadata.ledger_id).toBe(created.metadata.ledger_id)
    expect(frontier.step).toBe(current.step)
    expect(await page.evaluate(() => localStorage.getItem('storytangl.player-secret'))).toBe(secret)
    await expect(page.getByRole('button', { name: /Approach the fireplace/ })).toBeDisabled()
    await expect(
      page.getByRole('button', { name: /I'm looking for the Northern Pass/ })
    ).toBeDisabled()
    const currentChoices = frontier.fragments.filter(
      (item: { fragment_type: string; available?: boolean }) =>
        item.fragment_type === 'choice' && item.available !== false
    )
    await expect(page.locator('button.choice-button:enabled')).toHaveCount(currentChoices.length)
    await expect(page.getByText(/The Crossroads Inn sits at the junction/)).toHaveCount(1)
    expect(requests.filter((r) => r.path.endsWith('/story/create'))).toHaveLength(1)
    expect(requests.filter((r) => r.path.endsWith('/story/do'))).toHaveLength(2)
    expect(requests.some((r) => r.path.endsWith('/user/world'))).toBe(false)
    expect(players).toHaveLength(2)
    expect(new Set(players).size).toBe(1)
    expect(errors).toEqual([])
  } finally {
    await info.attach('network-and-errors', {
      body: JSON.stringify({ requests, responses, errors }, null, 2),
      contentType: 'application/json',
    })
  }
})
