% program4.pl
% ∀x. WorksHard(x) → (StudiesMath(x) ∨ StudiesPhysics(x)) → Succeeds(x)

% Facts
person(alice).
person(bob).
person(charlie).

studies_math(alice).
studies_physics(bob).
works_hard(bob).
works_hard(charlie).

% Nested implication expands to two rules
succeeds(X) :-
    works_hard(X),
    studies_math(X).

succeeds(X) :-
    works_hard(X),
    studies_physics(X).

% On load: print all solutions and exit
:- initialization(main).
main :-
    forall(succeeds(X), writeln(X)),
    halt.
