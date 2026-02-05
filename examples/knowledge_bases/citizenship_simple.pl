% Simplified British Citizenship Rules
% Based on TaxKB citizenship example but in standard Prolog
% UK Nationality Act 1981

% Facts about people
person(john).
person(alice).
person(emma).
person(charlie).

% Birth information
born_in(john, uk, '2021-10-09').
born_in(emma, uk, '2019-03-15').
born_in(charlie, france, '2020-06-20').

% Parent relationships
mother(alice, john).
mother(alice, emma).
father(bob, charlie).

% Citizenship status (on dates)
british_citizen(alice, '2021-10-09').
british_citizen(alice, '2019-03-15').

% Settlement status
settled_in_uk(bob, '2020-06-20').

% Commencement date (when the act came into force)
after_commencement('2019-03-15').
after_commencement('2020-06-20').
after_commencement('2021-10-09').

% Main rule: Acquisition by birth (simplified from Section 1)
% A person acquires British citizenship by birth if:
% - Born in the UK after commencement
% - AND at least one parent is a British citizen or settled in UK
acquires_citizenship(Person, Date) :-
    born_in(Person, uk, Date),
    after_commencement(Date),
    (
        (mother(Parent, Person), british_citizen(Parent, Date));
        (father(Parent, Person), british_citizen(Parent, Date));
        (mother(Parent, Person), settled_in_uk(Parent, Date));
        (father(Parent, Person), settled_in_uk(Parent, Date))
    ).

% Derive citizenship at a later date
british_citizen(Person, LaterDate) :-
    acquires_citizenship(Person, AcquisitionDate),
    date_after(LaterDate, AcquisitionDate).

% Helper: check if one date is after another
% Simplified - real implementation would parse dates
date_after(Date1, Date2) :-
    Date1 @> Date2.

% Eligibility for naturalization (simplified)
% Requires being settled for 5 years
eligible_for_naturalization(Person) :-
    person(Person),
    settled_in_uk(Person, _),
    \+ british_citizen(Person, _).

% Query examples:
% ?- acquires_citizenship(Person, Date).
% ?- british_citizen(john, '2021-10-09').
% ?- eligible_for_naturalization(Person).
