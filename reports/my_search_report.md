---
type: Отчёт
---
# Поиск по своей библиотеке: neural network surrogate for LES of PM2.5 dispersion in an urban street canyon

[источник] Библиотека проекта: `library/corpus.jsonl`, 37 работ, происхождение — OpenAlex REST API, дата обращения 2026-10-18 (`library/corpus_provenance.json`). Индексируются название и аннотация, словарь 2056 слов, в документе в среднем 155 слов. BM25 k1=1.2, b=0.75; векторный поиск — intfloat/multilingual-e5-small. Расчёт 2026-10-20, ноутбук `search_lab_pm25.ipynb`, раздел 14.

## metrics for evaluating dispersion model predictions FAC2 NMSE

| место | BM25 | вектор |
|---|---|---|
| 1 | Application of DNM And Hec-Ras Model For Pollutant Dispers (W4403196103, 4.78) | Evaluation of three pollutant dispersion models for the en (W2996962897, 0.862) |
| 2 | Evaluation of three pollutant dispersion models for the en (W2996962897, 4.22) | Application of DNM And Hec-Ras Model For Pollutant Dispers (W4403196103, 0.860) |
| 3 | Uncertainty-aware surrogate modeling for urban air polluta (W4404452021, 3.63) | Application of a Machine Learning Method for Prediction of (W4318474508, 0.857) |

[написано] Вероятно, BM25 взял статьи по совпадению слов: dispersion и model, а вектор — более подходящие по смыслу.

## convolutional neural network predicting flow field around buildings

| место | BM25 | вектор |
|---|---|---|
| 1 | Surrogate modelling of unsteady wind pressure on tall buil (W7125780903, 11.35) | A Convolutional Neural Network for Steady-State Flow Appro (W4386884969, 0.900) |
| 2 | Fast Prediction of Flow Field around Airfoils Based on Dee (W4310235246, 11.14) | Convolutional Neural Networks for Steady Flow Approximatio (W2515505748, 0.900) |
| 3 | A point-cloud deep learning framework for prediction of fl (W3093190107, 10.93) | A scalable convolutional neural network approach to fluid  (W4403136121, 0.894) |

[написано] Здесь выдачи более разные: BM25 ошибся сильно больше, вытащил суррогаты давления.

## can a trained network replace an expensive turbulence simulation

| место | BM25 | вектор |
|---|---|---|
| 1 | Deep learning to replace, improve, or aid CFD analysis in  (W3200982616, 7.61) | Deep learning to replace, improve, or aid CFD analysis in  (W3200982616, 0.856) |
| 2 | Convolutional Neural Networks for Steady Flow Approximatio (W2515505748, 4.88) | Surrogate convolutional neural network models for steady c (W3164867305, 0.853) |
| 3 | Surrogate modelling of unsteady wind pressure on tall buil (W7125780903, 4.62) | Application of DNM And Hec-Ras Model For Pollutant Dispers (W4403196103, 0.847) |

[написано] Обе взяли одну статью — вероятно потому, что она совпадает и по смыслу, и по словам.

## влияние растительности на концентрацию PM2.5 в уличном каньоне

| место | BM25 | вектор |
|---|---|---|
| 1 | Investigating the effect of trees on urban quality in Dubl (W3037481038, 5.47) | Influence of obstacles on urban canyon ventilation and air (W4390446491, 0.819) |
| 2 | — (BM25 не нашёл ни одного слова запроса) | Turbulent transfer and concentration statistics in a stree (W4220706766, 0.816) |
| 3 | — (BM25 не нашёл ни одного слова запроса) | High resolution wind-tunnel investigation about the effect (W4308203280, 0.813) |

[написано] Влияние растительности: русский текст совсем не поддерживается поиском.

## does the model work on building geometries it has not seen

| место | BM25 | вектор |
|---|---|---|
| 1 | Large-Eddy Simulation of Airflow and Pollutant Dispersion  (W4283691980, 8.16) | Large-Eddy Simulation of Airflow and Pollutant Dispersion  (W4283691980, 0.836) |
| 2 | Turbulent transfer and concentration statistics in a stree (W4220706766, 5.83) | Qualitative and Quantitative Investigation of Multiple Lar (W2906903649, 0.832) |
| 3 | Fourier Neural Operator for Parametric Partial Differentia (W3092923133, 4.72) | Surrogate modelling of unsteady wind pressure on tall buil (W7125780903, 0.832) |

[написано] Выделяется одна работа, но, кажется, в ней нет распространения на незнакомую геометрию.
