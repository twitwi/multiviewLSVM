import numpy as np
import time
from statistics import mean, stdev

from sklearn.metrics import accuracy_score
from sklearn.metrics.pairwise import rbf_kernel

from src.missing_views import set_random_views_to_value, laplacian_reconstruction
from src.svms import *
from src.utils import dict_to_csv, load_flower17, get_args, get_view_dict, twod_array, splits_generator, load_uwave, multiview_kernels

CV = 3

ratios_missing = [0.05*i for i in range(1, 11)]
c_range = [10**i for i in range(-3, 4)]

# ratios_missing = [0]
# c_range = [1]

X, Y, test_X, test_Y = load_uwave()

ITER = 10
PATH = "results/view/uwave/missing/svms/laplacian"

print("learning on uwave with SVMs, missing views completed by Laplacian completion")

acc_list = []
std_list = []
train_time_list = []
test_time_list = []

for r in ratios_missing:
    print(r, "\n")
    mean_accuracies = []

    for i in range(ITER):

        accuracies = []
        train_times = []
        test_times = []

        # erase some views from training 
        x, mask = set_random_views_to_value(X, r, r_type="none")
        test_x, test_mask = set_random_views_to_value(test_X, r, r_type="none")

        # kernelize and reconstruct views
        k_x, mask, mask2 = laplacian_reconstruction(x, rbf_kernel, test_x)

        y, test_y = Y[mask], test_Y[mask2]
        # cross-validation
        for train_inds, val_inds, _ in splits_generator(y, CV, None):

            train_y = y[train_inds]
            val_y = y[val_inds]

            k_train_x = get_view_dict(k_x[np.ix_(train_inds,train_inds)])
            k_val_x = get_view_dict(k_x[np.ix_(val_inds,train_inds)])

            t1 = time.time()

            # tuning     
            tuning_acc = {}.fromkeys(c_range, 0.)
            for c in c_range:
                model = train(k_train_x, train_y, c)
                pred = predict(k_val_x, val_y, model)

                tuning_acc[c] = accuracy_score(pred, val_y)

            best_C = max(tuning_acc, key=tuning_acc.get)

            t2 = time.time()
            print("tuning time:", t2-t1)

            # training
            train_val_inds = np.hstack((train_inds,val_inds))
            k_train_val_x = get_view_dict(k_x[np.ix_(train_val_inds,train_val_inds)])
            model = train(k_train_val_x, y[train_val_inds], best_C)

            t3 = time.time()
            print("training time:", t3-t2)

            test_inds = np.arange(len(test_y))+len(y)
            k_test_x = get_view_dict(k_x[np.ix_(test_inds,train_val_inds)])

            pred = predict(k_test_x, test_y, model)

            t4 = time.time()
            print("testing time:", t4-t3)

            acc = accuracy_score(pred, test_y)*100
            print(acc)
            accuracies.append(acc)
            train_times.append(t3-t2)
            test_times.append(t4-t3)

        mean_accuracies.append(mean(accuracies))
        print(mean(accuracies))

    acc_list.append(mean(mean_accuracies))
    std_list.append(stdev(mean_accuracies))
    train_time_list.append(mean(train_times))
    test_time_list.append(mean(test_times))

dict_to_csv({'accuracy':acc_list,'error':std_list,'train_time':train_time_list,'test_time':test_time_list,'ratios':ratios_missing},["nb_iter={},cv={}".format(ITER,3)],PATH+".csv")
