% Simplified Nephrology Knowledge Base
% Based on NephroDoctor but using standard Prolog
% Demonstrates medical diagnosis reasoning

% Patient symptoms
symptom(patient1, hematuria).
symptom(patient1, proteinuria).
symptom(patient1, edema).

symptom(patient2, oliguria).
symptom(patient2, hypertension).
symptom(patient2, elevated_creatinine).

symptom(patient3, hematuria).
symptom(patient3, flank_pain).
symptom(patient3, fever).

% Lab values
lab_value(patient1, proteinuria_level, 3.5).  % g/day
lab_value(patient2, creatinine, 2.5).         % mg/dL
lab_value(patient2, bun, 45).                 % mg/dL

% Patient demographics
age(patient1, 45).
age(patient2, 68).
age(patient3, 28).

% Diagnostic rules

% Nephrotic syndrome: proteinuria > 3.5 g/day + edema
diagnosis(Patient, nephrotic_syndrome) :-
    symptom(Patient, proteinuria),
    symptom(Patient, edema),
    lab_value(Patient, proteinuria_level, Level),
    Level >= 3.5.

% Acute kidney injury: oliguria + elevated creatinine
diagnosis(Patient, acute_kidney_injury) :-
    symptom(Patient, oliguria),
    symptom(Patient, elevated_creatinine),
    lab_value(Patient, creatinine, Cr),
    Cr > 1.5.

% Glomerulonephritis: hematuria + proteinuria
diagnosis(Patient, glomerulonephritis) :-
    symptom(Patient, hematuria),
    symptom(Patient, proteinuria).

% Pyelonephritis: fever + flank pain + hematuria
diagnosis(Patient, pyelonephritis) :-
    symptom(Patient, fever),
    symptom(Patient, flank_pain),
    symptom(Patient, hematuria).

% Chronic kidney disease (based on age and creatinine)
diagnosis(Patient, chronic_kidney_disease) :-
    age(Patient, Age),
    Age > 65,
    lab_value(Patient, creatinine, Cr),
    Cr > 2.0.

% Severity assessment
severity(Patient, severe) :-
    diagnosis(Patient, acute_kidney_injury),
    lab_value(Patient, creatinine, Cr),
    Cr > 3.0.

severity(Patient, severe) :-
    symptom(Patient, oliguria),
    symptom(Patient, hypertension).

severity(Patient, moderate) :-
    diagnosis(Patient, _),
    \+ severity(Patient, severe).

% Treatment recommendations
treatment(Patient, dialysis) :-
    diagnosis(Patient, acute_kidney_injury),
    severity(Patient, severe).

treatment(Patient, corticosteroids) :-
    diagnosis(Patient, nephrotic_syndrome).

treatment(Patient, antibiotics) :-
    diagnosis(Patient, pyelonephritis).

treatment(Patient, ace_inhibitor) :-
    diagnosis(Patient, chronic_kidney_disease),
    symptom(Patient, hypertension).

% Risk factors
risk_factor(Patient, diabetes) :-
    age(Patient, Age),
    Age > 50,
    diagnosis(Patient, chronic_kidney_disease).

risk_factor(Patient, hypertension_related) :-
    symptom(Patient, hypertension),
    diagnosis(Patient, _).

% Query examples:
% ?- diagnosis(patient1, D).
% ?- treatment(patient1, T).
% ?- severity(patient2, S).
% ?- risk_factor(Patient, R).
