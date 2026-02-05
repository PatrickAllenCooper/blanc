% Simple medical diagnosis knowledge base
% Demonstrates rule-based diagnosis

% Patient symptoms (facts)
symptom(patient1, fever).
symptom(patient1, cough).
symptom(patient1, fatigue).

symptom(patient2, fever).
symptom(patient2, rash).

symptom(patient3, cough).
symptom(patient3, fatigue).
symptom(patient3, shortness_of_breath).

% Risk factors
recent_travel(patient1).
immunocompromised(patient3).

% Diagnostic rules

% Flu diagnosis
diagnosis(P, flu) :- 
    symptom(P, fever),
    symptom(P, cough),
    symptom(P, fatigue).

% COVID-19 diagnosis (more specific, takes precedence)
diagnosis(P, covid19) :- 
    symptom(P, fever),
    symptom(P, cough),
    recent_travel(P).

diagnosis(P, covid19) :-
    symptom(P, shortness_of_breath),
    symptom(P, fatigue).

% Measles diagnosis
diagnosis(P, measles) :- 
    symptom(P, fever),
    symptom(P, rash).

% Severity assessment
severe_case(P) :- 
    diagnosis(P, _),
    immunocompromised(P).

severe_case(P) :-
    symptom(P, shortness_of_breath).

% Treatment recommendations
treatment(P, antiviral) :- diagnosis(P, flu).
treatment(P, isolation) :- diagnosis(P, covid19).
treatment(P, vaccination) :- diagnosis(P, measles).
treatment(P, hospitalization) :- severe_case(P).
