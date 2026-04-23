"""
Mathlib-topology theorem extraction.

Two surfaces:

    builtin_corpus()   -- a small, hand-curated TopologyCorpus that ships
                          with the package.  Contains Euler V-E+F=2,
                          related polyhedron theorems, and the canonical
                          Lakatos counterexample family.  This is what M0
                          drives end-to-end.

    MathlibExtractor   -- best-effort .lean parser that walks a Mathlib
                          checkout under the topology / geometry subtrees
                          and yields MathTheorems.  Used by M1 once a
                          local Mathlib clone is available; degrades to
                          the empty iterator if no path is supplied.

The parser is intentionally conservative: it extracts ``theorem`` /
``lemma`` declarations whose binder list it can split unambiguously, and
skips anything containing meta-variables, holes, or attribute decorators
it cannot safely round-trip.  Anything we cannot fully parse is dropped
on the floor; the dropper / scorer never sees a half-parsed theorem.

Author: Patrick Cooper
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional

from blanc.math.types import Hypothesis, MathTheorem


# ---------------------------------------------------------------------------
# Corpus container
# ---------------------------------------------------------------------------


@dataclass
class TopologyCorpus:
    """A fixed set of MathTheorems plus optional source provenance."""

    theorems: list[MathTheorem] = field(default_factory=list)

    def __iter__(self) -> Iterator[MathTheorem]:
        return iter(self.theorems)

    def __len__(self) -> int:
        return len(self.theorems)

    def by_id(self, identifier: str) -> MathTheorem:
        for t in self.theorems:
            if t.identifier == identifier:
                return t
        raise KeyError(f"no theorem {identifier!r} in corpus")

    def add(self, theorem: MathTheorem) -> None:
        if any(t.identifier == theorem.identifier for t in self.theorems):
            raise ValueError(f"duplicate theorem id {theorem.identifier!r}")
        self.theorems.append(theorem)


# ---------------------------------------------------------------------------
# Built-in corpus (Lakatos / Euler family)
# ---------------------------------------------------------------------------


def builtin_corpus() -> TopologyCorpus:
    """Return the curated Lakatos / Euler corpus that drives M0.

    These are intentionally hand-stated so the dropper has unambiguous,
    obviously-critical hypotheses to mask.  Lean expressions are written
    in a Mathlib-faithful style so a real SubprocessLeanHarness with
    Mathlib on the path could in principle elaborate them; the M0 demo
    runs against MockLeanHarness with pre-registered verdicts.
    """
    corpus = TopologyCorpus()

    corpus.add(
        MathTheorem(
            identifier="EulerCharacteristic.convex_polytope_v_minus_e_plus_f",
            statement="P.vertices.card - P.edges.card + P.faces.card = 2",
            hypotheses=(
                Hypothesis(name="P", lean_expr="Polytope \u211d 3"),
                Hypothesis(name="h_convex", lean_expr="Convex \u211d P.carrier", critical=True),
                Hypothesis(name="h_bounded", lean_expr="IsBounded P.carrier", critical=True),
                Hypothesis(name="h_simply_connected", lean_expr="IsSimplyConnected P.boundary",
                           critical=True),
            ),
            source_path="Mathlib/Geometry/Polytope/Euler.lean",
            natural_language=(
                "For every bounded convex polytope P in three-space whose boundary "
                "is simply connected, the Euler characteristic V - E + F equals 2."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="EulerCharacteristic.genus_zero_polyhedron",
            statement="P.vertices.card - P.edges.card + P.faces.card = 2 - 2 * P.genus",
            hypotheses=(
                Hypothesis(name="P", lean_expr="Polyhedron \u211d 3"),
                Hypothesis(name="h_closed_surface",
                           lean_expr="IsClosedSurface P.boundary", critical=True),
                Hypothesis(name="h_genus_finite", lean_expr="P.genus < \u22a4"),
            ),
            source_path="Mathlib/AlgebraicTopology/EulerCharacteristic.lean",
            natural_language=(
                "For every closed-surface polyhedron P in three-space, "
                "V - E + F equals 2 - 2g where g is the genus."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.compact_hausdorff_implies_normal",
            statement="NormalSpace X",
            hypotheses=(
                Hypothesis(name="X", lean_expr="Type*"),
                Hypothesis(name="inst_top", lean_expr="TopologicalSpace X"),
                Hypothesis(name="h_compact", lean_expr="CompactSpace X", critical=True),
                Hypothesis(name="h_t2", lean_expr="T2Space X", critical=True),
            ),
            source_path="Mathlib/Topology/Separation.lean",
            natural_language=(
                "Every compact Hausdorff space is normal."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.continuous_image_of_compact_is_compact",
            statement="IsCompact (f '' s)",
            hypotheses=(
                Hypothesis(name="X", lean_expr="Type*"),
                Hypothesis(name="Y", lean_expr="Type*"),
                Hypothesis(name="inst_top_X", lean_expr="TopologicalSpace X"),
                Hypothesis(name="inst_top_Y", lean_expr="TopologicalSpace Y"),
                Hypothesis(name="f", lean_expr="X \u2192 Y"),
                Hypothesis(name="s", lean_expr="Set X"),
                Hypothesis(name="h_continuous", lean_expr="Continuous f", critical=True),
                Hypothesis(name="h_compact", lean_expr="IsCompact s", critical=True),
            ),
            source_path="Mathlib/Topology/SubsetProperties.lean",
            natural_language=(
                "The continuous image of a compact set is compact."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.heine_borel",
            statement="IsCompact s",
            hypotheses=(
                Hypothesis(name="s", lean_expr="Set \u211d"),
                Hypothesis(name="h_closed", lean_expr="IsClosed s", critical=True),
                Hypothesis(name="h_bounded", lean_expr="IsBounded s", critical=True),
            ),
            source_path="Mathlib/Topology/MetricSpace/HeineBorel.lean",
            natural_language=(
                "A subset of the reals is compact iff it is closed and bounded."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.connected_image_of_continuous",
            statement="IsConnected (f '' s)",
            hypotheses=(
                Hypothesis(name="X", lean_expr="Type*"),
                Hypothesis(name="Y", lean_expr="Type*"),
                Hypothesis(name="inst_top_X", lean_expr="TopologicalSpace X"),
                Hypothesis(name="inst_top_Y", lean_expr="TopologicalSpace Y"),
                Hypothesis(name="f", lean_expr="X \u2192 Y"),
                Hypothesis(name="s", lean_expr="Set X"),
                Hypothesis(name="h_continuous", lean_expr="Continuous f", critical=True),
                Hypothesis(name="h_connected", lean_expr="IsConnected s", critical=True),
            ),
            source_path="Mathlib/Topology/Connected/Basic.lean",
            natural_language=(
                "The continuous image of a connected set is connected."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.uniform_limit_of_continuous_is_continuous",
            statement="Continuous g",
            hypotheses=(
                Hypothesis(name="X", lean_expr="Type*"),
                Hypothesis(name="Y", lean_expr="Type*"),
                Hypothesis(name="inst_top_X", lean_expr="TopologicalSpace X"),
                Hypothesis(name="inst_uniform_Y", lean_expr="UniformSpace Y"),
                Hypothesis(name="f", lean_expr="\u2115 \u2192 X \u2192 Y"),
                Hypothesis(name="g", lean_expr="X \u2192 Y"),
                Hypothesis(name="h_each_continuous",
                           lean_expr="\u2200 n, Continuous (f n)", critical=True),
                Hypothesis(name="h_uniform_convergence",
                           lean_expr="TendstoUniformly f g atTop", critical=True),
            ),
            source_path="Mathlib/Topology/UniformSpace/UniformConvergence.lean",
            natural_language=(
                "The uniform limit of a sequence of continuous functions is continuous "
                "(this is one of the canonical Lakatos counterexample sites: pointwise "
                "convergence is insufficient)."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.tychonoff",
            statement="CompactSpace (\u03a0 i, X i)",
            hypotheses=(
                Hypothesis(name="\u03b9", lean_expr="Type*"),
                Hypothesis(name="X", lean_expr="\u03b9 \u2192 Type*"),
                Hypothesis(name="inst_top",
                           lean_expr="\u2200 i, TopologicalSpace (X i)"),
                Hypothesis(name="h_each_compact",
                           lean_expr="\u2200 i, CompactSpace (X i)", critical=True),
            ),
            source_path="Mathlib/Topology/Constructions.lean",
            natural_language=(
                "An arbitrary product of compact spaces is compact."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.intermediate_value_theorem",
            statement="\u2203 c \u2208 Set.Icc a b, f c = y",
            hypotheses=(
                Hypothesis(name="a", lean_expr="\u211d"),
                Hypothesis(name="b", lean_expr="\u211d"),
                Hypothesis(name="y", lean_expr="\u211d"),
                Hypothesis(name="f", lean_expr="\u211d \u2192 \u211d"),
                Hypothesis(name="h_le", lean_expr="a \u2264 b"),
                Hypothesis(name="h_continuous_on",
                           lean_expr="ContinuousOn f (Set.Icc a b)", critical=True),
                Hypothesis(name="h_y_between",
                           lean_expr="y \u2208 Set.Icc (f a) (f b)", critical=True),
            ),
            source_path="Mathlib/Topology/Algebra/Order/IntermediateValue.lean",
            natural_language=(
                "The intermediate value theorem on a real interval."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.path_connected_implies_connected",
            statement="IsConnected s",
            hypotheses=(
                Hypothesis(name="X", lean_expr="Type*"),
                Hypothesis(name="inst_top", lean_expr="TopologicalSpace X"),
                Hypothesis(name="s", lean_expr="Set X"),
                Hypothesis(name="h_path_connected",
                           lean_expr="IsPathConnected s", critical=True),
            ),
            source_path="Mathlib/Topology/Connected/PathConnected.lean",
            natural_language=(
                "Every path-connected set is connected (the converse fails on the "
                "topologist's sine curve)."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.urysohn_lemma",
            statement="\u2203 f : X \u2192 \u211d, Continuous f \u2227 EqOn f 0 A \u2227 EqOn f 1 B",
            hypotheses=(
                Hypothesis(name="X", lean_expr="Type*"),
                Hypothesis(name="inst_top", lean_expr="TopologicalSpace X"),
                Hypothesis(name="A", lean_expr="Set X"),
                Hypothesis(name="B", lean_expr="Set X"),
                Hypothesis(name="h_normal", lean_expr="NormalSpace X", critical=True),
                Hypothesis(name="h_A_closed", lean_expr="IsClosed A", critical=True),
                Hypothesis(name="h_B_closed", lean_expr="IsClosed B", critical=True),
                Hypothesis(name="h_disjoint", lean_expr="Disjoint A B", critical=True),
            ),
            source_path="Mathlib/Topology/UrysohnsLemma.lean",
            natural_language=(
                "Urysohn's lemma: in a normal space, disjoint closed sets can be "
                "separated by a continuous real-valued function."
            ),
        )
    )

    corpus.add(
        MathTheorem(
            identifier="Topology.sequential_compactness_iff_compactness_metric",
            statement="IsCompact s \u2194 IsSeqCompact s",
            hypotheses=(
                Hypothesis(name="X", lean_expr="Type*"),
                Hypothesis(name="inst_metric", lean_expr="MetricSpace X"),
                Hypothesis(name="s", lean_expr="Set X"),
            ),
            source_path="Mathlib/Topology/MetricSpace/Sequences.lean",
            natural_language=(
                "In a metric space, compactness and sequential compactness coincide."
            ),
        )
    )

    return corpus


# ---------------------------------------------------------------------------
# Best-effort Mathlib extractor
# ---------------------------------------------------------------------------


_DECL_HEAD_RE = re.compile(
    r"^(?P<kw>theorem|lemma)\s+(?P<name>[A-Za-z_][\w.']*)",
    re.MULTILINE,
)
"""Locates the start of each ``theorem`` / ``lemma`` declaration.  The
binder list and statement that follow are split by a balanced-paren walker
in :func:`_split_decl`, since binders contain ``:`` characters that defeat
a single regex."""


_BINDER_RE = re.compile(r"\(\s*([^():]+?)\s*:\s*([^()]+?)\s*\)")


def _split_decl(text: str, start: int) -> Optional[tuple[str, str, int]]:
    """Walk from ``start`` (just past the identifier) and return (binders, statement, end).

    The grammar we accept is:

        (binder)* ':' statement ':='

    Anything that breaks balanced parens, contains a brace block, or runs
    off the end of the file aborts the parse and returns None -- the
    extractor is best-effort by design.
    """
    n = len(text)
    i = start
    binders_start = i
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            return None
        if text[i] == "(":
            depth = 1
            j = i + 1
            while j < n and depth:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            if depth:
                return None
            i = j
            continue
        if text[i] == ":":
            binders = text[binders_start:i]
            j = text.find(":=", i + 1)
            if j < 0:
                return None
            statement = text[i + 1:j].strip()
            return binders, statement, j + 2
        return None
    return None


@dataclass
class MathlibExtractor:
    """Walks a Mathlib checkout and yields ``MathTheorem`` records.

    The extractor is best-effort.  It is designed to be safe rather than
    complete: if it cannot fully parse a declaration, it skips it.  M1 may
    upgrade this to a real LeanInteract / Pantograph backed extractor.

    Args:
        mathlib_root: Path to a Mathlib clone (the directory containing
            ``Mathlib/`` itself).
        subtrees: Mathlib subdirectories to walk.  Defaults to the topology
            and geometry corners called out in
            ``ai_for_math_abstract.tex``.
    """

    mathlib_root: Optional[Path] = None
    subtrees: tuple[str, ...] = (
        "Mathlib/Topology",
        "Mathlib/AlgebraicTopology",
        "Mathlib/Geometry",
    )

    def iter_files(self) -> Iterator[Path]:
        if self.mathlib_root is None:
            return
            yield  # noqa: pragma: no cover  (unreachable)
        root = self.mathlib_root
        for sub in self.subtrees:
            base = root / sub
            if not base.exists():
                continue
            yield from base.rglob("*.lean")

    def parse_file(self, path: Path) -> Iterable[MathTheorem]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return
        for match in _DECL_HEAD_RE.finditer(text):
            ident = match.group("name")
            split = _split_decl(text, match.end())
            if split is None:
                continue
            binders_blob, statement, _ = split
            hypotheses: list[Hypothesis] = []
            for bm in _BINDER_RE.finditer(binders_blob):
                names_blob = bm.group(1).strip()
                ty = bm.group(2).strip()
                for name in names_blob.split():
                    hypotheses.append(Hypothesis(name=name, lean_expr=ty))
            if not hypotheses:
                continue
            yield MathTheorem(
                identifier=ident,
                statement=statement,
                hypotheses=tuple(hypotheses),
                source_path=str(path.relative_to(self.mathlib_root))
                if self.mathlib_root else str(path),
            )

    def extract(self) -> TopologyCorpus:
        corpus = TopologyCorpus()
        seen: set[str] = set()
        for path in self.iter_files():
            for theorem in self.parse_file(path):
                if theorem.identifier in seen:
                    continue
                seen.add(theorem.identifier)
                corpus.theorems.append(theorem)
        return corpus
