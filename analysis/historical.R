data_dir <- Sys.getenv("DATA_DIR")
stopifnot(nzchar(data_dir), dir.exists(data_dir))
results_dir <- Sys.getenv("RESULTS_DIR")
stopifnot(nzchar(results_dir))
seed <- as.integer(Sys.getenv("ANALYSIS_SEED"))
stopifnot(length(seed) == 1, !is.na(seed))
set.seed(seed)
out <- file.path(results_dir, "historical")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
d <- read.csv(file.path(data_dir, "historical/person_analysis.csv"), stringsAsFactors = FALSE)
d <- merge(d, read.csv(file.path(data_dir, "derived/historical_extended.csv"))[, c("blind_id", "besh_only_classifier")],
  by = "blind_id"
)
d <- d[d$besh_only_classifier == 0, ]
d$ic <- factor(d$ic)
d$yearf <- factor(d$year)
d$year_c <- d$year - 2018
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
boot_ci <- function(formula, x, term) {
  est <- fit(formula, x, term)
  if (Sys.getenv("PUBLIC") == "1") return(c(est = est, n = nrow(x)))
  cl <- split(seq_len(nrow(x)), x$org_id)
  reps <- replicate(n_boot, {
    ix <- unlist(cl[sample(length(cl), replace = TRUE)], use.names = FALSE)
    fit(formula, x[ix, ], term)
  })
  c(est = est, lo = unname(quantile(reps, 0.025, na.rm = TRUE)), hi = unname(quantile(reps, 0.975,
        na.rm = TRUE
      )), n = nrow(x), na_reps = sum(is.na(reps)))
}
res <- list()
add <- function(m, est, outcome, sample, spec) {
  res[[length(res) + 1]] <<- data.frame(
    mechanism = m, estimand = est, outcome = outcome, sample = sample,
    estimate = round(100 * spec["est"], 1), lo = round(100 * spec["lo"], 1), hi = round(
      100 * spec["hi"],
      1
    ), n = spec["n"], na_reps = spec["na_reps"], row.names = NULL
  )
}
for (m in c("K23", "K08")) {
  x <- d[d$mechanism == m, ]
  add(m, "E0 intent share post-pre", "intent", "all", boot_ci(intent ~ post + ic, x, "post"))
  for (o in c("primary", "R01")) {
    add(m, "E1 portfolio level change (trend + IC)", o, "all", boot_ci(
      as.formula(paste(o, "~ post + year_c + ic")),
      x, "post"
    ))
    add(m, "E2 DID intent x post (year FE + IC)", o, "all", boot_ci(
      as.formula(paste(o, "~ intent*post + yearf + ic")),
      x, "intent:post"
    ))
  }
  y18 <- x[x$year == 2018, ]
  add(m, "E3 FY2018 intent awardees post vs pre FOA", "primary", "K start 2018, intent=1", boot_ci(primary ~
        post + ic, y18[y18$intent == 1, ], "post"))
  add(m, "E3 FY2018 DID intent x post", "primary", "K start 2018", boot_ci(primary ~ intent * post +
        ic, y18, "intent:post"))
  add(m, "E2 DID", "primary_fdaaa", "FDAAA-like trials only", boot_ci(primary_fdaaa ~ intent * post +
        yearf + ic, x, "intent:post"))
  add(m, "E2 DID", "primary_4y", "4-year window", boot_ci(
    primary_4y ~ intent * post + yearf + ic,
    x, "intent:post"
  ))
  add(m, "E2 DID", "primary", "excluding NCI", boot_ci(primary ~ intent * post + yearf + ic, x[x$ic !=
          "NCI", ], "intent:post"))
  shared <- intersect(unique(as.character(x$ic[x$post == 1])), unique(as.character(x$ic[x$post == 0])))
  add(m, "E2 DID", "primary", "ICs present in both periods", boot_ci(primary ~ intent * post + yearf +
        ic, x[x$ic %in% shared, ], "intent:post"))
  pre <- x[x$post == 0 & x$year <= 2017, ]
  pre$fake <- as.integer(pre$year >= 2016)
  add(
    m, "Placebo DID intent x (2016-17 vs 2014-15), pre only", "primary", "pre-policy 2014-2017",
    boot_ci(primary ~ intent * fake + yearf + ic, pre, "intent:fake")
  )
  add(m, "Placebo level change 2016, pre only", "primary", "pre-policy 2014-2017", boot_ci(primary ~
        fake + year_c + ic, pre, "fake"))
}
est <- do.call(rbind, res)
write.csv(est, file.path(out, "estimates.csv"), row.names = FALSE)
cat(sprintf("aggregate estimates: %d rows\n", nrow(est)))
