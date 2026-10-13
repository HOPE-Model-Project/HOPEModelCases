using HOPE

const GTEP_CASE = @__DIR__
const PCM_CASE = normpath(joinpath(@__DIR__, "..", "MD_PCM_restricted_linkage_case"))

result = HOPE.run_hope_holistic(GTEP_CASE, PCM_CASE)
report = HOPE.write_holistic_coverage_report(
    result,
    joinpath(PCM_CASE, "Settings", "HOPE_holistic_acceptance.yml");
    require_all = true,
)
println("Holistic coverage passed: ", report["all_passed"])
