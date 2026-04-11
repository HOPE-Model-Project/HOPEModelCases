# Export Germany Census 2022 population grid to the HOPE fallback spatial-load format.
#
# Usage in R:
#   install.packages(c("terra", "sf"))
#   install.packages("z22", repos = c("https://jslth.r-universe.dev", "https://cloud.r-project.org"))
#   source("tools/germany_pcm_case_related/raw_sources/public_spatial_load/export_population_grid_z22.R")
#
# Output:
#   tools/germany_pcm_case_related/raw_sources/public_spatial_load/population_grid_1km.csv

library(z22)
library(terra)

out_path <- file.path(
  "tools", "germany_pcm_case_related", "raw_sources", "public_spatial_load", "population_grid_1km.csv"
)

grid_pop <- z22_data("population", res = "1km", as = "raster")
df <- as.data.frame(grid_pop, xy = TRUE, na.rm = TRUE)

value_col <- setdiff(names(df), c("x", "y"))[1]
if (is.na(value_col) || value_col == "") {
  stop("Could not identify the population value column from z22 output")
}

out <- data.frame(
  Longitude = df$x,
  Latitude = df$y,
  Population = df[[value_col]]
)
out <- out[is.finite(out$Population) & out$Population > 0, ]

write.csv(out, out_path, row.names = FALSE)
message(sprintf("Wrote %s with %s populated grid rows", out_path, nrow(out)))
