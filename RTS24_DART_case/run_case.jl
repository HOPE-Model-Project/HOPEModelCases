using Pkg
Pkg.activate(normpath(joinpath(@__DIR__, "..", "..")))

using HOPE

mode = isempty(ARGS) ? "run" : lowercase(ARGS[1])
if mode == "validate"
    result = validate_hope(@__DIR__)
    println(result["inventory"])
    println(result["constraint_coverage"])
    println("RTS24 DART validation passed.")
elseif mode == "run"
    result = run_hope(@__DIR__)
    println("RTS24 DART run passed all acceptance checks.")
    println("Outputs: $(result["output_path"])")
else
    error("Mode must be validate or run.")
end
