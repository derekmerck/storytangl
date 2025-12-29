
# Games

Games are semi-abstract descriptions of various game logic, moves, and rules.  Games can be wrapped by a {class}`~tangl.story.Challenge` block to create a story element that iterates through the game state until the player either wins or loses.

## Base Game

```{eval-rst}
.. autoclass:: tangl.games.basic_game.BasicGame
.. autoclass:: tangl.games.basic_player.BasicPlayer
```

## Rock-Paper-Scissors

```{eval-rst}
.. autoclass:: tangl.games.rps.RpsGame
.. autoclass:: tangl.games.rps.RpsPlayer
.. autoclass:: tangl.games.rps.Rps5Game
```

## Twenty-One (cards)

```{eval-rst}
.. autoclass:: tangl.games.twentyone.TwentyOneGame
.. autoclass:: tangl.games.twentyone.TwentyOnePlayer
.. autoclass:: tangl.games.twentytwo.TwentyTwoGame
```

## Bag Rock-Paper-Scissors (tokens)

```{eval-rst}
.. automodule:: tangl.games.bag_rps
```

## Incremental (tokens)

```{eval-rst}
.. automodule:: tangl.games.incremental
```
