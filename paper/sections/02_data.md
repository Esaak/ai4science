# 2. DATA (с. 3–6)

[с. 3]
2. DA T A
2.1. Physical problem statement
The reference data are generated with LES of an idealized urban canopy under neutral
thermal stratification, representative of Moscow conditions (Fig. 1). The domain is256×
256×64m, discretised on a128×128×32grid (2m per cell in the horizontal). The building
x–3

[с. 4]
Deep Learning in Computational Physics
geometry is fixed across the whole dataset: identical blocks of height16m in a regular staggered
array occupying about6%of the plan area. Vegetation is represented by trees with prescribed
leaf-area density (LAD) and leaf-area index (LAI); roads are modelled as volumetric PM2.5
emission sources of height8m. The flow is forced by a prescribed horizontal pressure gradient
that sets the wind; the wind speed is essentially constant across the dataset (varying by<0.5%),
so only the winddirectionand the emission and vegetation layout vary between simulations.
Figure 1. Physical problem: an idealized staggered-block urban canopy (256×256×64m) with fixed
16m buildings, trees (LAD/LAI), and8m road emission sources, forced by a mean wind set by a
horizontal pressure gradient.
2.2. LES model
The data were produced with the LES model developed at the Moscow State University
Research Computing Center (MSU-RCC) [9–11], which integrates the spatially filtered incom­
pressibleNavier–StokesequationsundertheBoussinesqapproximationtogetherwithatransport
equation for the passive scalar,
𝜕¯𝑢𝑖
𝜕𝑥𝑖
= 0,
𝜕¯𝑢𝑖
𝜕𝑡 + 𝜕(¯𝑢𝑖 ¯𝑢𝑗)𝜕𝑥𝑗 =− 1𝜌0 𝜕¯𝑝*𝜕𝑥𝑖− 𝜕𝜏𝑖𝑗𝜕𝑥𝑗 +𝑓 𝑐𝜖𝑖𝑗3 ¯𝑢𝑗,
𝜕¯𝑐
𝜕𝑡 + 𝜕(¯𝑢𝑗 ¯𝑐)𝜕𝑥𝑗 = 𝜕𝜕𝑥𝑗
(︂
𝐷𝑐
𝜕¯𝑐
𝜕𝑥𝑗
)︂
− 𝜕𝜏𝑐𝑗
𝜕𝑥𝑗
+𝑆 𝑐,
x–4

[с. 5]
Moscow University Physics Bulletin80(9), x (2026)
with¯𝑢𝑖 the filtered velocity,¯𝑝* the modified kinematic pressure,𝜏𝑖𝑗 and𝜏 𝑐𝑗 the subgrid stress
and scalar-flux tensors,𝑓 𝑐 the Coriolis parameter, and𝑆 𝑐 the source term. Subgrid closure
uses the Smagorinsky model [12] with a dynamic procedure [13, 14] for the coefficients, and the
buildings enter as solid blocks resolved on the grid.
2.3. Input representation and dataset
Each LES run reaches a quasi-stationary state, after which the concentration field is time-av­
eraged to give the target. The dataset comprises9layouts and2670simulations (“experiments”),
each carrying several independently released tracers, for a total of58566samples. The input
for each tracer is a7×128×128raster (Fig. 2): normalised building height; a signed-distance
function (SDF) map to buildings; the leaf-area index (LAI); the road emission power (below);
a signed-distance map to roads (source SDF); and two constant planes encoding the wind di­
rection(cos𝜑,sin𝜑). A signed-distance encoding of geometry is a standard, effective input for
convolutional flow surrogates [5]. Four normalised coordinate planes (coordinate convolution,
CoordConv [15]) are appended inside the network, and the full wind3-vector(cos𝜑,sin𝜑,|v|)is
also supplied to the wind-conditioning module (Sec. 3.2). The prediction target has five maps:
the concentration at𝑧= 3,10,16,50m (levels Z1, Z5, Z8, Z25) and the vertically averaged
concentration (“Mean”). All concentrations are transformed bylog(1 +𝐶)for training, as they
span several orders of magnitude.
The road-emission power is reconstructed from the rasterised road mask: connected segments
are split into lengthℓand width𝑤by morphological opening and assigned a strengthℓ 𝑤2 ℎ𝑠 𝑘𝑒
(ℎ𝑠 = 8m,𝑘 𝑒 = 13.06/3.5), passed to the network aslog(1 +power). Figure 3 summarises the
dataset: the mean concentration of the central level, the vegetated area fraction, thelog10 of the
peak source power (bimodal, spanning about two orders of magnitude), and the distribution of
wind directions.
The split into training and test sets is byexperiment(80/20, fixed seed): all tracers of
one simulation stay on the same side, giving46934training and11632test samples. Because
the geometry is identical everywhere, the layouts are pooled before splitting; the consequences
for generalisation are discussed in Sec. 5. Spatial augmentation (90∘ rotations and reflections,
applied consistently to the raster, the target and the wind vector) is used on the training set
only.
x–5

[с. 6]
Deep Learning in Computational Physics
Figure 2. The7-channel input raster: building height and building SDF, LAI, road emission power
(log) and road SDF, and two constant planes for the wind direction. The same wind vector is also fed
to the FiLM module.
Figure 3. Dataset distributions: mean concentration of the central level, vegetated area fraction,log10
of the peak source power (bimodal), and wind-direction rose.
