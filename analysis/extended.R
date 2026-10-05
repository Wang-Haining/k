data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- results_dir
dir.create(file.path(out, "historical"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(out, "supplementary"), recursive = TRUE, showWarnings = FALSE)
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
  did <- function(o, xx = x, spec = "year FE + IC") {
    add("historical DID", m, o, spec, boot(as.formula(paste(
      o,
      "~ intent*post + yearf + ic"
    )), xx, "intent:post"))
  }
  add("historical DID", m, "primary", "all eligibility", boot(primary ~ intent * post + yearf +
        ic, hall[hall$mechanism == m, ], "intent:post"))
  for (o in c(
    "primary", "secondary", "ktrial_direct", "informative_strict", "primary_nihdef", "primary_late",
    "nonpi_multisite", "R01eq_5y", "R01eq_or_trialgrant_5y"
  )) {
    did(o)
  }
  did("ktrial_direct", x[x$post == 1 | x$start_ge_2018 == 1, ],
    "pre-policy limited to 2018-19 legacy-FOA awards (submitted after NOT-OD-16-149)")
  did("ktrial_direct", x[x$post == 1 | x$start_ge_2017_09 == 1, ], "pre-policy limited to K start >= 2017-09-01")
  did("ktrial_direct_fdaaa", x, "drug/biologic/device trials only")
  pre <- x[x$post == 0 & x$year <= 2017, ]
  pre$fake <- as.integer(pre$year >= 2016)
  add("historical placebo DID", m, "ktrial_direct", "2016-17 vs 2014-15, pre-policy only", boot(ktrial_direct ~
        intent * fake + yearf + ic, pre, "intent:fake"))
  y18 <- x[x$year == 2018, ]
  add("historical E3 FY2018", m, "ktrial_direct", "intent awardees, new vs legacy FOA", boot(ktrial_direct ~
        post + ic, y18[y18$intent == 1, ], "post"))
  did("primary", x[x$preK_PI == 0, ], "awardees with no registered trial before K")
  for (o in c(
    "ktrial_direct", "informative_strict", "primary_nihdef", "primary_late", "nonpi_multisite",
    "R01eq_5y", "R01eq_or_trialgrant_5y"
  )) {
    add("main RD", m, o, "unadjusted", boot(as.formula(paste(o, "~ A")), y, "A"))
  }
  add("main RD", m, "primary_main", "awardees with no registered trial before K", boot(primary_main ~
        A, y[y$preK_PI == 0, ], "A"))
  add("main RD", m, "R01eq_7y", "K start 2018-2019 (7-year follow-up complete)", boot(
    R01eq_7y ~ A,
    y[y$followup_7y_complete == 1, ], "A"
  ))
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "historical/leadership_estimates.csv"), row.names = FALSE)
rep <- do.call(rbind, lapply(c("K23", "K08"), function(m) {
  do.call(rbind, lapply(c("Required", "Not Allowed"), function(g) {
    s <- d[d$mechanism == m & d$group == g & d$new_trial_due == 1, ]
    data.frame(mechanism = m, group = g, n_with_due_new_trial = nrow(s), pct_with_results_posted = if (nrow(s)) {
      round(100 * mean(s$new_trial_due_with_results), 1)
    } else {
      NA
    })
  }))
}))
write.csv(rep, file.path(out, "supplementary/new_trial_reporting.csv"), row.names = FALSE)
cat(sprintf("extended: %d estimate rows, %d reporting rows\n", nrow(est), nrow(rep)))
