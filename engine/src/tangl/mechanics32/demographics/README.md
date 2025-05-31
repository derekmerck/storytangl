# International Demographics Generator  

This library provides a "Demographic" dataclass and factory for sampling romanized world names by region, country, and ethnic subtype.

It also includes a provider wrapper for use with Faker in `demographics.faker`

## Features

- Romanized foreign names by gender, country, region, race
- Follows statistical country and race population distributions
- Does NOT follow statistical name distributions within a country name bank
- Does NOT respect localized name order, i.e., surname precedes given name

The name lists in resources/world_names.yaml are indexed by country code
and sub-categorized by gender and first/last.

Some mixed-origin name types are very broad and require additional specification,
specifically usa_(european|asian|black|latinx) and zaf_(european|black).

Some surnames include enumerated masculine variants keyed as "male_surnames" 
(e.g. isl, ukr, etc.).

## Credits

The name bank was primarily compiled from the FreeCities Twine game.  Someone put a lot of work into it.  Other demographic data, such as populations and demonyms were scraped from the web.

## StoryTangl Dependencies

Demographics is independent of the StoryTangl code base other than convenience functions.
