%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% world.lp -- content pack: two rooms, the mom cascade, one soft-lock trap.
%% Everything here is data. The engine never changes.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% ----- initial configuration: the minimal unlocked seed ----------------
init(state(alice, known)).
init(state(home,  known)).
init(empty(room1)).
init(empty(room2)).
init(stock(icecream)).          % the shop has exactly ONE ice cream (linear!)

%% ----- monotone unlock chain (knowledge gates, reusable forever) -------
action(chat_alice).
  pre(chat_alice, state(alice, known)).
  add(chat_alice, state(alice, befriended)).
  add(chat_alice, state(park,  known)).          % alice mentions the park

action(visit_park).
  pre(visit_park, state(park, known)).
  add(visit_park, state(tom,  known)).           % you meet tom there
  add(visit_park, state(shop, known)).           % and spot the ice cream shop

%% ----- linear resources (the consumable economy) -----------------------
action(buy_icecream).
  pre(buy_icecream, state(shop, known)).
  pre(buy_icecream, stock(icecream)).
  del(buy_icecream, stock(icecream)).            % supply is finite
  add(buy_icecream, has(icecream)).

action(eat_icecream).                            % the soft-lock trap: pure
  pre(eat_icecream, has(icecream)).              % consumption, no progress
  del(eat_icecream, has(icecream)).

action(befriend_tom).
  pre(befriend_tom, state(tom, known)).
  pre(befriend_tom, has(icecream)).
  del(befriend_tom, has(icecream)).              % the favor is SPENT
  add(befriend_tom, state(tom,  befriended)).
  add(befriend_tom, state(gwen, known)).         % tom introduces gwen
  add(befriend_tom, state(hardware, known)).

action(buy_toolkit).                             % hardware restocks freely
  pre(buy_toolkit, state(hardware, known)).
  add(buy_toolkit, has(toolkit)).

action(fix_room1).
  pre(fix_room1, has(toolkit)).
  del(fix_room1, has(toolkit)).
  add(fix_room1, ready(room1)).

action(fix_room2).
  pre(fix_room2, has(toolkit)).
  del(fix_room2, has(toolkit)).
  add(fix_room2, ready(room2)).

%% ----- befriending and commitment (slot assignment) --------------------
action(befriend_gwen).
  pre(befriend_gwen, state(gwen, known)).
  pre(befriend_gwen, state(tom,  befriended)).
  add(befriend_gwen, state(gwen, befriended)).

action(offer_room1_gwen).
  pre(offer_room1_gwen, state(gwen, befriended)).
  pre(offer_room1_gwen, ready(room1)).
  pre(offer_room1_gwen, empty(room1)).
  del(offer_room1_gwen, empty(room1)).           % commitment: slot is taken
  add(offer_room1_gwen, housed(gwen)).

%% ----- the mom funnel ---------------------------------------------------
%% housing gwen makes mom surface (she hears you have space)
trigger(reveal_mom).  action(reveal_mom).
  pre(reveal_mom, housed(gwen)).
  add(reveal_mom, state(mom, known)).

action(invite_mom).                              % the inciting commitment
  pre(invite_mom, state(mom, known)).
  pre(invite_mom, ready(room2)).
  pre(invite_mom, empty(room2)).
  del(invite_mom, empty(room2)).
  add(invite_mom, housed(mom)).

%% the cascade: forced, one-shot, and it RAIDS the tableau
trigger(evict_gwen).  action(evict_gwen).
  pre(evict_gwen, housed(mom)).
  pre(evict_gwen, housed(gwen)).
  del(evict_gwen, housed(gwen)).                 % narrative eviction: free
  add(evict_gwen, empty(room1)).
  add(evict_gwen, gwen_gone).

trigger(partner_appears).  action(partner_appears).
  pre(partner_appears, gwen_gone).
  add(partner_appears, state(partner, known)).   % ONLY producer: cascade-bound

action(befriend_partner).
  pre(befriend_partner, state(partner, known)).
  add(befriend_partner, state(partner, befriended)).

action(reinvite_couple).                         % the second summit
  pre(reinvite_couple, state(partner, befriended)).
  pre(reinvite_couple, empty(room1)).
  pre(reinvite_couple, ready(room1)).
  del(reinvite_couple, empty(room1)).
  add(reinvite_couple, housed(gwen)).
  add(reinvite_couple, housed(partner)).

%% ----- the summit -------------------------------------------------------
goal(housed(mom)).
goal(housed(gwen)).
goal(housed(partner)).
