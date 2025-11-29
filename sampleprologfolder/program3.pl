% program3.pl
% (∀x. StudiesMath(x)→Succeeds(x))  ∨  (∀x. (StudiesPhysics(x)∧WorksHard(x))→Succeeds(x))

% Facts
person(alice).
person(bob).
person(charlie).

studies_math(alice).
studies_physics(bob).
works_hard(bob).
works_hard(charlie).

% Toggle which implication you want:
option(math).      % ← comment this and uncomment the next to switch
% option(physics).

% Branch 1: StudiesMath(x) -> Succeeds(x)
succeeds(X) :-
    option(math),
    studies_math(X).

% Branch 2: (StudiesPhysics(x) ∧ WorksHard(x)) -> Succeeds(x)
succeeds(X) :-
    option(physics),
    studies_physics(X),
    works_hard(X).

% On load: print all solutions and exit
:- initialization(main).
main :-
    forall(succeeds(X), writeln(X)),
    halt.
