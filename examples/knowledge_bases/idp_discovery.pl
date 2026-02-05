% IDP (Intrinsically Disordered Proteins) Discovery Scenario
% From the BLANC research paper
% Demonstrates how defeasible logic models scientific revolutions

% Traditional structure-function dogma
% "All functional proteins have a fixed 3D structure"

% Protein facts
protein(alpha_synuclein).
protein(myoglobin).
protein(hemoglobin).
protein(tau).

% Structural properties
has_fixed_structure(myoglobin).
has_fixed_structure(hemoglobin).
lacks_fixed_structure(alpha_synuclein).
lacks_fixed_structure(tau).

% Functional properties
functionally_active(alpha_synuclein).
functionally_active(myoglobin).
functionally_active(hemoglobin).
functionally_active(tau).

% Traditional dogma (defeasible rule)
% This was the prevailing belief before IDP discovery
functional(P) :- 
    protein(P), 
    has_fixed_structure(P).

% IDP classification
% The revolutionary discovery: some proteins are intrinsically disordered
intrinsically_disordered(P) :- 
    protein(P),
    lacks_fixed_structure(P),
    functionally_active(P).

% New understanding: IDPs can be functional despite lacking structure
% This defeats the traditional dogma for these special cases
functional(P) :- intrinsically_disordered(P).

% Scientific metadata (for research)
discovered_year(alpha_synuclein, 1997).
discovered_year(tau, 1975).
disease_association(alpha_synuclein, parkinsons).
disease_association(tau, alzheimers).

% Research implications
paradigm_shift(idp_discovery) :-
    protein(P),
    intrinsically_disordered(P),
    functionally_active(P),
    lacks_fixed_structure(P).

% Query examples:
% ?- functional(alpha_synuclein).  % Should succeed via IDP exception
% ?- functional(myoglobin).         % Should succeed via traditional rule
% ?- intrinsically_disordered(X).   % Find all IDPs
% ?- paradigm_shift(X).              % Demonstrate the paradigm shift
