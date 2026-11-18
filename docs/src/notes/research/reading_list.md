# Reading List

The project library sorted by how closely each work needs to be read. This is a
first-pass triage. Many entries were proposed by research agents and have not
been read (they carry `origin-agent` and no `engaged-*` tag), so a tier is a
guess about relevance, not a judgment of the work.

Tiers are Zotero tags, and the lists below are generated from them, so re-tagging
an item in Zotero and re-exporting moves it here. To list a tier in a terminal:

```bash
poetry run python scripts/mini_bib.py -k triage-assess
```

| Tag | Tier | What a reading produces |
|---|---|---|
| `triage-assess` | Prior art: systems and models that do part of StoryTangl's job | A reading note: contributions, pitfalls, strategies to adopt or reject |
| `triage-review` | Relevant to a particular topic or approach | A reading note scoped to the topic it was filed under |
| `triage-summarize` | Ancillary background | One or two sentences in the library entry's abstract field |
| `triage-witness` | Games and gamebooks that exhibit a mechanic | A witness card: the mechanic, the StoryTangl capability it pressures, how it was engaged |

## From notes to a literature review

Reading notes are the raw material; the literature review is organized by topic.
Each `devref:<topic>` with enough notes gets a review page that synthesizes them
with inline `{cite}` references, and is revised as notes are added. A note
records:

- **Claim:** what the work argues or demonstrates, in a sentence.
- **Mechanism:** the model, representation, or algorithm, in StoryTangl's
  vocabulary where a correspondence exists.
- **Contributions:** what it settled that StoryTangl can take as given.
- **Pitfalls:** what failed or was reported as costly (authoring burden,
  opacity, scaling, soft-locks).
- **Strategies:** what to adopt, adapt, or explicitly reject, with the design
  doc or issue it bears on.
- **Engagement:** how closely it was read, and by whom.

## Prior art to assess

What to look for in each, grouped by the StoryTangl concern it bears on.

**Provisioning and storylets**

- {cite}`short_storylets_2019,short_storylets_2019-1,short_beyond_2016` — whether
  quality-based, salience-based, and waypoint structures are configurations of
  the offer and provisioning model rather than separate modes, and where Short's
  reported failure modes (grind, flat salience) would appear.
- {cite}`kreminski_sketching_2018` — where StoryTangl sits on the storylet design
  space's axes, and which regions it leaves unreachable.
- {cite}`garbe_storyassembler_2019` — what HTN fragment assembly buys over
  dependency-driven template provisioning.
- {cite}`otto_dendryscope_2023` — which symbolic checks on quality-based content
  belong in authoring validation.

**Drama management and solvers**

- {cite}`mateas_structuring_2005` — beats as the unit of content, and how Façade
  recovered from interruption, against episodes and the beat overlay.
- {cite}`weyhrauch_guiding_1997,nelson_search-based_2005` — search over plot with
  an evaluation function, and whether a deterministic engine needs one or only
  its validation half.
- {cite}`riedl_narrative_2010` — satisfying plot and character intention together
  in provisioning.
- {cite}`smith_answer_2011,gebser_multi-shot_2019` — answer-set programming as a
  validation or provisioning backend, and incremental solving for re-entrant
  planning.

**Open links, roles, and social simulation**

- {cite}`evans_versusimulationist_2014,dameris_praxish_2023` — social practices as
  scoped affordance providers: the nearest prior art for facets and role grants.
- {cite}`mccoy_social_2014,samuel_ensemble_2015` — volition as a weighted rule
  fold, compared with the additive changer fold; Ensemble's schema as a candidate
  off-the-shelf format.
- {cite}`crawford_assumptions_1999,crawford_balance_1986` — verb-centred design,
  and the Balance of Power formulas as a specification for the geopolitical
  world design.

**Transactions and resources**

- {cite}`martens_ceptre_2015,martens_programming_2015` — linear-logic resources:
  whether the wallet and transaction layer has linear semantics, and what Ceptre's
  stages say about concurrent timelines.

**Journal and discourse**

- {cite}`montfort_generating_2007` — separating content from narration (order,
  focalization): direct prior art for the discourse layer.
- {cite}`ryan_curating_2018,kreminski_felt_2019,kreminski_winnow_2021` — sifting
  queries over event history, against journal retrieval through slices and
  selectors.

**Authoring languages and runtimes**

- {cite}`nelson_inform_nodate` — rulebooks and rule specificity, against dispatch
  and specificity arbitration.
- {cite}`inkle_ink_2016,choice_of_games_llc_introduction_nodate,edwards_sugarcube_nodate`
  — flow and state semantics each codec target needs StoryTangl to represent.
- {cite}`interactive_fiction_technology_foundation_twee_nodate` — the interchange
  format a Twine codec reads and writes.
- {cite}`meretzky_learning_1989` — ZIL's object and action dispatch model.
- {cite}`renpy_contributors_renpy_2026` — the screen language and interaction loop,
  against the widget vocabulary and client projection.
- {cite}`plotkin_plotex_2012` — puzzle-constraint exploration as reachability
  validation.

```{bibliography}
:filter: keywords % "triage-assess"
:keyprefix: reading-
```

## Relevant by topic

Read for the topic each was filed under: narrative theory, formal methods,
shape and appearance models, story inference and generation, prose generation,
validation and design craft, credentials, social simulation, and learning
environments.

```{bibliography}
:filter: keywords % "triage-review"
:keyprefix: reading-
```

## Background to summarize

```{bibliography}
:filter: keywords % "triage-summarize"
:keyprefix: reading-
```

## Witnesses

Games and gamebooks, characterized rather than read. Their `witness-*` tags
(`witness-epistemic`, `witness-social`, `witness-stateful`, and so on) group them
by the kind of state they exhibit.

```{bibliography}
:filter: keywords % "triage-witness"
:keyprefix: reading-
```
