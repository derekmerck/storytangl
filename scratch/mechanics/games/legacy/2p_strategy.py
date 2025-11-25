"""
Game ends when _either_ heap is emptied, the exhausted heap owner loses


2 suits, have to attack and defend

2xrange(0:5) red
2xrange(0:5) black




On your turn may _take_ any combination of 3 from either pile (0,3;1,2;2,1;3,0)

player loses if they have to draw the last from _their_ pile

attack w an open
defender plays equal or higher
attack w any value between min/max showing
if attacker can't play, they take all points showing
if defender can't respond, they take all points showing

"""

import random


NUM_CARDS = 5

p1_hand = list(range(0, NUM_CARDS))
p2_hand = list(range(0, NUM_CARDS))
prizes  = list(range(0, NUM_CARDS))

random.shuffle(prizes)

while prizes:
    p = prizes.pop()
    print(p)

    random.shuffle(p1_hand)
    p1 = p1_hand.pop()



exit()






piles = [12, 12]

def move(player):
    if player == 0:
        if piles == [1, 0]:
            raise RuntimeError("p1 lost")
        elif piles == [1, 1]:
            return (0, 1)

def random_move(max_, p0, p1):
    tk0 = random.randint( 0,  max_ )
    tk1 = random.randint( 0,  max_-tk0  )
    tk0 = min([tk0, max( [piles[0] - p0, 0])])
    tk1 = min([tk1, max( [piles[1] - p1, 0])])
    if tk0 + tk1 < 1:
        raise RuntimeError(f"No move for {'p0' if p0 else 'p1'}")
    return (tk0, tk1)

while any(piles):
    # p0
    print("piles: ", piles)
    mv = random_move(3,1,0)
    print("p0 mv", mv)
    piles[0] -= mv[0]
    piles[1] -= mv[1]
    # if piles[0] <= 0:
    #     raise RuntimeError("p0 lost")

    # p0
    print("piles: ", piles)
    mv = random_move(3,0,1)
    print("p1 mv", mv)
    piles[0] -= mv[0]
    piles[1] -= mv[1]
    # if piles[1] <= 0:
    #     raise RuntimeError("p1 lost!")





