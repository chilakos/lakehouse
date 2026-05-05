# 09 — Failure modes to design against

Three patterns sink hub self-service if not actively prevented. The
framework must take a hard line on each.

## 9.1 The escape-hatch becomes the highway

**Pattern:** A DMO hits a case `product.yml` does not handle. They
write a custom dbt model. The custom model spreads. The framework
becomes optional. Six months later, half the products have bespoke
patterns that do not pass through the standard governance hooks.

**Mitigation:**

1. Keep `product.yml` deliberately expressive. Review every escape
   request and fold genuine patterns back into the schema.
2. Custom dbt models are allowed only in `framework/`, not in
   `products/`, and require platform-team CODEOWNERS approval.
3. Publish a quarterly "top 5 escape requests" list and address them
   in framework releases.

If the schema is the contract, escape hatches outside the contract
must be rare and deliberate.

## 9.2 The "I just updated this row" temptation

**Pattern:** A DMO sees a wrong number in Gold. They run an `UPDATE`
statement. Now Gold is no longer derivable from Bronze. The whole
rerun and rehydration story is broken — silently, until the next
rehydrate request comes in and produces different numbers.

**Mitigation:**

1. DMO Snowflake roles have `INSERT` and `SELECT`, but no `UPDATE` or
   `DELETE` on Bronze, Silver, or Gold. Enforced by RBAC, not by
   policy.
2. Data fixes are PRs that change the SQL, not the data.
3. Emergency override is a Hub Steward + Enterprise Data dual approval
   that creates an audit record.
4. Snowflake Time Travel makes "undo" cheap, so the temptation is
   reduced.

The fix-the-SQL discipline is the single most important behavioural
shift this design depends on. It must be reinforced relentlessly in
DMO onboarding.

## 9.3 Test-skipping under deadline pressure

**Pattern:** CI lets through a product with the bare minimum tests.
Six months later it is a Gold product with one `not_null` and no
uniqueness, feeding a regulatory dashboard. The first time someone
asks "how do you know this number is right" there is no answer.

**Mitigation:**

1. The minimum-test bar is enforced by CI and cannot be waived without
   an Enterprise Data exception ticket.
2. The catalog displays a "test coverage" score on every product.
3. The hub scorecard reviewed monthly with Vinh includes coverage
   trends per DMO.

Minimum bar (proposed):

- Every Silver model: at least one `not_null` test on a key column,
  one freshness check
- Every Gold model: at least one uniqueness test on the declared
  primary key, one `not_null` on every column flagged non-null in the
  schema, one referential test if it joins to a conformed dimension

Below this bar, CI refuses to promote. Period.

## What all three have in common

Each failure mode is a slow erosion. None of them produce an outage on
day one. They produce a hub that *looks* healthy for six months and
then suddenly is not — at which point the cost of rolling back is
much higher than the cost of preventing it.

The framework must be opinionated, and the platform team must enforce
the opinion. Self-service is not the same as un-governed. Done well,
self-service is *more* governed than the spaghetti it replaces,
because the governance is in the framework instead of in the heads of
five overworked engineers.
