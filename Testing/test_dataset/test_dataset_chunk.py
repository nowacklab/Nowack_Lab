import numpy as np
from importlib import reload
from IPython import get_ipython
ipython = get_ipython()

import Nowack_Lab.Utilities.dataset
reload(Nowack_Lab.Utilities.dataset)
from Nowack_Lab.Utilities.dataset import Dataset


def makedataset(chunk):
    dataset = Dataset('testset_{0:d}.hdf5'.format(int(time.time())))
    dataset.append('/foo/', np.full( (100,100,10000), np.nan), 
            chunks=chunk)
    return dataset

def appenddataset(dataset, slc, shape):
    dataset.append('/foo/', np.full(shape, np.nan), slc=slc)

def getdataset(dataset, slc):
    a = dataset.get('/foo/', slc=slc)

ipython.magic("timeit makedataset((2,2,4375))")
ipython.magic("timeit makedataset(True)")
ipython.magic("timeit makedataset(None)")
dataset = makedataset(None)
ipython.magic("timeit appenddataset(dataset, (2,3), (10000,))")
ipython.magic("timeit getdataset(dataset, (2,3))")
ipython.magic("timeit getdataset(dataset, (slice(0,100),3,1))")
dataset = makedataset(True)
ipython.magic("timeit appenddataset(dataset, (2,3), (10000,))")
ipython.magic("timeit getdataset(dataset, (2,3))")
ipython.magic("timeit getdataset(dataset, (slice(0,100),3,1))")
dataset = makedataset((1,1,100))
ipython.magic("timeit appenddataset(dataset, (2,3), (10000,))")
ipython.magic("timeit getdataset(dataset, (2,3))")
ipython.magic("timeit getdataset(dataset, (slice(0,100),3,1))")

'''
No point in chunking
Both custom and automatic chunksizes give longer read and write times

testset_1544554027.hdf5
testset_1544554037.hdf5
testset_1544554054.hdf5
testset_1544554072.hdf5
testset_1544554089.hdf5
testset_1544554106.hdf5
testset_1544554123.hdf5
testset_1544554139.hdf5
17.1 s ± 338 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
testset_1544554157.hdf5
testset_1544554170.hdf5
testset_1544554184.hdf5
testset_1544554197.hdf5
testset_1544554211.hdf5
testset_1544554224.hdf5
testset_1544554238.hdf5
testset_1544554250.hdf5
13.4 s ± 454 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
testset_1544554264.hdf5
testset_1544554276.hdf5
testset_1544554288.hdf5
testset_1544554300.hdf5
testset_1544554312.hdf5
testset_1544554324.hdf5
testset_1544554337.hdf5
testset_1544554349.hdf5
12.2 s ± 540 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)

testset_1544555070.hdf5
691 µs ± 182 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
453 µs ± 2.56 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
1.3 ms ± 13.4 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
testset_1544555094.hdf5
1.56 ms ± 154 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
751 µs ± 4.09 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
1.2 ms ± 22.7 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
testset_1544555126.hdf5
1.38 ms ± 104 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
901 µs ± 2.75 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
1.85 ms ± 8.05 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
'''
