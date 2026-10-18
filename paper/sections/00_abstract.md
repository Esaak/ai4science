# 0. ABSTRACT (с. 1–2)

[с. 1]
Moscow University Physics Bulletin80(9), x (2026)
Machine Learning for Environmental Sciences
Stationary pollutant concentration fields in urban layer: deep
learning approximation of large-eddy simulation
I. A. Gerasimov,1,* M. A. Krinitskiy,1, 2, 3, 4, 5 E. V. Mortikov,3, 4 and A. V. Debolskiy3, 5
1Moscow Institute of Physics and Technology (National
Research University), Dolgoprudny, 141701 Russia
2Shirshov Institute of Oceanology, Russian Academy of Sciences, Moscow, 117997 Russia
3Research Computing Center, Lomonosov Moscow State University, Moscow, 119991 Russia
4Moscow Center for Fundamental and Applied Mathematics, Moscow, Russia
5Obukhov Institute of Atmospheric Physics, Russian
Academy of Sciences, Moscow, 119017 Russia
(Received xx.xx.2026; Revised xx.xx.2026; Accepted xx.xx.2026)
x–1

[с. 2]
Deep Learning in Computational Physics
Abstract
Reliable, spatially resolved prediction of pollutant concentration in an urban canopy is expensive
with Large Eddy Simulation (LES) and out of reach for Gaussian models that ignore the geometry.
We train a convolutional surrogate neural model that maps a raster description of an idealized, regular
staggered-block, urban canopy described in building geometry, leaf-area index, road emission sources,
and wind — onto the steady-state PM2.5 field at four heights and its vertical mean, using data from
the MSU-RCC LES model. On the test set the surrogate reaches𝑅 2 = 0.86withF AC2 = 0.75,
NMSE = 0.44and low bias (FB = 0.07,mass_ratio = 0.93), satisfying the Chang–Hanna acceptance
criteria. We demonstrate that the predicted field is governed primarily by the emission sources and
the vegetation. Also, we demonstrate that the feature-wise Linear Modulation (FiLM) on the wind
vector, intended to improve the fit, gives no measurable benefit in a controlled ablation study and
slightly worsens the mass-balance metric. By contrast, data augmentation is shown to be essential.
We also demonstrate the computational efficiency: the surrogate model runs in about3.5ms per city
configuration.
PACS numbers: 92.60.Sz, 07.05.Mh, 47.27.ep
Keywords: urban dispersion, PM 2.5, large eddy simulation, surrogate model, U-Net, feature attribution, air
quality model evaluation
