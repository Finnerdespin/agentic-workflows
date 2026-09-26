# TODOs

1. Medium before external storage support: the provider boundary is incomplete

**Locations:** `WorkflowService.__init__`, `src/ww/storage.py:267`, `src/ww/service.py:529`, `src/ww/extensions/registry.py:334`, `src/ww/storage_adapters/base.py:120–147` and `:309`.

| Boundary | Current state | Work needed before advertising interchangeable external providers |
|---|---|---|
| Task aggregates/artifacts/metadata | Typed injectable storage adapter, filesystem and memory implementations, shared tests | publish a versioned contract and reusable conformance suite |
| Project metadata | Separate injectable port and merge lock | Define lock/consistency requirements for shared remote providers |
| Bootstrap identity requests | Direct `.ww/bootstrap` files and filesystem locks | Introduce a bootstrap storage/coordination port or explicitly declare bootstrap local-only |
| Extension durable state | Registry constructs concrete filesystem `ExtensionStore` | Inject a small store factory/port if extension state must move with an external backend |
| Provider installation/selection | Task storage adapter passed by Python construction; CLI always constructs default `Storage` | Add explicit factory/configuration selection when external CLI providers are in scope |
| External extensions | `ww.extensions` entry points, API version, lazy loading, typed results, recovery checker, installed-package test | Publish author guide, supported API surface, compatibility/update policy, and sample package |

Do not generalize all filesystem access: local configuration, Git workspaces, and local executable paths are legitimate. The missing pieces are authoritative workflow state and coordination that must follow the chosen backend.

The default task/project lock methods are no-ops. Task locking is documented as mandatory for shared storage adapters, but this is easy for an author to miss; `read_task_record` also defaults to separate data/revision reads. Moreover, the coordinator fetches a fresh revision when committing, so CAS does not substitute for the whole-operation lock. Specify these requirements prominently or make capabilities explicit/required. A database provider must not assume implementing CAS alone makes concurrent service calls safe.

**Acceptance:** an independently packaged provider can be selected without editing core; identical tests exercise bootstrap, ordinary execution, metadata, artifacts, reset, handoff, and children. For any explicitly local-only feature, fail clearly rather than silently splitting state across backends. Test two service instances against shared storage.

2. Medium: duplicated invariants and incomplete type coverage increase drift risk

Concrete duplication exists in `_validate_aggregate` in filesystem and memory storage adapters; dotted metadata validation/serialization in `TaskMetadata` and `ProjectMetadata`; artifact path construction in both storage adapters; and the reset-body logic of normal repeat and continue.

`service.py` is now 2,453 lines, `plan.py` 1,239, `config.py` 1,179, and `instructions.py` 1,014. Size alone is not a defect. The practical issue is that init completion, assignment boundaries, loops, and cross-task publication interact in the service without one obvious invariant boundary. The configured type check also excludes important changed modules such as service, CLI, config, and filesystem persistence. A broader check found actual annotation/narrowing problems in addition to missing stubs.

**Fix brief:** extract storage-independent aggregate validation, metadata leaf rules, and a logical artifact-address helper. Keep representation details in each backend. Expand type checking module by module, declare PyYAML stubs in development dependencies, and narrow command-specific CLI arguments explicitly. Only extract service components around cohesive responsibilities with concrete callers; do not perform a cosmetic class split.

**Acceptance:** both backends pass independent malformed-record and behavior tests; standard lint/type commands cover the changed modules; remove broad suppressions only as touched. Add format checking if consistent formatting is an intended release rule. Formatting alone is low priority.
