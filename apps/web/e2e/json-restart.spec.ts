import { expect, test, type BrowserContext, type Page } from '@playwright/test'
import { execFileSync, spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { cp, mkdir, mkdtemp, readdir, rm, readFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { isChoiceFragment } from '../src/components/story/fragmentUtils'
import type { RuntimeEnvelope, UserInfo, UserSecretResponse } from '../src/types'

const web = path.resolve(import.meta.dirname, '..')
const origin = 'http://127.0.0.1:4173'
type Backend = {
  child: ChildProcessWithoutNullStreams
  closed: Promise<void>
  output: () => string
  root: string
  phase: string
}

// This one reference-world test owns exactly two processes; no production control endpoint.
async function startServer(root: string, phase: 'a' | 'b'): Promise<Backend> {
  await new Promise<void>((resolve, reject) => {
    const port = createServer()
    port.once('error', reject)
    port.listen(4173, '127.0.0.1', () => port.close(() => resolve()))
  })
  const python = execFileSync('poetry', ['env', 'info', '--executable'], {
    cwd: web,
    encoding: 'utf8',
  }).trim()
  const child = spawn(
    python,
    ['e2e/server.py', '--root', root, '--profile', 'json_file', '--log-name', `json-${phase}.log`],
    { cwd: web }
  )
  let output = ''
  child.stdout.on('data', (chunk) => {
    output += chunk.toString()
  })
  child.stderr.on('data', (chunk) => {
    output += chunk.toString()
  })
  const closed = new Promise<void>((resolve, reject) => {
    child.once('close', () => resolve())
    child.once('error', reject)
  })
  const server = { child, closed, output: () => output, root, phase }
  try {
    await expect
      .poll(
        async () => {
          if (child.exitCode !== null || child.signalCode !== null) throw new Error(output)
          if (!output.includes('Uvicorn running')) return false
          try {
            return (
              await fetch(`${origin}/api/v2/system/info`, { signal: AbortSignal.timeout(500) })
            ).ok
          } catch {
            return false
          }
        },
        { timeout: 20_000, message: `JSON process ${phase} readiness` }
      )
      .toBe(true)
    return server
  } catch (error) {
    try {
      await stopServer(server)
    } finally {
      throw error
    }
  }
}

async function stopServer(server: Backend) {
  if (server.child.exitCode === null && server.child.signalCode === null)
    server.child.kill('SIGTERM')
  try {
    await Promise.race([
      server.closed,
      delay(10_000, undefined, { ref: false }).then(() => {
        throw new Error('Graceful shutdown timed out')
      }),
    ])
  } catch (error) {
    server.child.kill('SIGKILL')
    await server.closed
    throw error
  }
  expect(server.output()).toContain('Application shutdown complete')
}

const identity = (envelope: RuntimeEnvelope) => ({
  ledger: envelope.metadata?.ledger_id,
  world: envelope.metadata?.world_id,
  cursor: envelope.cursor_id,
  step: envelope.step,
  choices: envelope.fragments
    .filter(isChoiceFragment)
    .map(({ uid, edge_id, text, available }) => ({ uid, edge_id, text, available })),
})

const renderedHistory = async (page: Page) => ({
  fragments: await page.locator('.fragment-row').allTextContents(),
  choices: await page.locator('button.choice-button').allTextContents(),
})

async function assertHistoryAndFrontier(page: Page, envelope: RuntimeEnvelope) {
  await expect(page.getByText(/The Crossroads Inn sits at the junction/)).toHaveCount(1)
  await expect(page.getByRole('button', { name: /Approach the fireplace/ })).toBeDisabled()
  await expect(
    page.getByRole('button', { name: /I'm looking for the Northern Pass/ })
  ).toBeDisabled()
  await expect(page.locator('button.choice-button:enabled')).toHaveCount(
    envelope.fragments.filter(isChoiceFragment).filter((item) => item.available !== false).length
  )
  for (const choice of envelope.fragments
    .filter(isChoiceFragment)
    .filter((item) => item.available !== false)) {
    await expect(
      page.locator('button.choice-button').filter({ hasText: choice.text! })
    ).toBeEnabled()
  }
  const image = page.locator('img[src$="/media/world/reference/images/tavern.svg"]').last()
  await expect
    .poll(() => image.evaluate((item) => (item as HTMLImageElement).naturalWidth))
    .toBeGreaterThan(0)
}

test('JSON story survives backend restart and recovery through a fresh browser UI', async ({
  page,
  browser,
}, info) => {
  const root = await mkdtemp(path.join(tmpdir(), 'storytangl-browser-json-'))
  await cp(path.resolve(web, '../../worlds/reference'), path.join(root, 'worlds/reference'), {
    recursive: true,
  })
  for (const directory of ['user_data', 'story_media', 'cache_data'])
    await mkdir(path.join(root, directory))
  const contexts: BrowserContext[] = []
  const extraPages: Page[] = []
  const errors: string[] = []
  const observations: Array<Record<string, unknown>> = []
  const creations: string[] = []
  const submissions: unknown[] = []
  let expectedInvalidSecret = false
  let failed = false
  let running: Awaited<ReturnType<typeof startServer>> | undefined
  const processes: Array<{ pid: number | undefined; root: string; phase: string }> = []
  const watch = (observed: Page, name: string) => {
    observed.on('pageerror', (error) => errors.push(`${name}: ${error.message}`))
    observed.on('console', (message) => {
      if (message.type() === 'error') {
        observations.push({ browser: name, consoleError: message.text() })
        if (
          !(
            expectedInvalidSecret &&
            (message.text().includes('401') ||
              message.text().startsWith('Response error:') ||
              message.text().startsWith('Failed to initialize authentication:'))
          )
        )
          errors.push(`${name}: ${message.text()}`)
      }
    })
    observed.on('requestfailed', (request) =>
      errors.push(`${name}: ${request.url()} ${request.failure()?.errorText}`)
    )
    observed.on('request', (request) => {
      const pathname = new URL(request.url()).pathname
      if (pathname.endsWith('/story/create')) creations.push(name)
      if (pathname.endsWith('/story/do')) submissions.push(request.postDataJSON())
      if (pathname.endsWith('/user/world')) errors.push('Unsupported user/world request')
      observations.push({ browser: name, method: request.method(), path: pathname })
    })
    observed.on('response', (response) => {
      const pathname = new URL(response.url()).pathname
      if (!/^\/(api|media)\//.test(pathname)) return
      observations.push({ browser: name, path: pathname, status: response.status() })
      if (
        response.status() >= 400 &&
        !(expectedInvalidSecret && response.status() === 401 && pathname.endsWith('/user/info'))
      )
        errors.push(`${name}: ${pathname} ${response.status()}`)
    })
  }
  const currentResponse = (observed: Page) =>
    observed.waitForResponse(
      (response) =>
        new URL(response.url()).pathname.endsWith('/story/update') &&
        new URL(response.url()).searchParams.has('since_step')
    )
  watch(page, 'a')

  try {
    running = await startServer(root, 'a')
    processes.push({ pid: running.child.pid, root: running.root, phase: 'a' })
    const playerCreated = page.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/user/create')
    )
    await page.goto('/')
    const credentials = (await (await playerCreated).json()) as UserSecretResponse
    await expect(page.getByText('Choose a world from Worlds')).toBeVisible()
    const secret = await page.evaluate(() => localStorage.getItem('storytangl.player-secret'))
    expect(secret).toBe(credentials.user_secret)
    await page.getByRole('button', { name: 'Worlds', exact: true }).click()
    const createdResponse = page.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/story/create')
    )
    await page.getByText('The Crossroads Inn', { exact: true }).click()
    let current = (await (await createdResponse).json()) as RuntimeEnvelope
    const tavern = page.locator('img[src$="/media/world/reference/images/tavern.svg"]').last()
    await expect
      .poll(() => tavern.evaluate((image) => (image as HTMLImageElement).naturalWidth))
      .toBeGreaterThan(0)
    for (const text of ['Approach the fireplace', "I'm looking for the Northern Pass"]) {
      const choice = current.fragments.filter(isChoiceFragment).find((item) => item.text === text)!
      const moved = page.waitForResponse((response) =>
        new URL(response.url()).pathname.endsWith('/story/do')
      )
      await page.getByRole('button', { name: new RegExp(text) }).click()
      const response = await moved
      expect(response.request().postDataJSON().edge_id).toBe(choice.edge_id)
      const next = (await response.json()) as RuntimeEnvelope
      expect(next.step).toBeGreaterThan(current.step!)
      expect(next.cursor_id).not.toBe(current.cursor_id)
      current = next
    }
    expect(current.step).toBe(3)
    const saved = identity(current)
    await page.locator('button[data-info-channel="ui-sidebar"]').click()
    await expect(
      page.locator('.story-status-item').filter({ has: page.getByText('Step', { exact: true }) })
    ).toContainText('3')
    await expect(
      page.getByRole('button', { name: /Offer to split any treasure found/ })
    ).toBeEnabled()
    const savedHistory = await renderedHistory(page)
    expect(await readdir(path.join(root, 'user_data'))).toContain(`${saved.ledger}.json`)

    await stopServer(running)
    expect(running.output()).toContain('Application shutdown complete')
    running = undefined
    running = await startServer(root, 'b')
    processes.push({ pid: running.child.pid, root: running.root, phase: 'b' })
    expect(processes[0]!.pid).not.toBe(processes[1]!.pid)
    expect(processes[0]!.root).toBe(processes[1]!.root)
    const restoredUserResponse = page.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/user/info')
    )
    const resumed = currentResponse(page)
    await page.reload()
    const restoredUser = (await (await restoredUserResponse).json()) as UserInfo
    current = await (await resumed).json()
    expect(restoredUser.user_id).toBe(credentials.user_id)
    expect(restoredUser.current_ledger_id).toBe(saved.ledger)
    expect(identity(current)).toEqual(saved)
    await assertHistoryAndFrontier(page, current)
    expect(await renderedHistory(page)).toEqual(savedHistory)
    expect(creations).toHaveLength(1)

    const contextB = await browser.newContext({ baseURL: origin, serviceWorkers: 'block' })
    expect(await contextB.storageState()).toEqual({ cookies: [], origins: [] })
    contexts.push(contextB)
    const fresh = await contextB.newPage()
    extraPages.push(fresh)
    watch(fresh, 'b')
    const freshPlayer = fresh.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/user/create')
    )
    const freshInfo = fresh.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/user/info')
    )
    await fresh.goto('/')
    const freshCredentials = (await (await freshPlayer).json()) as UserSecretResponse
    expect(freshCredentials.user_id).not.toBe(credentials.user_id)
    const unrelated = (await (await freshInfo).json()) as UserInfo
    expect(unrelated.user_id).toBe(freshCredentials.user_id)
    expect(unrelated.current_ledger_id).toBeNull()
    await expect(fresh.getByText('Choose a world from Worlds')).toBeVisible()
    expect(
      await fresh.evaluate(() =>
        navigator.serviceWorker.getRegistrations().then((items) => items.length)
      )
    ).toBe(0)
    await expect(fresh.locator('button.choice-button')).toHaveCount(0)
    await fresh.getByRole('button', { name: 'User', exact: true }).click()
    await fresh.getByText('Switch or Recover Player', { exact: true }).click()
    await fresh
      .getByTestId('authentication-secret')
      .locator('input')
      .fill('not-a-real-recovery-secret')
    expectedInvalidSecret = true
    const invalidRecovery = fresh.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/user/info')
    )
    await fresh.getByTestId('authentication-existing').click()
    expect((await invalidRecovery).status()).toBe(401)
    await expect(fresh.getByTestId('authentication-error')).toBeVisible()
    expectedInvalidSecret = false
    await fresh.getByTestId('authentication-secret').locator('input').fill(secret!)
    const recoveredUser = fresh.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/user/info')
    )
    const recovered = currentResponse(fresh)
    await fresh.getByTestId('authentication-existing').click()
    const recoveredProfile = (await (await recoveredUser).json()) as UserInfo
    expect(recoveredProfile.user_id).toBe(credentials.user_id)
    expect(recoveredProfile.current_ledger_id).toBe(saved.ledger)
    current = await (await recovered).json()
    expect(identity(current)).toEqual(saved)
    await assertHistoryAndFrontier(fresh, current)
    expect(await renderedHistory(fresh)).toEqual(savedHistory)
    const choice = current.fragments
      .filter(isChoiceFragment)
      .find((item) => item.text === 'Offer to split any treasure found')!
    const advancement = fresh.waitForResponse((response) =>
      new URL(response.url()).pathname.endsWith('/story/do')
    )
    await fresh.getByRole('button', { name: /Offer to split any treasure found/ }).click()
    const advancedResponse = await advancement
    expect(advancedResponse.request().postDataJSON().edge_id).toBe(choice.edge_id)
    const advanced = (await advancedResponse.json()) as RuntimeEnvelope
    expect(advanced.step).toBeGreaterThan(saved.step!)
    expect(advanced.cursor_id).not.toBe(saved.cursor)
    expect(advanced.metadata?.ledger_id).toBe(saved.ledger)
    await expect(
      fresh.getByRole('button', { name: /Continue deeper into the forest/ })
    ).toBeEnabled()
    const advancedHistory = await renderedHistory(fresh)
    const readback = currentResponse(fresh)
    await fresh.reload()
    expect(identity(await (await readback).json())).toEqual(identity(advanced))
    await assertHistoryAndFrontier(fresh, advanced)
    expect(await renderedHistory(fresh)).toEqual(advancedHistory)

    // The unrelated player's observed real credential cannot read or act on this story.
    const deniedRead = await fresh.request.get('/api/v2/story/update', {
      headers: { 'X-API-Key': freshCredentials.api_key },
    })
    expect(deniedRead.status()).toBe(400)
    expect((await deniedRead.json()).detail).toBe('No active story')
    const deniedMove = await fresh.request.post('/api/v2/story/do', {
      headers: { 'X-API-Key': freshCredentials.api_key },
      data: { edge_id: choice.edge_id },
    })
    expect(deniedMove.status()).toBe(400)
    expect((await deniedMove.json()).detail).toBe('No active story')
    const finalReadback = currentResponse(fresh)
    await fresh.reload()
    expect(identity(await (await finalReadback).json())).toEqual(identity(advanced))
    await assertHistoryAndFrontier(fresh, advanced)
    expect(creations).toHaveLength(1)
    expect(submissions).toHaveLength(3)
    expect(
      observations.filter((item) => item.method === 'POST' && item.path === '/api/v2/user/create')
    ).toHaveLength(2)
    expect(errors).toEqual([])
    await info.attach('json-restart-identity', {
      body: JSON.stringify(
        { processes, saved, advanced: identity(advanced), user: restoredUser.user_id },
        null,
        2
      ),
      contentType: 'application/json',
    })
  } catch (error) {
    failed = true
    throw error
  } finally {
    try {
      const results = await Promise.allSettled([
        running ? stopServer(running) : Promise.resolve(),
        ...contexts.map(async (context, index) => {
          try {
            const extra = extraPages[index]
            if (failed && extra && !extra.isClosed())
              await extra.screenshot({ path: info.outputPath(`context-${index}.png`) })
          } finally {
            await context.close()
          }
        }),
      ])
      const cleanupErrors = results
        .filter((result) => result.status === 'rejected')
        .map((result) => String(result.reason))
      await info.attach('network-and-errors', {
        body: JSON.stringify({ observations, errors, creations, submissions }, null, 2),
        contentType: 'application/json',
      })
      for (const phase of ['a', 'b']) {
        const log = path.join(web, 'e2e-artifacts', `json-${phase}.log`)
        if (failed)
          await info.attach(`server-${phase}`, {
            body: await readFile(log).catch(() => Buffer.from('Process did not start')),
            contentType: 'text/plain',
          })
      }
      if (cleanupErrors.length) {
        await info.attach('cleanup-errors', {
          body: cleanupErrors.join('\n'),
          contentType: 'text/plain',
        })
        if (!failed) throw new Error(cleanupErrors.join('\n'))
      }
    } finally {
      await rm(root, { recursive: true, force: true })
      await expect(readdir(root)).rejects.toMatchObject({ code: 'ENOENT' })
      await info.attach('temporary-store-cleanup', {
        body: JSON.stringify({ root, removed: true }),
        contentType: 'application/json',
      })
    }
  }
})
