Game Mechanics
==============

Game mechanics model various complex interactions that can be wrapped in interactive GameBlocks. The framework follows the common handler/component pattern.

The GameHandler encapsulates all functionality into just a few public api calls:

- `setup_game`
- `get_possible_moves`
- `handle_player_move`
- `check_game_status`

The Game component class itself is only responsible for managing and dumping state when required, such as for assigning namespace variables to evaluate win conditions at higher levels.

Games progress over "rounds", to distinguish them from story "turns".  One turn of the base story structure (i.e., one block) may comprise multiple games with multiple rounds.

Types of Games
--------------

Game structure is defined by three axes: 
- player relationship (solo, competitive, cooperative, multiple)
- state-dependency
- genre: like simple, token, picking, card, board

Examples:
- solo games: blackjack, slots, find the x, solitaire, clickers
- competitive games: rock/paper/scissors, most token/card/board games, auctions

- state-independent games: rps, find the x
- state-dependent games: most token/card/board games, clickers

- simple games: require no equipment, often-state independent, rps
- token games: requires fungible markers, nim
- picking games: require target and distractor markers, memory, waldo
- card game: requires an ordered set of markers, blackjack, poker
- board game: requires a map of positions for markers, checkers, life
