# TODO: Datadog dashboard demo of the edge pipeline's energy (Talk 2)

**Status:** planned, not built (added 2026-10-04). Lower priority than the slides: the talk is 2026-10-08, and the deck comes first.

The plan: `docs/TALK2-DATADOG-DASHBOARD-PLAN.md`. Per-decision energy, completion, thermal state and invocation rate on one Datadog dashboard, live on the MacBook with toggles (thinking on, gate off) or replayed from the study's runs. It makes the paper's §VI (Table VI) visible.

**Blocked on the user's decisions:** Datadog site, an API key (and an application key for API-created dashboards; environment variables only, never in the repo), Agent vs HTTP API, live vs replay, LLM Observability spans or metrics only.

**Constraint:** don't build or run it on the MacBook while benchmarks are running.
