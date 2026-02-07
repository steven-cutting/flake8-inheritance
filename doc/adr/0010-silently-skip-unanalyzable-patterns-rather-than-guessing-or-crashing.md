# 10: Silently skip unanalyzable patterns rather than guessing or crashing

Date: 2026-02-07
Status: Accepted

## Context

The plugin performs static analysis using only the `ast` module, which means certain Python patterns are inherently unanalyzable: dynamic base classes computed at runtime (e.g., `class Foo(get_base()):`), names imported via star imports (e.g., `from myproject import *`), and dotted attribute bases referencing names not in the import map (e.g., `class Foo(unknown.Bar):`). The plugin has three options for each unanalyzable pattern: (1) crash or raise an exception, (2) guess and risk a false positive, (3) silently skip and produce no diagnostic. Option 1 is unacceptable — a linting plugin must never cause flake8 to crash regardless of input. Option 2 violates the project's hard requirement of zero false positives on external or third-party base classes. Option 3 accepts the possibility of false negatives (missed violations) in exchange for reliability and trust.

## Decision

When the plugin encounters a base class it cannot classify — a non-`Name`/`Attribute` AST node (dynamic base), a name not present in the import map (star import or undeclared), or any other unanalyzable pattern — it will silently skip that base class with no error, no warning, and no crash. The plugin's design philosophy is: silence is preferable to a wrong answer.

## Consequences

The plugin will miss some inheritance violations in codebases that rely heavily on dynamic base classes or star imports. These are documented edge cases, not bugs. Users who need coverage of these patterns must use complementary tools (e.g., Pylint with astroid, or runtime checks). The error handling paths are tested with dedicated edge case tests to confirm no crashes and no false positives. The plugin can be safely run against any syntactically valid Python file, including adversarial inputs, without affecting flake8's exit code.
