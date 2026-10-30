# EcoIQ Native Computing Strategy — Rust + C++ (candidate v1)

## Proprietary software is about IP, not a mandatory language

EcoIQ already owns its authored Python/Django and TypeScript product code
subject to applicable code contributions and dependency licences.
Rust/C++ do **not** make IP automatically proprietary, and the availability
of language compilers or third-party libraries does not imply ownership of
their code or models. Validate licence terms and a contributor/IP policy
before distributing a commercial desktop, mobile or native package.

Architecture: **one EcoIQ OS**, not three competing decision engines.

| Layer | Language | Responsibility |
|---|---|---|
| Business OS / projects / access / audit / Mizan / Islah | Python/Django | Authoritative, tenant-aware decisions and source provenance |
| Web / desktop / mobile interfaces | TypeScript + existing clients | User experience, 3D view presentation and interaction |
| Optional batch numerical acceleration | Rust | Low-level memory-safe numeric kernels, bulk stream validation |
| Optional geometry and simulation | C++20 | Spatial math and deterministic digital-twin primitives |
| AI / ML experiments | Python + existing AI Gateway, sklearn/PyTorch | Governed models with evidence and human review |

## What PR includes

1. `native/rust_resource_kernel` (Rust standard library only):
   a **candidate** reported loss-rate calculator with strict nonnegative,
   finite, unit and period boundaries. Unknown != 0. Returns explicit flags
   `independently_verified=false` and
   `implementation_permitted=false`. The authoritative calculation is
   still in `ecoiq_os/process_diagnostic.py`.
2. `native/cpp_twin_geometry` (C++20/CMake, no external dependencies):
   deterministic point transformation, bounding boxes and volumes in metres
   for the existing `digital_twin` module. Nonfinite, negative scales,
   reversed bounds and overflow fail closed. It does **not** claim real
   physics, mesh processing, fluid simulation, mining simulation, AR engine
   or safety certification.
3. Offline parity tests between Rust and the canonical Python process
   diagnostic with finite synthetic quantities; separate C++ CTest and Rust
   unit tests plus GitHub CI.

These are **isolated experiments**. No Python bindings, FFI, shared library
loading, database migration, new API endpoint, network, business write, model
training, production build, Render config, AR device integration or live
industrial telemetry is introduced. Rust uses f64 demonstration arithmetic,
**never for financial accounting** — use Decimal/approved fixed-point
numeric contracts where money is involved.

## Build and test locally

```bash
cargo test --manifest-path native/rust_resource_kernel/Cargo.toml --offline
cargo build --manifest-path native/rust_resource_kernel/Cargo.toml --offline

cmake -S native/cpp_twin_geometry -B /tmp/ecoiq-twin-cmake -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/ecoiq-twin-cmake --parallel 2
ctest --test-dir /tmp/ecoiq-twin-cmake --output-on-failure

python -m unittest scripts.native.test_rust_python_parity -v
```

Requirements: Rust toolchain and C++20 compiler/CMake in development/CI,
not installed into the runtime Django web service. Run only synthetic
fixtures. CI keeps native modules outside the standard Python build.

## Non-negotiable gates before calling Rust/C++ from Django

1. Verify a real measured performance bottleneck using a benchmark with
   identical inputs, hardware, and correctness criteria. If Python/NumPy
   already meets target latency/cost, leave it alone.
2. Define a versioned, typed and bounded FFI contract (e.g., PyO3/maturin
   for Rust, or pybind11 for C++), including error codes, units,
   missingness and input limits.
3. Run parity/property/fuzz tests across Python/native, compiler sanitizers,
   buffer boundaries and repeated loads. No native module may bypass
   tenant-level RBAC or supply evidence-authentication claims.
4. Profile cold-start, wheel size and memory to fit Render constraints.
   Build binary wheels in CI for supported Linux/macOS/Windows targets
   and architecture, with ABI/version pinning and dependency license audit.
5. Keep a tested pure Python fallback, typed errors, telemetry and
   feature flag. Rollback must not require a production database migration.
6. Do not connect the geometry kernel to real digital-twin/AR assets without
   coordinate reference system, asset scope, physical unit provenance,
   engineering calibration, and specialist validation.
7. The 33×114 KPI–surah review inventory and 99-name catalogue are **not**
   ML labels or moral scores. Rust/C++ are irrelevant to determining
   theological truth and cannot certify Islamic compliance.

## Commercial priority

For the first paid UK construction pilots, prioritise accurate evidence,
customer onboarding, data contracts and annual recurring revenue.
Native optimisation is useful after we can demonstrate a measurable
runtime or offline simulation advantage. **Neither Rust nor C++ is needed
to prove that EcoIQ owns its authored software.**
