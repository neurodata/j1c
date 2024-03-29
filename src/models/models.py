import numpy as np
import pandas as pd
from graspy.embed import MultipleASE
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier

from rerf.rerfClassifier import rerfClassifier


def run_mase(X, y, train_idx, test_idx):
    # Data wrangle
    XTRAIN = X[train_idx]
    XTEST = X[test_idx]
    YTRAIN = y[train_idx]
    YTEST = y[test_idx]

    train_samples = XTRAIN.shape[0]
    test_samples = XTEST.shape[0]
    n_samples = train_samples + test_samples

    X = np.vstack([XTRAIN, XTEST])

    mase = MultipleASE(n_components=None, scaled=True)
    mase.fit(X)

    rhats = mase.scores_.reshape(n_samples, -1)

    knn = KNeighborsClassifier(n_neighbors=1, metric="euclidean")
    knn.fit(rhats[:train_samples], YTRAIN)

    preds = knn.predict(rhats[train_samples:])
    error = np.mean(preds != YTEST)

    return np.mean(error)


def train_random_forest(
    X,
    y,
    train_idx,
    test_idx,
    projection_matrices=[
        "RerF", 
        "S-RerF", 
        "Graph-Node-RerF", 
        "Graph-Edge-RerF"
        ],
    n_trees=1000,
    sporf_mtry=None,
    morf_mtry=None,
    patch_min=None,
    patch_max=None,
    random_state=None,
    return_prob=False
):

    XTRAIN = X[train_idx]
    XTEST = X[test_idx]
    YTRAIN = y[train_idx]
    YTEST = y[test_idx]

    # params inferred from data
    img_height = X.shape[1]

    # vectorize so that inputs work
    XTRAIN = XTRAIN.reshape(XTRAIN.shape[0], -1)
    XTEST = XTEST.reshape(XTEST.shape[0], -1)

    errors = []
    for projection_matrix in projection_matrices:
        if projection_matrix == "RerF":
            mtry = sporf_mtry
        else:
            mtry = morf_mtry

        cls = rerfClassifier(
            projection_matrix=projection_matrix,
            max_features=mtry,
            n_jobs=-1,
            n_estimators=n_trees,
            oob_score=False,
            random_state=random_state,
            image_height=img_height,
            image_width=img_height,
            patch_height_max=patch_max,
            patch_height_min=patch_min,
            patch_width_max=patch_max,
            patch_width_min=patch_min,
        )
        cls.fit(XTRAIN, YTRAIN)
        
        if not return_prob:
            preds = cls.predict(XTEST)
            errors.append(np.mean(preds != YTEST))
        else:
            preds = cls.predict_proba(XTEST)
            errors.append(preds)

    return errors


def run_classification(X, y, folds=5, seed=None, **kwargs):
    kfolds = StratifiedKFold(n_splits=folds, random_state=seed)

    errors = []
    for train_idx, test_idx in kfolds.split(X, y):
        error = train_random_forest(X, y, train_idx, test_idx, **kwargs)
        mase_error = run_mase(X, y, train_idx, test_idx)
        errors.append(error + [mase_error])

    cols = ["RerF", "S-RerF", "Graph-Node-RerF", "Graph-Edge-RerF", "MASE o 1NN"]
    df = pd.DataFrame(errors, columns=cols)

    return df


def run_tree_sweep(X, y, folds=5, seed=None, **kwargs):
    kfolds = StratifiedKFold(n_splits=folds, random_state=seed)

    errors = []
    for train_idx, test_idx in kfolds.split(X, y):
        error = train_random_forest(X, y, train_idx, test_idx, return_prob=True, **kwargs)
        errors.append(error)

    return errors

