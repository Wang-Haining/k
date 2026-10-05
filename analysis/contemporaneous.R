data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- file.path(results_dir, "contemporaneous")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
d <- read.csv(file.path(data_dir, "contemporaneous/person_analysis.csv"), stringsAsFactors = FALSE, na.strings = c(
  "",
  "NA"
))
v <- read.csv(file.path(data_dir, "instrument/analysis/person_variants.csv"),
  stringsAsFactors = FALSE,
  na.strings = c("", "NA", "nan")
)
stopifnot(nrow(d) == 1527, nrow(v) == 1527, setequal(d$blind_id, v$blind_id))
d <- merge(d[, c(
  "blind_id", "mechanism", "group", "year", "ic", "eligible_main", "eligible_no_mixed",
  "research_type", "human_scope", "R01", "R34", "U01", "any_funding"
)], v, by = "blind_id")
for (o in grep("^(primary|secondary)_", names(d), value = TRUE)) d[[o]][d$unresolved == 1] <- NA
d$primary_and_R01 <- as.integer(d$primary_main == 1 & d$R01 == 1)
d$primary_without_R01 <- as.integer(d$primary_main == 1 & d$R01 == 0)
d$R01_without_primary <- as.integer(d$primary_main == 0 & d$R01 == 1)
d$A <- as.integer(d$group == "Required")
source("analysis/risk_differences.R")
estimates <- list()
est_block <- function(base, m, elig, o, label) {
  known <- base[!is.na(base[[o]]), , drop = FALSE]
  add_estimate(known, base, m, elig, o, paste0(label, "all_eligible"), "raw") # nolint: object_usage_linter.
  cs <- common(known) # nolint: object_usage_linter.
  add_estimate(cs, base, m, elig, o, paste0(label, "common_year_IC_support"), # nolint: object_usage_linter.
    "pooled_standardized") # nolint: object_usage_linter.
}
main_outcomes <- c(
  "primary_main", "secondary_main", "R01", "R34", "U01", "any_funding", "primary_and_R01",
  "primary_without_R01", "R01_without_primary"
)
sens_outcomes <- grep("^primary_(window_4y|excl_|registry|current)", names(d), value = TRUE)
for (m in c("K08", "K23")) {
  base <- d[d$mechanism == m & d$eligible_main == 1, , drop = FALSE]
  for (o in c(main_outcomes, sens_outcomes)) est_block(base, m, "eligible_main", o, "")
  nm <- d[d$mechanism == m & d$eligible_no_mixed == 1, , drop = FALSE]
  est_block(nm, m, "eligible_no_mixed", "primary_main", "")
  for (s in 0:1) {
    for (o in c("primary_main", "R01")) {
      sub <- base[base$preK_PI == s, , drop = FALSE]
      add_estimate(sub[!is.na(sub[[o]]), ], sub, m, "eligible_main", o, paste0( # nolint: object_usage_linter.
        "preK_trial_PI_",
        s
      ), "raw")
    }
  }
  ap <- base[base$human_scope == "applied", , drop = FALSE]
  for (o in c("primary_main", "R01")) {
    add_estimate( # nolint: object_usage_linter.
      ap[!is.na(ap[[o]]), ], ap, m, "eligible_main", o,
      "baseline_applied_human_scope", "raw"
    )
  }
}
est <- do.call(rbind, estimates)
pct <- function(x) round(100 * x, 1)
write.csv(est, file.path(out, "estimates.csv"), row.names = FALSE, na = "")
cum <- do.call(rbind, lapply(c("K08", "K23"), function(m) {
  do.call(rbind, lapply(c("Required", "Not Allowed"), function(g) {
    x <- d[d$mechanism == m & d$group == g & d$eligible_main == 1 & d$unresolved == 0, ]
    data.frame(mechanism = m, group = g, n = nrow(x), year = 1:5, primary = sapply(1:5, function(t) {
      if (Sys.getenv("PUBLIC") == "1") {
        pct(mean(x[[paste0("primary_by_", t, "y")]]))
      } else {
        pct(mean(!is.na(x$t_first_primary) & x$t_first_primary <= t))
      }
    }), secondary = sapply(1:5, function(t) {
      if (Sys.getenv("PUBLIC") == "1") {
        pct(mean(x[[paste0("secondary_by_", t, "y")]]))
      } else {
        pct(mean(!is.na(x$t_first_secondary) & x$t_first_secondary <= t))
      }
    }))
  }))
}))
write.csv(cum, file.path(out, "cumulative.csv"), row.names = FALSE)
cat(sprintf("contemporaneous: %d estimates, %d cumulative rows\n", nrow(est), nrow(cum)))
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
