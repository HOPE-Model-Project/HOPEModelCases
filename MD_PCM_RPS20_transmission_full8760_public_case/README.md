# Maryland 20% RPS full-year OSM PCM benchmark

This is the 8760-hour operational stage paired with `MD_GTEP_RPS20_4zone_full8760_public_case`. It
retains 656 buses and 838 branches from the documented OSM-derived Maryland
transmission reconstruction and uses nodal angle-based DCOPF, unit commitment,
four operating-reserve products, storage chronology, and a local 20% Maryland
RPS.

The annual nodal load multipliers are derived deterministically from the annual
four-zone profiles and each bus's `Zone_id`. Maryland is not electrically
isolated: `EXT` boundary buses and branches remain in the network. Net
interchange has a zero schedule because no authoritative hourly schedule is
assumed, while hourly nodal interchange caps allow endogenous imports and
exports within the documented boundary-interface limits.

Generator-specific annual outage traces are not available with compatible
stable identities. The case therefore uses generator-level `AF` and `FOR`
parameters rather than repeating one July week across the year.

The exact post-GTEP physical tables used by PCM are written under
`output_holistic/realized_inputs/`; source `Data/` files remain unchanged.
This is a research workflow benchmark, not an official PJM planning case.

The four-zone planning model cannot represent every intra-zonal constraint. A
July deliverability screen found one PEPCO 69 kV branch at its inferred 500 MW
limit during the only load-shedding hour. The benchmark therefore calibrates
`OSM_L1528639488` to 600 MW in both directions. This is explicitly recorded as
a modeled assumption in `references/physical_deliverability_adjustments.csv`.

## Validation status

The source case remains a complete 8760-hour input. Full-year GTEP solved to
`OPTIMAL`; the strict GTEP-to-PCM handoff and the detailed PCM constraints were
validated on a 744-hour July slice, which solved to `OPTIMAL` with zero load
shedding, zero RPS slack, and every configured acceptance check passing.

The monolithic 8760-hour PCM construction exceeded the 32 GB workstation's
memory (about 27.6 GB private memory at failure). No hours or network elements
were removed from this published case to conceal that limit. See
`references/VALIDATION.md` for commands, metrics, and interpretation.

The validation folder also contains
`references/july_linkage_validation_summary.csv`, a compact machine-readable
summary derived from the solved annual GTEP and July PCM outputs.
