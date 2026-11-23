import { expect, test } from '@playwright/test'

import { choose, startWorld, watchErrors } from './witness'

test('concept_naming_demo attributes standalone speech without a fallback', async ({ page }) => {
  const errors = watchErrors(page)
  await startWorld(page, 'concept_naming_demo', 'Meeting Rin')
  await choose(page, 'Meet the girl')

  // The service realizes the speaker anonymously, then by name once introduced.
  const lines = page.getByTestId('attributed-line')
  await expect(lines).toHaveCount(2)
  await expect(lines.nth(0)).toContainText('the blonde girl')
  await expect(lines.nth(0)).toContainText('Hi, I am Rin.')
  await expect(lines.nth(1)).toContainText('Rin')
  await expect(page.getByTestId('fragment-fallback')).toHaveCount(0)
  await expect(page.locator('.story-scene').getByText('attributed')).toHaveCount(0)
  expect(errors).toEqual([])
})
