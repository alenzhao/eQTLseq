"""Implements run()."""

import sys as _sys

import numpy as _nmp
import multiprocessing as _mlp

from eQTLseq.ModelBinomGibbs import ModelBinomGibbs as _ModelBinomGibbs
from eQTLseq.ModelNBinomGibbs import ModelNBinomGibbs as _ModelNBinomGibbs
from eQTLseq.ModelNBinom2Gibbs import ModelNBinom2Gibbs as _ModelNBinom2Gibbs
from eQTLseq.ModelNBinom3Gibbs import ModelNBinom3Gibbs as _ModelNBinom3Gibbs
from eQTLseq.ModelNBinom4Gibbs import ModelNBinom4Gibbs as _ModelNBinom4Gibbs
from eQTLseq.ModelNormalGibbs import ModelNormalGibbs as _ModelNormalGibbs
from eQTLseq.ModelPoissonGibbs import ModelPoissonGibbs as _ModelPoissonGibbs


def run(Z, G, mdl='Normal', scale=True, n_iters=1000, n_burnin=None, beta_thr=1e-6, s2_lims=(1e-20, 1e3),
        n_threads=1, progress=True, **extra):
    """Run an estimation algorithm for a specified number of iterations."""
    Z = Z.T
    n_threads = _mlp.cpu_count() if n_threads is None else n_threads
    n_burnin = round(n_iters * 0.5) if n_burnin is None else n_burnin
    assert mdl in ('Normal', 'Poisson', 'Binomial', 'NBinomial', 'NBinomial2', 'NBinomial3', 'NBinomial4')

    n_samples1, n_genes = Z.shape
    n_samples2, n_markers = G.shape

    assert n_samples1 == n_samples2

    # arguments
    G = (G - _nmp.mean(G, 0)) / _nmp.std(G, 0)
    GTG = G.T.dot(G)

    args = {
        'n_samples': n_samples1,
        'n_markers': n_markers,
        'n_genes': n_genes,
        'n_iters': n_iters,
        'n_burnin': n_burnin,
        'beta_thr': beta_thr,
        's2_lims': s2_lims,
        'scale': scale,
        'Z': Z,
        'G': G,
        'GTG': GTG,
        **extra
    }

    if mdl == 'Normal':
        args['Y'] = (Z - _nmp.mean(Z, 0)) / _nmp.std(Z, 0) if scale else Z - _nmp.mean(Z, 0)
        args['YTY'] = _nmp.sum(args['Y']**2, 0)
        args['GTY'] = G.T.dot(args['Y'])

    # prepare model
    Model = {
        'Poisson': _ModelPoissonGibbs,
        'Binomial': _ModelBinomGibbs,
        'NBinomial': _ModelNBinomGibbs,
        'NBinomial2': _ModelNBinom2Gibbs,
        'NBinomial3': _ModelNBinom3Gibbs,
        'NBinomial4': _ModelNBinom4Gibbs,
        'Normal': _ModelNormalGibbs,
    }[mdl]
    mdl = Model(**args)

    # loop
    state = _nmp.empty(n_iters + 1)
    state.fill(_nmp.nan)
    state[0] = 0
    print('Starting...', file=_sys.stderr)
    parallel = None if n_threads == 1 else _mlp.Pool(processes=n_threads)
    for itr in range(1, n_iters + 1):
        mdl.update(itr, parallel=parallel, **args)
        state[itr] = mdl.get_state(**args)
        if progress:
            print('\r' + 'Iteration {0} of {1}'.format(itr, n_iters), end='', file=_sys.stderr)

    if parallel is not None:
        parallel.close()
        parallel.join()

    print('\nDone!', file=_sys.stderr)

    #
    return {
        'state': state,
        **mdl.get_estimates(**args)
    }
