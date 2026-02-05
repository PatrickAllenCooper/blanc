% Family relationships knowledge base
% Demonstrates transitive relations and complex queries

% Gender facts
male(tom).
male(bob).
male(jim).
male(pat).
female(liz).
female(ann).
female(sue).

% Parent relationships
parent(tom, bob).
parent(tom, liz).
parent(bob, ann).
parent(bob, pat).
parent(pat, jim).
parent(liz, sue).

% Derived relationships

% Father and mother
father(X, Y) :- parent(X, Y), male(X).
mother(X, Y) :- parent(X, Y), female(X).

% Grandparent
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
grandfather(X, Z) :- grandparent(X, Z), male(X).
grandmother(X, Z) :- grandparent(X, Z), female(X).

% Siblings
sibling(X, Y) :- parent(P, X), parent(P, Y), X \= Y.
brother(X, Y) :- sibling(X, Y), male(X).
sister(X, Y) :- sibling(X, Y), female(X).

% Aunts and uncles
aunt(X, Y) :- parent(P, Y), sister(X, P).
uncle(X, Y) :- parent(P, Y), brother(X, P).

% Ancestors (transitive closure)
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).

% Descendants
descendant(X, Y) :- ancestor(Y, X).
