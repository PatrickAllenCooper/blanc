# blanc 🕵🏻‍♂️

LLMs struggle with regression to the best explanation. We wish to provide an efficient way to evaluate abductive reasoning. Our innovation is to use deductive proofs to create defeasible sets which can be used to grade our resulting generation for some generative model.

While modus tollens and modus ponens are able to generate certain determinations via -deduction- and as such do not require any appeal to grounding or uncertainty reasoning about the world itself is considerabley more nuanced.

The Novelty: We reframe grounding as a question of defeasible logic, thereby making it a question of reasoning from uncertainty.

Aside: Defeasible non-monotonic logics are related to causal inference.

The System: Create a set of statements K for which a deduction is arrived at via a prolog interpreter called E. Create a deliberate subset k_i for an incomplete rendition or subset of K for which a known defeasible logic can be dedduced which is likewise arrived at by a prolog interpreter.  We use some subset of statements k_i as input for a foundation model where ordered pairs (d_i, e_i) is the label or target. Note, e is the label of the defeasible inference method utilized.

The Algorithm: We require a principled method for exracting incomplete renditions of knowledgebases which can be described in terms of defeasible logic. I will call this system the "Author."

Tooling:
We elect to use PyLog instead of Prolog directly (https://wiki.python.org/moin/PyLog) since it provides a prolog interface allowing us to keep this whole academic project within a single language (never a bad thing).

References:
"Defeasible Logic" - Nute, 94'

"A Skeptical Non-monotonic Reasoning System" - Nute, 87'

"A Logic for Legal Reasoning" - Nute, 97'

Java Framework - SPINdle

Prolog Encodings

Answer Set Programming - Clingo or DLV

LOGicalThought: Logic-Based Ontological Grounding of LLMs for High-Assurance Reasoning

LOGicalThought (LogT)

DARK (Deductive and Abductive Reasoning in Knowledge graphs)

Rational Closure (KLM Framework)

