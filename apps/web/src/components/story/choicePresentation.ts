import type { ChoiceStoryFragment } from '@/types'

export const CHOICE_KEYS = '123456789abcdefghijklmnopqrstuvwyz'

const nonEmpty = (value: unknown): string | undefined => {
  if (typeof value !== 'string') {
    return undefined
  }
  const text = value.trim()
  return text || undefined
}

export const choiceKeyForPosition = (
  choice: ChoiceStoryFragment,
  position: number
): string | undefined => {
  if (choice.available === false) {
    return undefined
  }
  return nonEmpty(choice.ui_hints?.hotkey) ?? CHOICE_KEYS[position - 1]
}

export const choiceKeysForList = (choices: ChoiceStoryFragment[]): Array<string | undefined> => {
  const keys = choices.map((choice, index) => choiceKeyForPosition(choice, index + 1))
  const seen = new Map<string, { position: number; edgeId: string }>()

  keys.forEach((key, index) => {
    if (key === undefined) {
      return
    }
    const normalized = key.toLowerCase()
    const previous = seen.get(normalized)
    if (previous) {
      throw new Error(
        `Duplicate choice hotkey "${normalized}" for positions ${previous.position} ` +
          `(${previous.edgeId}) and ${index + 1} (${choices[index]!.edge_id})`
      )
    }
    seen.set(normalized, { position: index + 1, edgeId: choices[index]!.edge_id })
  })

  return keys
}

export const choicePresentation = (choice: ChoiceStoryFragment) => {
  const blockers = choice.blockers ?? []
  const replacement = blockers.find((blocker) => blocker.replaces_text && nonEmpty(blocker.message))
  if (replacement) {
    return {
      text: nonEmpty(replacement.message)!,
      refusal: undefined,
      refusalRefs: [] as string[],
      refusalFromBlocker: false,
    }
  }

  const written = blockers.find((blocker) => nonEmpty(blocker.message))
  return {
    text: choice.text,
    refusal: nonEmpty(written?.message) ?? nonEmpty(choice.unavailable_reason),
    refusalRefs: (written?.refs ?? []).filter((ref): ref is string => typeof ref === 'string'),
    refusalFromBlocker: written !== undefined,
  }
}
