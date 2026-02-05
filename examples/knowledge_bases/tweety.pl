% Classic Tweety the penguin example
% Demonstrates defeasible reasoning

% Facts
bird(tweety).
bird(woody).
penguin(opus).

% Rules
% Birds typically fly (defeasible rule)
flies(X) :- bird(X), \+ penguin(X).

% Penguins are birds
bird(X) :- penguin(X).

% Penguins don't fly (defeats the general rule)
\+ flies(X) :- penguin(X).
