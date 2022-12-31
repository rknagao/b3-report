import numpy as np
import pandas as pd


def calculate_accrued_yield(array_value, array_yield):
    assert len(array_value) == len(array_yield)

    list_new_value = []
    list_new_value.append(array_value[0])

    for i in range(1, len(array_value)):
        last_value = list_new_value[i - 1] * (1 + array_yield[i]/100)
        new_value = round(last_value + array_value[i], 2)
        list_new_value.append(new_value)
    
    return np.array(list_new_value)
