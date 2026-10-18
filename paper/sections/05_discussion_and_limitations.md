# 5. DISCUSSION AND LIMITATIONS (с. 13–13)

[с. 13]
5. DISCUSSION AND LIMIT A TIONS
Three limitations shape the interpretation. First, the objective is the main weakness: it is
a log-space error, whereas the quantities of interest (mass, bias) are physical. The features the
model handles worst — peak magnitude and physical mass, and the very quantities in which the
ablation variants differ — are exactly those the log loss does not constrain. Rebuilding the loss
on a physical concentration normalisation (a mass-consistent term, or training partly in physical
space) is the natural next step. Second, the geometry and wind speed are fixed: generalisation
to unseen building morphologies or wind speeds is out of scope, and the marginal role of the
wind conditioning is a property ofthisregime, not a general statement about FiLM. Because
the layouts share a common geometry, the test set does not probe geometric generalisation;
the meaningful axis here would be held-out source and vegetation configurations, which are the
dominant predictors. Third, the emission-power channel is reconstructed from a raster and is
fragile for non-axis-aligned roads.
Finally, we note the practical finding that a plume-weighted loss and𝑅2 anti-correlate late
in training, so checkpoint selection must be stated explicitly.
