import Lake
open Lake DSL

package blancMath

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.25.0"

lean_lib BlancMath where
  roots := #[`BlancMath]
