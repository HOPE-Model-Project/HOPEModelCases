# Maryland transmission case tools

These scripts build reproducible ModelCases. They are not part of the runtime
GTEP-to-PCM transfer implementation.

## Canonical entry points

- `run_build_md_transmission_case.py`: build the public-data Maryland physical
  transmission reconstruction.
- `run_finalize_md_transmission_case.py`: finalize and validate the physical PCM
  case inputs.
- `build_md_rps20_holistic_pair.py`: build the compact 168-hour 20% RPS
  GTEP-to-PCM benchmark.
- `build_md_rps20_full8760_holistic_pair.py`: build and validate the canonical
  8760-hour GTEP plus 8760-hour PCM source pair, or materialize an isolated
  monthly PCM integration-test workspace.

## Supporting builders

- `fetch_md_public_network.py` and `build_md_transmission_case.py` acquire and
  transform the public network sources.
- `finalize_md_transmission_case.py` performs final schema and provenance work.
- `build_md_gtep_4zone_twin.py` and `build_md_gtep_nodal_twin.py` construct the
  planning representations paired with the physical network.
- `generate_md_public_network_visualization.py` regenerates the documented
  network visualization.

Runtime transfer belongs to the HOPE package in `src/holistic_linkage.jl`,
`src/holistic_contract.jl`, and `src/run_holistic.jl`. Solved workspaces and
outputs belong under the ignored `artifacts/` or case `output*/` directories;
they should not be copied into source input folders.
