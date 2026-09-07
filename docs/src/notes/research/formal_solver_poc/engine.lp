%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% engine.lp -- generic machinery for the finishability formalism.
%% Content packs supply: action/1, trigger/1, pre/2, add/2, del/2,
%% init/1, goal/1.  The engine supplies time, inertia, firing rules.
%%
%% The five-field atom maps on as:
%%   condition  -> pre(Action, Fluent)     (conjunction: one fact per conjunct)
%%   cost       -> del(Action, Fluent)     (consuming a linear token IS the cost)
%%   effect     -> add(Action, Fluent)
%%   discovery  -> add(Action, state(X, known))   (just an effect on a visibility fluent)
%%   trigger    -> trigger(Action)         (absent = player-invoked)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#const h = 12.                 % planning horizon (overridden by the driver)
step(0..h-1).

%% ----- initial state ---------------------------------------------------
holds(F, 0) :- init(F).

%% ----- when is an action possible? -------------------------------------
%% poss(A,T) holds iff every precondition fluent of A holds at T.
poss(A, T) :- action(A), step(T), holds(F, T) : pre(A, F).

%% ----- player choice: at most one non-trigger action per step ----------
{ occurs(A, T) : action(A), not trigger(A) } 1 :- step(T).
:- occurs(A, T), not poss(A, T).          % chosen actions must be legal

%% ----- triggers: fire automatically, at most once, when possible -------
%% (fired-latch makes cascades one-shot; monotone latch keeps things finite)
occurs(A, T) :- trigger(A), poss(A, T), not holds(fired(A), T).
holds(fired(A), T+1) :- occurs(A, T), trigger(A).
holds(fired(A), T+1) :- holds(fired(A), T), step(T).

%% ----- effects and inertia (the frame axiom) ---------------------------
holds(F, T+1) :- occurs(A, T), add(A, F).
holds(F, T+1) :- holds(F, T), step(T), not removed(F, T).
removed(F, T) :- occurs(A, T), del(A, F).

%% consuming a fluent requires it to be present (no double-spending)
:- occurs(A, T), del(A, F), not holds(F, T).

%% ----- goal ------------------------------------------------------------
:- goal(F), not holds(F, h).

%% ----- prefer shorter plans at a fixed horizon -------------------------
#minimize { 1, A, T : occurs(A, T), not trigger(A) }.

#show occurs/2.
