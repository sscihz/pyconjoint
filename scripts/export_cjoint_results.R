library(cjoint)
library(jsonlite)

levels <- fromJSON('data/immigrationconjoint_levels.json')
immigrationconjoint <- read.csv('data/immigrationconjoint.csv',
                                stringsAsFactors = FALSE,
                                check.names = FALSE)
for (col_name in names(levels)) {
  immigrationconjoint[[col_name]] <- factor(immigrationconjoint[[col_name]],
                                            levels = levels[[col_name]])
}

set.seed(42)
immigrationconjoint$weights <- runif(nrow(immigrationconjoint))
write.csv(data.frame(weights = immigrationconjoint$weights),
          'data/immigrationconjoint_weights.csv',
          row.names = FALSE)

formula_main <- Chosen_Immigrant ~ Gender + Education + `Country of Origin` + `Language Skills`
formula_interact <- Chosen_Immigrant ~ Gender + Education + Gender:Education

mod_cluster <- amce(formula_main,
                    data = immigrationconjoint,
                    cluster = TRUE,
                    respondent.id = 'CaseID',
                    design = 'uniform')

mod_nocluster <- amce(formula_main,
                      data = immigrationconjoint,
                      cluster = FALSE,
                      respondent.id = NULL,
                      design = 'uniform')

mod_interact <- amce(formula_interact,
                     data = immigrationconjoint,
                     cluster = FALSE,
                     respondent.id = NULL,
                     design = 'uniform')

mod_weights <- amce(formula_main,
                    data = immigrationconjoint,
                    cluster = TRUE,
                    respondent.id = 'CaseID',
                    design = 'uniform',
                    weights = 'weights')

extract_amce <- function(model) {
  sm <- summary(model)
  amce_tbl <- sm$amce
  data.frame(term = paste(amce_tbl$Attribute, amce_tbl$Level, sep = ':'),
             estimate = amce_tbl$Estimate,
             std_error = amce_tbl$`Std. Err`,
             row.names = NULL,
             check.names = FALSE)
}

extract_acie <- function(model) {
  sm <- summary(model)
  if (is.null(sm$acie)) {
    return(data.frame())
  }
  acie_tbl <- sm$acie
  data.frame(term = paste(acie_tbl$Attribute, acie_tbl$Level, sep = ':'),
             estimate = acie_tbl$Estimate,
             std_error = acie_tbl$`Std. Err`,
             row.names = NULL,
             check.names = FALSE)
}

output <- list(
  formula_main = deparse(formula_main),
  formula_interact = deparse(formula_interact),
  cluster = extract_amce(mod_cluster),
  no_cluster = extract_amce(mod_nocluster),
  interaction_amce = extract_amce(mod_interact),
  interaction_acie = extract_acie(mod_interact),
  weights = extract_amce(mod_weights)
)

writeLines(toJSON(output, dataframe = 'rows', auto_unbox = TRUE, pretty = TRUE),
           'data/cjoint_expected_results.json')
