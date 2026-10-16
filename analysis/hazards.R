data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- results_dir
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
boot <- function(formula, x, term, id = "org_id") {
  est <- fit(formula, x, term)
  cl <- split(seq_len(nrow(x)), x[[id]])
  reps <- replicate(n_boot, {
    ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
    fit(formula, x[ix, ], term)
  })
  c(est = est, lo = unname(quantile(reps, 0.025, na.rm = TRUE)), hi = unname(quantile(reps, 0.975,
        na.rm = TRUE
      )), n = nrow(x), na = sum(is.na(reps)))
}
res <- list()
add <- function(analysis, m, outcome, spec, s) {
  res[[length(res) + 1]] <<- data.frame(
    analysis = analysis, mechanism = m, outcome = outcome, spec = spec,
    estimate = round(100 * s["est"], 1), lo = round(100 * s["lo"], 1), hi = round(
      100 * s["hi"],
      1
    ), n = s["n"], na_reps = s["na"], row.names = NULL
  )
}
h <- merge(read.csv(file.path(data_dir, "historical/person_analysis.csv"), stringsAsFactors = FALSE),
  read.csv(file.path(data_dir, "derived/historical_characteristics.csv"), stringsAsFactors = FALSE),
  by = "blind_id"
)
h$ic <- factor(h$ic)
h$yearf <- factor(h$year)
h <- merge(h, read.csv(file.path(data_dir, "derived/historical_extended.csv"))[, c("blind_id", "besh_only_classifier")],
  by = "blind_id"
)
h <- h[h$besh_only_classifier == 0, ]
d <- read.csv(file.path(data_dir, "contemporaneous/person_analysis.csv"), stringsAsFactors = FALSE, na.strings = c(
  "",
  "NA"
))
d <- merge(d[, c("blind_id", "mechanism", "group", "year", "ic", "eligible_main")], read.csv(file.path(
  data_dir,
  "derived/contemporaneous_characteristics.csv"
), stringsAsFactors = FALSE), by = "blind_id")
d <- merge(d, read.csv(file.path(data_dir, "instrument/analysis/person_variants.csv"), stringsAsFactors = FALSE)[
  ,
  c("blind_id", "org_id", "primary_main", "secondary_main", "preK_PI", "unresolved")
], by = "blind_id")
d <- d[d$eligible_main == 1 & d$unresolved == 0, ]
d$A <- as.integer(d$group == "Required")
d$ic <- factor(d$ic)
d$yearf <- factor(d$year)
for (m in c("K23", "K08")) {
  x <- h[h$mechanism == m, ]
  y <- d[d$mechanism == m, ]
  add("historical DID", m, "primary", "adjusted for pre-K trial PI", boot(primary ~ intent * post +
        preK_PI + yearf + ic, x, "intent:post"))
  add("historical DID", m, "primary", "pre-K trial PI x post also", boot(primary ~ intent * post +
        preK_PI * post + yearf + ic, x, "intent:post"))
  add("main RD", m, "primary_main", "adjusted for pre-K trial PI + FY + IC", boot(primary_main ~ A +
        preK_PI + yearf + ic, y, "A"))
  add("main RD", m, "primary_main", "unadjusted (reference)", boot(primary_main ~ A, y, "A"))
  for (o in c(
    "secondary", "informative_new_trial", "multisite_new_trial", "completed_with_results",
    "nih_funded_new_trial", "industry_new_trial", "R01eq", "R01eq_contact_PI"
  )) {
    add("historical DID", m, o, "year FE + IC", boot(
      as.formula(paste(o, "~ intent*post + yearf + ic")),
      x, "intent:post"
    ))
    if (o != "secondary") {
      add("main RD", m, o, "unadjusted", boot(as.formula(paste(o, "~ A")), y, "A"))
    }
  }
}
py <- read.csv(file.path(data_dir, "derived/historical_person_years.csv"))
py <- merge(py, h[, c("blind_id", "mechanism", "intent", "post", "ic", "org_id", "year")], by = "blind_id")
py$kf <- factor(py$k)
py$calf <- factor(py$cal_year)
py$ic <- factor(py$ic)
for (m in c("K23", "K08")) {
  z <- py[py$mechanism == m, ]
  add(
    "historical hazard DID (per person-year)", m, "first new trial", "years-since-K FE + calendar FE + IC",
    boot(event ~ intent * post + kf + calf + ic, z, "intent:post")
  )
  add("historical hazard DID (per person-year)", m, "first new trial", "+ calendar x intent FE", boot(event ~
        intent * post + kf + calf * intent + ic, z, "intent:post"))
  add(
    "historical hazard DID (per person-year)", m, "first new trial", "+ calendar x intent + years-since-K x intent FE",
    boot(event ~ intent * post + kf * intent + calf * intent + ic, z, "intent:post")
  )
  zc <- z[!(z$cal_year %in% c(2020, 2021)), ]
  add(
    "historical hazard DID (per person-year)", m, "first new trial", "excluding 2020-2021 person-years",
    boot(event ~ intent * post + kf + calf + ic, zc, "intent:post")
  )
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "supplementary/hazard_estimates.csv"), row.names = FALSE)
hz <- aggregate(event ~ cal_year + intent + post, data = py[py$mechanism == "K23", ], FUN = function(v) {
  round(100 *
      mean(v), 2)
})
hz$n <- aggregate(event ~ cal_year + intent + post, data = py[py$mechanism == "K23", ], FUN = length)$event
write.csv(hz, file.path(out, "supplementary/k23_hazards_by_calendar.csv"), row.names = FALSE)
desc <- do.call(rbind, lapply(c("K23", "K08"), function(m) {
  y <- d[d$mechanism == m, ]
  do.call(rbind, lapply(c("Required", "Not Allowed"), function(g) {
    s <- y[y$group == g, ]
    ev <- s[s$primary_main == 1, ]
    data.frame(mechanism = m, group = g, n = nrow(s), pct_k_trial_registered_as_PI = round(100 *
          mean(s$k_trial_registered_as_PI), 1), n_new_trial_PIs = nrow(ev),
      pct_new_trial_PIs_with_NIH_funded_trial = round(100 *
          mean(ev$nih_funded_new_trial), 1), pct_new_trial_PIs_with_industry_trial = round(
        100 * mean(ev$industry_new_trial),
        1
      ), pct_informative = round(100 * mean(s$informative_new_trial), 1), pct_R01eq = round(100 *
          mean(s$R01eq), 1))
  }))
}))
write.csv(desc, file.path(out, "supplementary/hazard_descriptives.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
