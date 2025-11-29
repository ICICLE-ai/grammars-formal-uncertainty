% program5.pl
% ∀x. Succeeds(x) ↔ (StudiesMath(x) ∨ (StudiesPhysics(x) ∧ WorksHard(x)))

% Facts
person(alice).
person(bob).
person(charlie).

studies_math(alice).
studies_physics(bob).
works_hard(bob).
works_hard(charlie).

% Forward direction
succeeds(X) :-
    studies_math(X).
succeeds(X) :-
    studies_physics(X),
    works_hard(X).

% Backward direction to enforce ↔
studies_math(X) :-
    succeeds(X),
    \+ (studies_physics(X), works_hard(X)).

studies_physics(X) :-
    succeeds(X),
    works_hard(X).

% On load: print all solutions and exit
:- initialization(main).
main :-
    forall(succeeds(X), writeln(X)),
    halt.
