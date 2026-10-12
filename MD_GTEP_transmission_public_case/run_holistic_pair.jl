using HOPE

pcm_case = normpath(joinpath(@__DIR__, "..", "MD_PCM_transmission_public_case"))
HOPE.run_hope_holistic(@__DIR__, pcm_case)
