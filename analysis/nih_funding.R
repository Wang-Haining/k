data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- results_dir
dir.create(file.path(out, "funding"), recursive = TRUE, showWarnings = FALSE)
n_boot <- 1000
fit <- function(formula, x, term) {
  x <- droplevels(x)
  drop <- Filter(function(v) is.factor(x[[v]]) && nlevels(x[[v]]) < 2, all.vars(formula))
  if (length(drop)) {
    formula <- update(formula, as.formula(paste(". ~ . -", paste(drop, collapse = " - "))))
  }
  b <- tryCatch(coef(lm(formula, data = x))[term], error = function(e) stop("model fitting failed"))
  if (is.na(b)) {
    NA_real_
  } else {
    unname(b)
  }
}
boot <- function(formula, x, term) {
  est <- fit(formula, x, term)
  if (Sys.getenv("PUBLIC") == "1") return(c(est = est, n = nrow(x)))
  cl <- split(seq_len(nrow(x)), x$org_id)
  reps <- replicate(n_boot, {
    ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
    fit(formula, x[ix, ], term)
  })
  c(est = est, lo = unname(quantile(reps, 0.025, na.rm = TRUE)), hi = unname(quantile(reps, 0.975,
        na.rm = TRUE
      )), se = sd(reps, na.rm = TRUE), n = nrow(x), na = sum(is.na(reps)))
}
res <- list()
add <- function(analysis, m, outcome, spec, s, scale = 100) {
  res[[length(res) + 1]] <<- data.frame(
    analysis = analysis, mechanism = m, outcome = outcome, spec = spec,
    estimate = round(scale * s["est"], 1), lo = round(scale * s["lo"], 1), hi = round(
      scale * s["hi"],
      1
    ), se = round(scale * s["se"], 2), mde80 = round(2.8 * scale * s["se"], 1), n = s["n"],
    na_reps = s["na"], row.names = NULL
  )
}
h <- Reduce(function(a, b) merge(a, b, by = "blind_id"), list(read.csv(file.path(data_dir,
        "historical/person_analysis.csv"),
      stringsAsFactors = FALSE
    ), read.csv(file.path(data_dir, "derived/historical_extended.csv"), stringsAsFactors = FALSE)))
starts <- source("analysis/start_flags.R")$value
h <- merge(h, starts, by = "blind_id")
h$ic <- factor(h$ic)
h$yearf <- factor(h$year)
hall <- h
h <- h[h$besh_only_classifier == 0, ]
d <- read.csv(file.path(data_dir, "contemporaneous/person_analysis.csv"), stringsAsFactors = FALSE, na.strings = c(
  "",
  "NA"
))
d <- Reduce(function(a, b) merge(a, b, by = "blind_id"), list(d[, c(
  "blind_id", "mechanism", "group",
  "year", "ic", "eligible_main"
)], read.csv(file.path(data_dir, "derived/contemporaneous_extended.csv"),
  stringsAsFactors = FALSE
), read.csv(file.path(data_dir, "instrument/analysis/person_variants.csv"),
  stringsAsFactors = FALSE
)[, c("blind_id", if (Sys.getenv("PUBLIC") != "1") "org_id", "primary_main", "preK_PI", "unresolved")]))
d <- d[d$eligible_main == 1 & d$unresolved == 0, ]
d$A <- as.integer(d$group == "Required")
d$ic <- factor(d$ic)
d$yearf <- factor(d$year)
for (m in c("K23", "K08")) {
  x <- h[h$mechanism == m, ]
  y <- d[d$mechanism == m, ]
  for (o in c("ktrial_any_start", "ktrial_grant_linked", "ktrial_judged_unlinked", "R01nih_5y",
      "R01nih_or_trialgrant_5y")) {
    add("historical DID", m, o, "year FE + IC", boot(
      as.formula(paste(o, "~ intent*post + yearf + ic")),
      x, "intent:post"
    ))
  }
  for (o in c("ktrial_any_start", "R01nih_5y", "R01nih_R35_5y", "R01nih_or_trialgrant_5y")) {
    add("main RD", m, o, "unadjusted", boot(as.formula(paste(o, "~ A")), y, "A"))
  }
  add("main RD", m, "R01nih_5y", "adjusted for FY + IC", boot(R01nih_5y ~ A + yearf + ic, y, "A"))
  add("main RD", m, "R01nih_7y", "K start 2018-2019 (7-year follow-up complete)", boot(R01nih_7y ~
        A, y[y$followup_7y_complete == 1, ], "A"))
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "funding/estimates.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
