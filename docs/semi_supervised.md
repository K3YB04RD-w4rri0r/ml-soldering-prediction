# Semi-Supervised Learning

With one row per `input_group`, the train set has 175 labelled rows and 321 unlabelled rows with complete inputs, see [1D_direct_classification.ipynb](../modeling/1D_direct_classification/1D_direct_classification.ipynb). Each target also lacks a value on 46% to 58% of the rows of `train.csv`, see the README. The unlabelled rows are not like the labelled ones: a random forest tells them apart from their inputs with an AUC of 0.946, and 220 of the 321 were never tested for Charpy, see [2_1_kmeans.ipynb](../modeling/2_semi_supervised/2_1_kmeans.ipynb).

## Assumptions

A semi-supervised method helps only if its assumption holds on the data. Unlabelled data can also make a model worse. The four assumptions come from Chapelle et al. 2006.

| Assumption | Meaning | Holds on this data | Source |
|---|---|---|---|
| Smoothness | Close inputs have close outputs. | Only at very short distance. The nearest row has the same label in 81% of the cases, the fifth nearest in 58%. | [1D2_knn.ipynb](../modeling/1D_direct_classification/1D2_knn.ipynb) |
| Cluster | Points of the same cluster have the same label. | In part. The K-means clusters are purer in label than with shuffled labels, 0.74 against 0.62 for k = 40, but far from pure, and 22 of the 40 clusters hold no labelled row. | [2_1_kmeans.ipynb](../modeling/2_semi_supervised/2_1_kmeans.ipynb) |
| Low density | The class boundary passes through a region with few points. | Unlikely. The linear SVM kept 45% of the rows as support vectors, so the classes overlap. | [1D3_svm.ipynb](../modeling/1D_direct_classification/1D3_svm.ipynb) |
| Manifold | The inputs lie on a space of lower dimension. | Weak. The PCA needed 12 of the 30 components for 80% of the variance. | [4_eda_pca.ipynb](../preprocessing/4_eda_pca.ipynb) |

## Methods

The methods come from two surveys: van Engelen and Hoos 2020 for classification, Kostopoulos et al. 2018 for regression.

| Method | Principle | Reference |
|---|---|---|
| Self-training | The model labels the unlabelled points it is most confident about, adds them to the training set and retrains. | Yarowsky 1995, Triguero et al. 2015, Amini et al. 2025 |
| Self-training for multi-target regression | Self-training with tree ensembles. The variance of the predictions of the trees gives the confidence. | Levatić et al. 2017 |
| Tri-training | Three models train on bootstrap samples. A point gets a label when two models agree on it. | Zhou and Li 2005b |
| Co-training | Two models train on two independent views of the inputs and label points for each other. | Blum and Mitchell 1998 |
| COREG | Co-training for regression with two k-NN regressors. | Zhou and Li 2005a |
| Cluster-then-label | Cluster all the points, then give each cluster the majority label of its labelled points. | Zhu and Goldberg 2009 |
| Mixture models and EM | A mixture of distributions models the inputs, one component per class. EM estimates it on all the points. | Nigam et al. 2000 |
| Label propagation and label spreading | A graph links close points. The labels spread along its edges. | Zhu and Ghahramani 2002, Zhou et al. 2004 |
| Transductive SVM | The SVM moves its boundary away from the unlabelled points. | Joachims 1999 |
| Semi-supervised random forests | The forest also maximises a margin on the unlabelled points. The out-of-bag error stops the training if the unlabelled points do not help. | Leistner et al. 2009 |
| Targets as inputs | A measured target is an input of the model of another target. | Spyromitros-Xioufis et al. 2016 |

## Evaluation

- **Baseline:** A semi-supervised method must beat the same model trained on the labelled data only, with the same folds and the same tuning budget. Oliver et al. 2018 found that studies often report a weak supervised baseline.
- **Gain:** Unlabelled data helps only for some data distributions, so a gain of zero is a possible result. Singh et al. 2008 give the conditions.

## References

- Amini, M.-R., Feofanov, V., Pauletto, L., Hadjadj, L., Devijver, E., Maximov, Y., 2025. Self-training: A survey. *Neurocomputing*, 616, 128904.
- Blum, A., Mitchell, T., 1998. Combining labeled and unlabeled data with co-training. *COLT 1998*, 92–100.
- Chapelle, O., Schölkopf, B., Zien, A., 2006. *Semi-Supervised Learning*. MIT Press.
- Joachims, T., 1999. Transductive inference for text classification using support vector machines. *ICML 1999*, 200–209.
- Kostopoulos, G., Karlos, S., Kotsiantis, S., Ragos, O., 2018. Semi-supervised regression: A recent review. *Journal of Intelligent & Fuzzy Systems*, 35, 1483–1500.
- Leistner, C., Saffari, A., Santner, J., Bischof, H., 2009. Semi-supervised random forests. *ICCV 2009*.
- Levatić, J., Ceci, M., Kocev, D., Džeroski, S., 2017. Self-training for multi-target regression with tree ensembles. *Knowledge-Based Systems*, 123, 41–60.
- Nigam, K., McCallum, A., Thrun, S., Mitchell, T., 2000. Text classification from labeled and unlabeled documents using EM. *Machine Learning*, 39, 103–134.
- Oliver, A., Odena, A., Raffel, C., Cubuk, E. D., Goodfellow, I., 2018. Realistic evaluation of deep semi-supervised learning algorithms. *NeurIPS 2018*.
- Singh, A., Nowak, R., Zhu, X., 2008. Unlabeled data: Now it helps, now it doesn't. *NeurIPS 2008*.
- Spyromitros-Xioufis, E., Tsoumakas, G., Groves, W., Vlahavas, I., 2016. Multi-target regression via input space expansion: treating targets as inputs. *Machine Learning*, 104, 55–98.
- Triguero, I., García, S., Herrera, F., 2015. Self-labeled techniques for semi-supervised learning: taxonomy, software and empirical study. *Knowledge and Information Systems*, 42, 245–284.
- van Engelen, J. E., Hoos, H. H., 2020. A survey on semi-supervised learning. *Machine Learning*, 109, 373–440.
- Yarowsky, D., 1995. Unsupervised word sense disambiguation rivaling supervised methods. *ACL 1995*, 189–196.
- Zhou, D., Bousquet, O., Lal, T. N., Weston, J., Schölkopf, B., 2004. Learning with local and global consistency. *NeurIPS 2003*, 321–328.
- Zhou, Z.-H., Li, M., 2005a. Semi-supervised regression with co-training. *IJCAI 2005*, 908–916.
- Zhou, Z.-H., Li, M., 2005b. Tri-training: exploiting unlabeled data using three classifiers. *IEEE Transactions on Knowledge and Data Engineering*, 17, 1529–1541.
- Zhu, X., Ghahramani, Z., 2002. Learning from labeled and unlabeled data with label propagation. Technical report CMU-CALD-02-107, Carnegie Mellon University.
- Zhu, X., Goldberg, A. B., 2009. *Introduction to Semi-Supervised Learning*. Morgan & Claypool.
