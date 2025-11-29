% program2.pl
% ∀x. ((StudiesMath(x) ∨ StudiesPhysics(x)) ∧ WorksHard(x)) → Succeeds(x).

% Facts
person(alice).
person(bob).
person(charlie).

studies_math(alice).
studies_physics(bob).
works_hard(bob).
works_hard(charlie).

% Rule
succeeds(X) :-
    ( studies_math(X)
    ; studies_physics(X)
    ),
    works_hard(X).

% On load: print all solutions and exit
:- initialization(main).
main :-
    forall(succeeds(X), writeln(X)),
    halt.
